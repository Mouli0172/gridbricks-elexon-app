import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gridbricks-backend")

app = FastAPI(
    title="Gridbricks Elexon Energy Dashboard API",
    description="Real Elexon BMRS telemetry ingestion for UK wind generation and day-ahead forecast analysis (Jan 1-31, 2026 & custom windows).",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ELEXON_BASE = "https://data.elexon.co.uk/bmrs/api/v1"
HEADERS = {"Accept": "application/json"}
CACHE_FILE_JAN2026 = os.path.join(os.path.dirname(__file__), "jan2026_elexon_data.json")

# In-memory cache for dynamic windows
CACHE: Dict[str, Dict[str, Any]] = {}


def fetch_dataset_chunked(endpoint: str, start_dt: datetime, end_dt: datetime, max_chunk_days: int = 7) -> List[dict]:
    """
    Fetch a dataset from Elexon BMRS in <=7-day chunks to comply with Elexon API restrictions.
    Follows meta.nextUri pagination if present.
    """
    all_results = []
    curr_start = start_dt

    while curr_start < end_dt:
        curr_end = min(curr_start + timedelta(days=max_chunk_days), end_dt)
        pub_from_str = curr_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        pub_to_str = curr_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching real {endpoint} chunk: {pub_from_str} -> {pub_to_str}")
        url = f"{ELEXON_BASE}/{endpoint}"
        params = {
            "publishDateTimeFrom": pub_from_str,
            "publishDateTimeTo": pub_to_str,
        }

        while url:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=40)
            resp.raise_for_status()
            body = resp.json()
            data_chunk = body.get("data", [])
            all_results.extend(data_chunk)
            url = (body.get("meta") or {}).get("nextUri")
            params = None

        curr_start = curr_end

    logger.info(f"Retrieved {len(all_results)} total records from {endpoint}")
    return all_results


def build_analysis_payload(fuel_records: List[dict], windfor_records: List[dict], start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    """
    Transforms raw Elexon FUELHH (WIND) and WINDFOR data into aligned 30-min settlement series.
    """
    df_act = pd.DataFrame([r for r in fuel_records if r.get("fuelType", "").upper() == "WIND"])
    df_for = pd.DataFrame(windfor_records)

    if df_act.empty:
        raise HTTPException(status_code=404, detail="No WIND records found in Elexon FUELHH dataset for requested period.")
    if df_for.empty:
        raise HTTPException(status_code=404, detail="No forecast records found in Elexon WINDFOR dataset for requested period.")

    df_act["startTime"] = pd.to_datetime(df_act["startTime"], utc=True)
    df_for["startTime"] = pd.to_datetime(df_for["startTime"], utc=True)
    df_for["publishTime"] = pd.to_datetime(df_for["publishTime"], utc=True)

    df_act["slot"] = df_act["startTime"].dt.floor("30min")
    df_act["hour_slot"] = df_act["slot"].dt.floor("h")

    df_for["hour_slot"] = df_for["startTime"].dt.floor("h")
    df_for = df_for.sort_values("publishTime").drop_duplicates(subset="hour_slot", keep="last")

    df_act = (
        df_act[["slot", "hour_slot", "generation"]]
        .drop_duplicates(subset="slot")
        .rename(columns={"generation": "actual_mw"})
    )
    df_for = df_for[["hour_slot", "generation"]].rename(columns={"generation": "forecast_mw"})

    merged = pd.merge(df_act, df_for, on="hour_slot", how="inner")
    merged = merged.sort_values("slot").reset_index(drop=True)

    # Filter strictly to target window
    merged = merged[(merged["slot"] >= start_dt) & (merged["slot"] <= end_dt)].reset_index(drop=True)

    if merged.empty:
        raise HTTPException(status_code=404, detail="No overlapping intervals found between FUELHH actuals and WINDFOR forecasts.")

    merged["variance_mw"] = merged["forecast_mw"] - merged["actual_mw"]
    merged["abs_error_mw"] = merged["variance_mw"].abs()
    merged["startTime"] = merged["slot"].dt.strftime("%Y-%m-%d %H:%M")

    output_df = merged[["startTime", "actual_mw", "forecast_mw", "variance_mw", "abs_error_mw"]]

    mae = float(output_df["abs_error_mw"].mean())
    total_variance = float(output_df["variance_mw"].sum())

    return {
        "source": "Elexon BMRS Live API",
        "period": {
            "from": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actual_start": output_df["startTime"].iloc[0],
            "actual_end": output_df["startTime"].iloc[-1],
        },
        "summary": {
            "mean_absolute_error_mw": round(mae, 2),
            "total_variance_mw": round(total_variance, 2),
            "record_count": len(output_df),
        },
        "data": output_df.to_dict(orient="records"),
    }


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "Gridbricks Wind Forecast Service",
        "elexon_live_api": ELEXON_BASE,
        "default_period": "2026-01-01 to 2026-01-31 (January 2026)",
        "source": "Official Elexon BMRS",
    }


@app.get("/api/wind-analysis")
def get_wind_analysis(
    start_date: Optional[str] = Query(
        None,
        description="Start date (YYYY-MM-DD or ISO). Defaults to 2026-01-01.",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date (YYYY-MM-DD or ISO). Defaults to 2026-01-31.",
    ),
    refresh: bool = Query(
        False,
        description="Force fresh live fetch from Elexon BMRS API.",
    ),
):
    """
    Fetches real Elexon BMRS wind generation actuals and forecast telemetry.
    Defaults specifically to January 1 to 31, 2026 (1,488 half-hour settlement intervals).
    """
    valid_start_date = start_date if isinstance(start_date, str) and start_date.strip() else None
    valid_end_date = end_date if isinstance(end_date, str) and end_date.strip() else None
    force_refresh = bool(refresh) if isinstance(refresh, bool) else False

    # Default strictly to January 1, 2026 -> January 31, 2026
    is_default_jan = False
    if not valid_start_date and not valid_end_date:
        is_default_jan = True
        start_dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(2026, 1, 31, 23, 30, 0, tzinfo=timezone.utc)
    else:
        try:
            start_dt = pd.to_datetime(valid_start_date or "2026-01-01", utc=True).to_pydatetime()
            end_dt = pd.to_datetime(valid_end_date or "2026-01-31 23:30", utc=True).to_pydatetime()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="start_date must be strictly before end_date.")

    cache_key = f"{start_dt.isoformat()}_{end_dt.isoformat()}"

    # 1. Check local persistent Jan 2026 Elexon dataset file if applicable
    if (is_default_jan or (start_dt.year == 2026 and start_dt.month == 1 and start_dt.day == 1 and end_dt.year == 2026 and end_dt.month == 1 and end_dt.day == 31)) and not force_refresh:
        if os.path.exists(CACHE_FILE_JAN2026):
            try:
                with open(CACHE_FILE_JAN2026, "r") as f:
                    cached_jan = json.load(f)
                logger.info(f"Loaded verified real Elexon January 2026 dataset ({cached_jan['summary']['record_count']} intervals)")
                return cached_jan
            except Exception as e:
                logger.warning(f"Could not read cached Jan 2026 file: {e}")

    # 2. Check in-memory cache
    if not force_refresh and cache_key in CACHE:
        logger.info(f"Serving in-memory cached analysis for {cache_key}")
        return CACHE[cache_key]

    # 3. Live chunked fetch from Elexon BMRS API
    # End date for publishDateTimeTo includes up to next boundary
    fetch_end_dt = end_dt + timedelta(hours=1)
    logger.info(f"Querying Elexon BMRS for real data from {start_dt} to {fetch_end_dt}...")

    try:
        fuel_records = fetch_dataset_chunked("datasets/FUELHH", start_dt, fetch_end_dt)
        windfor_records = fetch_dataset_chunked("datasets/WINDFOR", start_dt, fetch_end_dt)
    except requests.RequestException as e:
        logger.error(f"Elexon BMRS query failed: {e}")
        raise HTTPException(status_code=502, detail=f"Elexon BMRS API error: {e}")

    payload = build_analysis_payload(fuel_records, windfor_records, start_dt, end_dt)

    # Save to persistent file if it was for Jan 2026
    if is_default_jan:
        try:
            with open(CACHE_FILE_JAN2026, "w") as f:
                json.dump(payload, f)
        except Exception as e:
            logger.warning(f"Could not persist Jan 2026 dataset: {e}")

    CACHE[cache_key] = payload
    return payload


if __name__ == "__main__":
    import uvicorn

    port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    elif "PORT" in os.environ and os.environ["PORT"].isdigit():
        port = int(os.environ["PORT"])

    logger.info(f"Starting Gridbricks Elexon Live Backend on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
