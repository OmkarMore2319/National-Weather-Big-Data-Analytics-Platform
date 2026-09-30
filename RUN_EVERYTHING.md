# 🚀 RUN_EVERYTHING.md — Complete Local Run Sequence 

**National Weather Big Data Analytics Platform (PS 26069)**  
*Self-Contained Local Execution Guide across Windows, macOS, and Linux*

---

## 📋 System Prerequisites

| Component | Minimum Version | Notes |
| :--- | :--- | :--- |
| **Python** | 3.10+ (Tested through 3.14) | Standard virtual environment (`python -m venv`) |
| **Node.js & npm** | Node 18+ / npm 9+ | Standard Vite React frontend |
| **Network** | Offline / Localhost only | Zero external cloud or Docker dependencies required |

---

## ⚡ The 6-Process End-to-End Run Sequence

To start the entire platform from scratch, open **six separate terminal windows** (no containers, no background daemons that hide crashes). Terminals 1–4 are required; Terminals 5 and 6 are strongly recommended so the dashboard shows genuinely live news and weather data, not just seeded/simulated content.
```bash
Terminal 1: FastAPI Backend (Port 8010) 
 cd backend 
 venv\Scripts\activate (or source venv/bin/activate on Unix) 
 python -m uvicorn main:app --reload --port 8010 --host 127.0.0.1 
```
```bash
 Terminal 2: Database Seeder (Run Once) 
 cd backend 
 venv\Scripts\activate 
 python seed_demo_data.py 
```
```bash
Terminal 3: Frontend Dev Server (Port 5173) 
 cd frontend 
 npm run dev 
```
```bash
 Terminal 4: High-Velocity Live Stream Demo Mode 
 python run_demo_mode.py 
 (Or double-click demo_mode.bat on Windows / ./demo_mode.sh on Unix) 
```
```bash
 Terminal 5: Real Live News/RSS Ingestion (Recommended) 
 cd ingestion 
 python news_rss_scraper.py --interval 45 
```
```bash
Terminal 6: Real Live Official Weather Data Puller (Recommended) 
 cd ingestion 
 python official_puller.py --interval 180 
```
---

## 🛠️ Step-by-Step Instructions by Operating System

### 1. Terminal 1: Backend & ML Verification Service

The backend hosts the SQLite WAL database, the real `ml_verification` engine (TF-IDF + Cosine Duplicate + Factor Scorer), REST APIs, and live WebSockets.

#### Windows (PowerShell or Command Prompt):
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # If PowerShell script execution is restricted: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8010 --host 127.0.0.1
```

#### macOS / Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8010 --host 127.0.0.1
```

*Verification:*
- Open [http://127.0.0.1:8010/api/v1/health](http://127.0.0.1:8010/api/v1/health) in your browser.
- Expected response: `{"status":"ok","service":"weather-backend"}`
- Interactive Swagger docs: [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)

---

### 2. Terminal 2: Seed Demo Baseline Dataset (Run Once)

Populates 150 realistic Indian weather events across 25 major cities, 25 official IMD ground-truth readings, and initial admin audit log entries into SQLite.

#### Windows:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python seed_demo_data.py
```

#### macOS / Linux:
```bash
cd backend
source venv/bin/activate
python3 seed_demo_data.py
```

*Verification:*
- The terminal will display: `[SEED SUCCESS] 150 events, 25 official readings, 4 admin overrides inserted.`

---

### 3. Terminal 3: React Frontend Dashboard

Interactive Leaflet weather map, live WebSocket event feed, factor breakdown inspector, citizen report modal, and admin override control room.

#### All Platforms (Windows / macOS / Linux):
```bash
cd frontend
npm install
npm run dev
```

*Verification:*
- Open [http://localhost:5173](http://localhost:5173) in Chrome or Edge.
- Verify the green pulse dot indicating active WebSocket connection to `ws://localhost:8010/ws/live`.
- Stat cards and India map will immediately populate from the SQLite backend.

---

### 4. Terminal 4: Automated Ingestion & Live Demo Mode

To demonstrate real-time high-velocity ingestion :

#### Windows:
```cmd
demo_mode.bat
```
*or via Python:*
```powershell
python run_demo_mode.py --rate 2.0 --duration 4.0
```

#### macOS / Linux:
```bash
chmod +x demo_mode.sh
./demo_mode.sh
```

### 5. Terminal 5: Real Live News/RSS Ingestion (Recommended)

Continuously scrapes real, live weather-related headlines from Google News (India Weather search), The Hindu, and Indian Express RSS feeds, geocodes each item locally against a 300-city lookup table, and posts them to the backend as `NEWS_RSS` events. This is genuine live data, not simulated.

```bash
cd ingestion
python news_rss_scraper.py --interval 45
```

- `--interval 45` — re-scrapes every 45 seconds, frequent enough to feel live without over-polling the RSS feeds.
- Leave this running for the duration of your session (not just during the judged demo window) so the dashboard reflects genuinely current news.

---

### 6. Terminal 6: Real Live Official Weather Data Puller (Recommended)

Continuously pulls real, live current weather conditions (temperature, rainfall, wind, sky condition) for 32 major Indian cities from the free Open-Meteo API, and posts them to the backend as `OFFICIAL_STATION` (reference weather data) events, used by the verification engine's cross-match factor.

```bash
cd ingestion
python official_puller.py --interval 180
```

- `--interval 180` — re-pulls every 180 seconds (3 minutes). A longer interval than the RSS scraper is intentional: real weather conditions change slowly minute-to-minute, so polling less frequently is both sufficient and considerate of the free API's rate limits.
- Leave this running for the duration of your session for the same reason as Terminal 5.

---


## 🧪 Running Standalone Verification Tests

Both backend and ingestion modules include self-contained unit and contract compliance test suites:

### 1. Backend & ML Scorer Integration Tests (11/11 tests)
```bash
python -m unittest backend/test_backend.py
```

### 2. ML Verification Standalone Model Tests (10/10 scenarios)
```bash
python backend/ml_verification/test_standalone.py
```

### 3. Ingestion & Geocoding Suite (12/12 tests)
```bash
python -m unittest ingestion/test_ingestion.py
```

---

## 🔑 Key Endpoints & User Roles / Credentials

### 1. 🛡️ Admin / Incident Controller Officer (Admin Role)
Used for ground-truth verification, status overrides (`VERIFIED`, `REJECTED`, `DUPLICATE`), viewing audit logs, and generating **OASIS CAP v1.2 XML** emergency alerts.
- **Admin Officer Call-sign (Username)**: Any call-sign name (e.g. `admin_officer`, `officer_deshmukh`)
- **X-Admin-Token Secret**: `secret-admin-token-123`
- **API Header**: `X-Admin-Token: secret-admin-token-123`
- **UI Access**:
  - Open [http://localhost:5173](http://localhost:5173) in your browser.
  - Click **Admin Console** in the top navigation bar.
  - Enter your Officer Call-sign and set Token Secret to `secret-admin-token-123`.

### 2. 🌐 System URLs & Endpoints
- **Dashboard UI**: [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Docs**: [http://localhost:8010/docs](http://localhost:8010/docs)
- **Health Check Endpoint**: [http://localhost:8010/api/v1/health](http://localhost:8010/api/v1/health)
