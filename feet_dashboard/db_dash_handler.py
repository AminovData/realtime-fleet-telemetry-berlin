import time
from collections import Counter
import json
import redis
from pymongo import MongoClient


def ensure_group(r, r_stream, r_group):
    try:
        r.xgroup_create(r_stream, r_group, id="$", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            print(f"Redis error: {e}")


def fetch_vehicle_docs(car_id, start_dt, end_dt, mongo_uri, mongo_db, mongo_collection):
    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    collection = db[mongo_collection]
    
    docs = list(collection.find({
        "vehicle_id": car_id,
        "timestamp": {"$gte": start_dt.isoformat(), "$lte": end_dt.isoformat()}
    }).sort("timestamp", 1))
    
    return docs


def update_car_state(car_data, cars_state, fail_summary, parse_timestamp):
    car_id = car_data["vehicle_id"]
    ts = parse_timestamp(car_data["timestamp"])
    
    should_update = True
    if car_id in cars_state:
        if ts <= cars_state[car_id]["timestamp"]:
            should_update = False
    
    if should_update:
        failures = car_data["sensor_failures"]
        
        fail_type = type(failures)
        if fail_type == str:
            try:
                failures = json.loads(failures.replace("'", '"'))
            except:
                failures = []
        
        cars_state[car_id] = {
            "failures": list(set(fail_summary(failures))),
            "speed": car_data["speed"],
            "timestamp": ts
        }



def process_redis_message(msg_id, data_dict, buffer, r, cars_state, r_stream, r_group, 
                         update_car_state, fail_summary, parse_timestamp):
    raw = data_dict.get("data")

    try:
        if raw:
            data = json.loads(raw)
            car_id = data["vehicle_id"]
            ts = parse_timestamp(data["timestamp"])
            
            last_ts = cars_state.get(car_id, {}).get("timestamp", 0)
            if ts < last_ts:
                pass
            else:
                update_car_state(data, cars_state, fail_summary, parse_timestamp)
                buffer.append(data)
    except Exception as e:
        print(f"Parse error: {e}")
    finally:
        r.xack(r_stream, r_group, msg_id)


def calc_and_emit_metrics(buffer, cars_state, socketio):
    socketio.emit("vehicle_batch_update", buffer)
    print(f"Emitted {len(buffer)} updates")
    
    failed = {car_id for car_id, v in cars_state.items() if v["failures"]}
    moving_failed = {car_id for car_id, v in cars_state.items() if v["failures"] and v["speed"] > 0}
    
    fail_counts = Counter()
    for car_id in failed:
        v = cars_state[car_id]
        fail_list = v.get("failures", [])
        for f in fail_list:
            fail_counts[f] += 1 

    if cars_state:
        fail_rate = (len(failed)/len(cars_state)*100)
    else:
        fail_rate = 0

    common = fail_counts.most_common()
    
    print(f"Metrics: total={len(cars_state)} failed={len(failed)} rate={fail_rate:.1f}%")
    
    socketio.emit("metrics_update", {
        "vehicles_with_failures": list(failed),
        "moving_failed_vehicles": list(moving_failed),
        "failure_rate": round(fail_rate, 2),
        "most_common_failure_type": common,
    })
        

def redis_listener(r, socketio, cars_state, r_stream, r_group, consumer, fail_summary, parse_timestamp):
    print("Starting redis listener")
    ensure_group(r, r_stream, r_group)
    
    last_emit = time.time()
    buffer = []
    
    while True:
        try:
            entries = r.xreadgroup(
                groupname=r_group,
                consumername=consumer,
                streams={r_stream: ">"},
                count=100,
                block=2000
            )
            
            if entries:
                for _, msg in entries:
                    for msg_id, data_dict in msg:
                        process_redis_message(
                            msg_id, data_dict, buffer, r, cars_state, r_stream, r_group,
                            update_car_state, fail_summary, parse_timestamp
                        )
            now = time.time()
            if buffer and now - last_emit >= 1:
                calc_and_emit_metrics(buffer, cars_state, socketio)
                buffer.clear()
                last_emit = now
        except redis.exceptions.ResponseError as e:
            print(f"Redis error: {e}")
            time.sleep(1)
            ensure_group(r, r_stream, r_group)
        except Exception as e:
            print(f"Listener error: {e}")
            time.sleep(1)
