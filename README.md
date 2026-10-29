# Elexon Energy Demand Forecasting App

A full-stack, containerized dashboard for monitoring real-time UK energy demand against forecast models using Elexon BMRS data. Designed for grid operators and energy traders to track grid volatility, calculate absolute error margins, and visualize energy data instantly.

## 🚀 Features
- **Real-Time KPI Tracking:** Instant calculation of Mean Absolute Error (MW) and Total Variance.
- **Interactive Visualization:** Responsive time-series charts comparing actual energy generation vs. forecasted demand.
- **Data Pipeline:** Python backend for cleaning, formatting, and mathematically aggregating raw Elexon data before serving it to the client.
- **Containerized Architecture:** Fully isolated frontend and backend services using Docker for seamless deployment.

## 🛠️ Tech Stack
- **Frontend:** React.js, Vite, Tailwind CSS
- **Backend:** Python (FastAPI / Flask)
- **Infrastructure:** Docker, Docker Compose
- **Data Source:** Elexon BMRS API / JSON datasets

## ⚙️ Local Development Setup

### Prerequisites
- Docker & Docker Compose installed
- Node.js (for local frontend development)
- Python 3.9+ (for local backend development)

### Run with Docker (Recommended)
1. Clone the repository:
   `git clone https://github.com/yourusername/gridbricks-elexon.git`
   `cd gridbricks-elexon`
2. Build and spin up the containers:
   `docker-compose up --build`
3. Access the application:
   - Frontend Dashboard: `http://localhost:5173`
   - Backend API: `http://localhost:8000`

## 👤 Author
**Chandramouleeshwaran M**
Full Stack Developer & AI/ML Engineer
