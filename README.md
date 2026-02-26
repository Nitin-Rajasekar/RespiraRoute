# RespiraRoute

<img width="1493" height="881" alt="Pic-1" src="https://github.com/user-attachments/assets/1929c5dc-9b2b-417b-ac0e-08bc8c39b4a1" />
<img width="1443" height="790" alt="Pic-2" src="https://github.com/user-attachments/assets/9a8c47d8-2d02-4c55-9704-8c9c3791f848" />
<img width="330" height="413" alt="Pic-3" src="https://github.com/user-attachments/assets/842cc7ea-6a45-4fe7-8665-ab78676689f8" />
<img width="1280" height="863" alt="Pic-4" src="https://github.com/user-attachments/assets/cea12f40-84a1-47d8-b29b-e42ce6fedd93" />
<img width="1275" height="315" alt="Pic-5" src="https://github.com/user-attachments/assets/e7e119f2-8e04-4bbc-bfef-673d73caa90b" />

**Real-Time Urban Air Quality & Healthier Route Recommendation System**

A real-time system that monitors environmental conditions in city zones and recommends the healthiest commute route based on pollution exposure — powered by streaming data pipelines.

## Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌────────────┐    ┌──────────┐
│  Simulator   │───>│  Pathway Pipeline │───>│  FastAPI    │───>│  React   │
│  (JSONL)     │    │  (Stream Process) │    │  (REST+SSE) │    │  (UI)    │
└─────────────┘    └──────────────────┘    └────────────┘    └──────────┘
```

- **Data Simulator** generates realistic AQI, traffic, and weather data every 3 seconds
- **Pathway Pipeline** processes the stream: rolling averages, trend detection, anomaly alerts
- **FastAPI Server** serves computed results via REST API
- **React Frontend** displays real-time dashboard with auto-refresh

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend

```bash
cd backend
pip install -r ../requirements.txt
python server.py
```

The backend starts on `http://localhost:8000`. It automatically:
- Launches the data simulator (writes streaming JSONL)
- Starts the Pathway-inspired pipeline
- Serves the API

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Opens on `http://localhost:3000`.

### Optional: OpenAI Integration

For enhanced AI explanations, set your API key:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

Without it, the system uses intelligent rule-based explanations (works great for demos).

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/dashboard` | Full dashboard data (zones + routes + anomalies) |
| `GET /api/zones` | Latest zone data with AQI, traffic, weather |
| `GET /api/routes` | Route exposure scores and recommendation |
| `GET /api/explain/route` | AI: Why is this route safer? |
| `GET /api/explain/pollution` | AI: What caused the pollution spike? |
| `GET /api/explain/health` | AI: Health advice for commute |
| `GET /api/stream` | Server-Sent Events for real-time updates |

## Exposure Model

```
Exposure Score = Σ (AQI × time_in_zone × traffic_factor)
```

| Traffic Level | Factor |
|---|---|
| Low | 1.0x |
| Moderate | 1.3x |
| High | 1.7x |
| Severe | 2.2x |

Lower score = healthier route.

## Tech Stack

- **Backend:** Python, FastAPI, Pathway-style streaming
- **Frontend:** React 18, TailwindCSS
- **AI:** OpenAI GPT (optional) + rule-based fallback
- **Data:** Simulated real-time JSONL streams

## Project Structure

```
aqi-app-2/
├── backend/
│   ├── server.py              # FastAPI app + startup
│   ├── data_simulator.py      # Real-time data generator
│   ├── pathway_pipeline.py    # Streaming data pipeline
│   ├── route_calculator.py    # Exposure score engine
│   ├── ai_explainer.py        # AI explanation module
│   └── config.py              # Zones, routes, settings
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── App.jsx            # Main app
│   │   └── index.css          # TailwindCSS styles
│   └── package.json
├── requirements.txt
└── README.md
```
