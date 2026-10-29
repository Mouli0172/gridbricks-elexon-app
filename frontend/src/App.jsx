import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Activity, Zap, AlertTriangle, ShieldCheck, RefreshCw, BarChart2 } from 'lucide-react';

export default function App() {
  const [data, setData] = useState([]);
  const [summary, setSummary] = useState(null);
  const [period, setPeriod] = useState(null);
  const [source, setSource] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);

    const endpoints = [
      'https://gridbricks-elexon-app.onrender.com/api/wind-analysis',
      'http://localhost:8080/api/wind-analysis',
      'http://localhost:8000/api/wind-analysis',
    ];

    const queryString = forceRefresh ? '?refresh=true' : '';
    let success = false;
    let lastError = null;

    for (const base of endpoints) {
      try {
        const res = await axios.get(`${base}${queryString}`, { timeout: 45000 });
        setData(res.data.data);
        setSummary(res.data.summary);
        setPeriod(res.data.period);
        setSource(res.data.source);
        success = true;
        break;
      } catch (err) {
        lastError = err;
      }
    }

    if (!success) {
      console.error('Failed to connect to backend on 8080 and 8000:', lastError);
      setError('Failed to establish connection with Elexon Telemetry Engine.');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0B0F17] text-gray-300">
        <RefreshCw className="w-8 h-8 animate-spin text-[#3B82F6] mb-3" />
        <p className="text-sm tracking-wider uppercase font-semibold text-gray-400">
          Ingesting Elexon BMRS Telemetry Stream...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0B0F17] text-[#EF4444]">
        <AlertTriangle className="w-10 h-10 mb-2" />
        <p className="text-base font-semibold">{error}</p>
        <button
          onClick={() => fetchData(true)}
          className="mt-4 px-4 py-2 bg-[#111827] border border-[#1F2937] text-gray-200 rounded-md hover:bg-gray-800 transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F17] text-gray-100 p-6 md:p-10 font-sans">
      {/* Top Header Navigation */}
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-8 border-b border-[#1F2937] gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 bg-blue-500/10 rounded-lg text-[#3B82F6] border border-blue-500/20">
              <Zap className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Gridbricks <span className="text-gray-500 font-normal">| Energy Decision Platform</span>
            </h1>
          </div>
          <p className="text-xs text-gray-400 pl-11">
            UK Wind Generation Analytics &mdash;{' '}
            {period?.actual_start && period?.actual_end
              ? `${period.actual_start} → ${period.actual_end}`
              : period
              ? `${period.from.slice(0, 10)} → ${period.to.slice(0, 10)}`
              : 'Last 7 Days'}{' '}
            · {source ?? 'Elexon BMRS'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3.5 h-3.5" />
            {source === 'Elexon BMRS Live API' ? 'Live API Connected' : 'Data Loaded'}
          </span>
          <button
            onClick={() => fetchData(true)}
            className="p-2 bg-[#111827] border border-[#1F2937] rounded-lg hover:bg-gray-800 transition text-gray-300"
            title="Refresh Data from Elexon"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* KPI Cards Section */}
      {summary && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="p-5 bg-[#111827] border border-[#1F2937] rounded-xl shadow-lg relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Mean Absolute Error (MAE)
              </span>
              <Activity className="w-4 h-4 text-[#3B82F6]" />
            </div>
            <div className="text-3xl font-extrabold text-white">
              {summary.mean_absolute_error_mw.toLocaleString()} <span className="text-sm font-normal text-gray-400">MW</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">Average forecast variation margin</p>
          </div>

          <div className="p-5 bg-[#111827] border border-[#1F2937] rounded-xl shadow-lg relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Cumulative Net Variance
              </span>
              <AlertTriangle className="w-4 h-4 text-[#F59E0B]" />
            </div>
            <div className="text-3xl font-extrabold text-[#F59E0B]">
              {summary.total_variance_mw.toLocaleString()} <span className="text-sm font-normal text-gray-400">MW</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">Total thermal procurement requirement</p>
          </div>

          <div className="p-5 bg-[#111827] border border-[#1F2937] rounded-xl shadow-lg relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Settlement Periods Ingested
              </span>
              <BarChart2 className="w-4 h-4 text-[#10B981]" />
            </div>
            <div className="text-3xl font-extrabold text-[#10B981]">
              {summary.record_count} <span className="text-sm font-normal text-gray-400">Intervals</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">30-minute resolution dataset</p>
          </div>
        </section>
      )}

      {/* Primary Analytics Chart Card */}
      <main className="bg-[#111827] border border-[#1F2937] p-6 rounded-xl shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 pb-4 border-b border-[#1F2937] gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Generation Profile vs. Forecast Variance</h2>
            <p className="text-xs text-gray-400">Overlay of Actual Wind Generation, Day-Ahead Forecast, and Net Delta</p>
          </div>

          <div className="flex items-center gap-6 text-xs font-medium">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#10B981] inline-block"></span>
              <span className="text-gray-300">Actual (MW)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#3B82F6] inline-block"></span>
              <span className="text-gray-300">Forecast (MW)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#EF4444] inline-block"></span>
              <span className="text-gray-300">Variance Delta (MW)</span>
            </div>
          </div>
        </div>

        <div className="w-full h-[450px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
              <XAxis
                dataKey="startTime"
                tick={false}
                stroke="#6B7280"
              />
              <YAxis
                stroke="#6B7280"
                fontSize={12}
                tickFormatter={(val) => `${val} MW`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#111827',
                  borderColor: '#374151',
                  borderRadius: '8px',
                  color: '#F3F4F6',
                  fontSize: '12px',
                }}
                formatter={(value, name) => [`${Math.round(value).toLocaleString()} MW`, name]}
                labelFormatter={(label) => `Settlement Time: ${label}`}
              />
              <Area
                type="monotone"
                dataKey="forecast_mw"
                stroke="#3B82F6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorForecast)"
                name="Forecast (MW)"
              />
              <Area
                type="monotone"
                dataKey="actual_mw"
                stroke="#10B981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorActual)"
                name="Actual (MW)"
              />
              <Line
                type="monotone"
                dataKey="variance_mw"
                stroke="#EF4444"
                strokeWidth={1.5}
                dot={false}
                name="Variance (MW)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </main>
    </div>
  );
}