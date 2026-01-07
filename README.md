# Real-Time Fleet Telemetry Pipeline

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
#### Demo
<video src="https://github.com/user-attachments/assets/bc59ece4-2610-45e8-ac1f-7760a39c5135" autoplay loop muted playsinline width="500px"></video>

### Vehicle Detail
Per-vehicle telemetry: speed, acceleration, engine temp, tire pressure, battery, oil pressure, active failures.
#### Demo
<video src="https://github.com/user-attachments/assets/61e6d541-6daf-4948-85a2-d09d6af09bab" autoplay loop muted playsinline width="500px"></video>

### Historical Analysis
Route replay, performance trends, failure timeline with date filtering.
#### Demo

<img src="https://github.com/user-attachments/assets/5ccbf441-7f32-46be-8b90-106826ef9ab5" width="1000">

## Project Structure
## Project Structure
```
├── feet_dashboard/
│   ├── static/
│   │   ├── historical_dashboard.css
│   │   ├── historical.js
│   │   ├── individual_dashboard_style.css
│   │   ├── main_dashboard.css
│   │   └── main.js
│   ├── templates/
│   │   ├── historical_dashboard.html
│   │   ├── index.html
│   │   └── specific_car.html
│   ├── app.py
│   ├── config.py
│   ├── db_dash_handler.py
│   ├── helpers.py
│   
real-time-fleet-telemetry-berlin/
├── real_time_fleet_data_simulator/
│   ├── data/
│   │   ├── berlin_fixing_stations.json
│   │   ├── routes_1000_interpolated.json
│   │   └── stopped_vehicles.json #Automatically Created 
│   ├── config.py
│   ├── consumer_s3_mongo.py   
│   ├── helpers.py
│   ├── kafka_utils.py 
│   ├── simulation.py 
│   └── vehicle.py
├── requirements.txt
└── env_example
└── README.md
```
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





