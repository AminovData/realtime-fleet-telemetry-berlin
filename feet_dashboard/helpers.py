
import json
from datetime import datetime, timedelta
from collections import defaultdict
from dateutil import parser
import math

cars_state = {}

def parse_timestamp(ts):
    result = 0
    ts_type = type(ts)
    
    if ts_type == int or ts_type == float:
        result = ts
    elif ts_type == str:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            result = dt.timestamp()
        except:
            result = 0
    
    return result

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
    return 2*R*math.asin(math.sqrt(a))


def fail_summary(failures):
    if isinstance(failures, str):
        try:
            failures = json.loads(failures)
        except:
            return []
    
    if not failures:
        return []
    
    result = set()
    for f in failures:
        if f.startswith("tire_"):
            result.add("tire_pressure_fail")
        else:
            result.add(f)
    return list(result)

def parse_date_range(start_date, end_date):
    if not start_date or not end_date:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=1)
    else:
        start_dt = datetime.fromisoformat(start_date + "T00:00:00")
        end_dt = datetime.fromisoformat(end_date + "T23:59:59")
    return start_dt, end_dt

def group_by_segments(docs):
    segs = defaultdict(list)
    for d in docs:
        seg_id = d.get("segment_id")
        if seg_id:
            segs[seg_id].append({
                "lat": d["lat"],
                "lon": d["lon"],
                "timestamp": parser.isoparse(d["timestamp"]).isoformat(),
                "sensor_failures": d.get("sensor_failures", [])
            })
    return segs

def assign_colors_and_markers(segs):
    sorted_seg_ids = sorted(segs.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))
    
    seg_colors = {}
    seg_markers = {}
    
    for i, seg_id in enumerate(sorted_seg_ids):
        pts = segs[seg_id]
        
        has_failure = False
        for p in pts:
            if p.get("sensor_failures"):
                has_failure = True
                break
        
        seg_colors[seg_id] = "red" if has_failure else "blue"
        
        markers = []
        if pts:
            markers.append({"lat": pts[0]["lat"], "lon": pts[0]["lon"], "type": "start", "order": i + 1})
            markers.append({"lat": pts[-1]["lat"], "lon": pts[-1]["lon"], "type": "end"})
            for p in pts:
                if p.get("sensor_failures"):
                    markers.append({"lat": p["lat"], "lon": p["lon"], "type": "failure"})
        seg_markers[seg_id] = markers
    
    return sorted_seg_ids, seg_colors, seg_markers


def calc_trip_metrics(docs):
    total_dist = 0
    for i in range(len(docs) - 1):
        total_dist += haversine(docs[i]['lat'], docs[i]['lon'], docs[i + 1]['lat'], docs[i + 1]['lon'])
    
    start_t = parser.isoparse(docs[0]['timestamp'])
    end_t = parser.isoparse(docs[-1]['timestamp'])
    duration = (end_t - start_t).total_seconds() / 3600
    
    all_fails = []
    for d in docs:
        all_fails.extend(d.get("sensor_failures", []))
    
    total_speed = 0
    max_spd = 0
    total_temp = 0
    for d in docs:
        spd = d.get("speed", 0)
        total_speed += spd
        if spd > max_spd:
            max_spd = spd
        total_temp += d.get("engine_temp", 0)
    
    metrics = {
        "distance": round(total_dist, 1),
        "duration": round(duration, 2),
        "failures": len(set(all_fails)),
        "avg_speed": round(total_speed / len(docs), 1),
        "max_speed": max_spd,
        "avg_temp": round(total_temp / len(docs), 1)
    }
    
    return metrics


def extract_failure_timeline(docs):
    seen_fails = set()
    fail_time = []
    for d in docs:
        for f in d.get("sensor_failures", []):
            if f not in seen_fails:
                fail_time.append({"time": d["timestamp"], "event": f})
                seen_fails.add(f)
    return fail_time


def aggregate_daily_metrics(docs):
    daily_data = defaultdict(lambda: {"speed": [], "engine_temp": [], "battery_level": [], "oil_pressure": []})
    for d in docs:
        day = parser.isoparse(d["timestamp"]).date().isoformat()
        daily_data[day]["speed"].append(d.get("speed", 0))
        daily_data[day]["engine_temp"].append(d.get("engine_temp", 0))
        daily_data[day]["battery_level"].append(d.get("battery_level", 0))
        daily_data[day]["oil_pressure"].append(d.get("oil_pressure", 0))
    
    daily_labels = []
    daily_speed = []
    engine_tmp = []
    daily_battery = []
    daily_oil = []
    
    for day, vals in sorted(daily_data.items()):
        daily_labels.append(day)
        
        if vals["speed"]:
            daily_speed.append(round(sum(vals["speed"]) / len(vals["speed"]), 1))
        else:
            daily_speed.append(0)
        
        if vals["engine_temp"]:
            engine_tmp.append(round(sum(vals["engine_temp"]) / len(vals["engine_temp"]), 1))
        else:
            engine_tmp.append(0)
        
        if vals["battery_level"]:
            daily_battery.append(round(sum(vals["battery_level"]) / len(vals["battery_level"]), 1))
        else:
            daily_battery.append(0)
        
        if vals["oil_pressure"]:
            daily_oil.append(round(sum(vals["oil_pressure"]) / len(vals["oil_pressure"]), 1))
        else:
            daily_oil.append(0)
    
    return daily_labels, daily_speed, engine_tmp, daily_battery, daily_oil



