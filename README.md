# realtime-fleet-telemetry-berlin
# Fleet Telemetry Pipeline

Real-time fleet monitoring system with synthetic vehicle telemetry, streaming architecture, and live dashboards.

## Overview

Simulates 1,000+ vehicles across Berlin with realistic GPS routes, sensor data, and failure scenarios. Vehicles with failures automatically route to repair stations.

**Stack:** Python · Kafka · Redis · MongoDB · Flask · Leaflet.js · Chart.js

## Architecture

```
Synthetic Data → Kafka → Redis/MongoDB → Flask API → WebSocket → Dashboard
```

## Dashboards

### Fleet View
Live map of all vehicles. Red = failure, Green = normal. Shows failure rates and affected vehicles.
## Demo
<video src="https://github.com/user-attachments/assets/bc59ece4-2610-45e8-ac1f-7760a39c5135" autoplay loop muted playsinline width="70%"></video>


### Vehicle Detail
Per-vehicle telemetry: speed, acceleration, engine temp, tire pressure, battery, oil pressure, active failures.

![Vehicle Dashboard](screenshots/individual_dashboard.png)

### Historical Analysis
Route replay, performance trends, failure timeline with date filtering.

![Historical Dashboard](screenshots/historical_dashboard.png)

## Project Structure

real-time-fleet-telemetry-berlin/
│
├── vehicle_simulation_folder/
│   │
│   ├── data_folder/
│   │   ├── berlin_fixing_stations.json
│   │   ├── routes_1000_interpolated.json
│   │   └── stopped_vehicles.json
│   │
│   ├── simulation.py
│   ├── vehicle.py
│   ├── kafka_utils.py
│   ├── consumer_s3_mongo.py
│   └── helpers.py
│
├── vehicle_dashboard_folder/
│   │
│   ├── static/
│   │   ├── historical_dashboard.css
│   │   ├── historical.js
│   │   ├── individual_dashboard_style.css
│   │   ├── main_dashboard.css
│   │   └── main.js
│   │
│   ├── templates/
│   │   ├── historical_dashboard.html
│   │   ├── index.html
│   │   └── specific_car.html
│   │
│   ├── app.py
│   ├── config.py
│   ├── db_dash_handler.py
│   ├── helpers.py
│   └── env_example
│
├── requirements.txt
└── README.md

## Quick Start

```bash
# Start infrastructure
docker-compose up -d  # Kafka, Redis, MongoDB

# Run simulation
cd vehicle_simulation
python simulation.py

# Run dashboard
cd vehicle_dashboard
python app.py

# Open http://localhost:8081
```

## Config

See `config.py` for simulation parameters (vehicle count, failure rates, thresholds).





