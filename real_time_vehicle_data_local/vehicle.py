import random
import time
import json
from geopy.distance import geodesic
from helpers import get_ors_route, calculate_heading, interpolate_points, add_failure, nearest_repair_station, load_file
from config import TOTAL_FAILS, SENSOR_SEVERITY, ARRIVAL_THRESHOLD_M,STOPPED_CARS_FILE_PATH, MAX_UNIQUE_CARS, NUM_ACTIVE

gl_failures = {}
gl_plan_failures = {}
gl_cars_to_fail = set()
gl_prv_speed = {}
car_count = 1
uniq_created = 0
fuel = {}
coolant_tmp = {}
tire_press = {}
oil_press = {}
seg_buff = {}
failure_count = 0 
cars_done = 0





def __build_route(route_choice, start_lat=None, start_lon=None):
    or_route = route_choice['route']
    
    if start_lat is not None and start_lon is not None:
        dest = or_route[-1]
        ors = get_ors_route(start_lat, start_lon, dest['lat'], dest['lon'])
        if ors:
            route = interpolate_points(ors)
        else:
            route = interpolate_points([
                {'lat': start_lat, 'lon': start_lon},
                {'lat': dest['lat'], 'lon': dest['lon']}
            ])
    else:
        route = or_route.copy()
    return route, or_route.copy()  




def __initialize_vehicle_sensors(car_id):
    gl_prv_speed[car_id] = random.uniform(30, 60)
    fuel[car_id] = 100.0
    coolant_tmp[car_id] = random.uniform(70, 90)
    tire_press[car_id] = {}
    tire_press[car_id]['fl'] = random.uniform(30, 35)
    tire_press[car_id]['fr'] = random.uniform(30, 35)
    tire_press[car_id]['rl'] = random.uniform(30, 35)
    tire_press[car_id]['rr'] = random.uniform(30, 35)
    oil_press[car_id] = random.uniform(30, 50)

def spawn_vehicle(route_choice, start_lat=None, start_lon=None):
    global car_count, uniq_created

    if car_count > MAX_UNIQUE_CARS:
        car_count = 1

    car_id = f"CAR_{car_count:03d}"
    car_count += 1
    uniq_created = min(uniq_created + 1, MAX_UNIQUE_CARS)
    

    route, or_route = __build_route(route_choice, start_lat, start_lon)
    if route:
        dest = route[-1]
    else:
        dest = None
    info = {
        'route_id': route_choice['route_id'],
        'segment_id': f"seg_{car_id}_{int(time.time())}", 
        'original_route': or_route,
        'route': route,
        'idx': 0,
        'destination': dest,
        'vehicle_failed_once': False
    }
    __initialize_vehicle_sensors(car_id)

    failure_eligibility(car_id, info['vehicle_failed_once'])

    return car_id, info


def update_kinematics(car_id, info):
    idx = info['idx']
    route = info['route']
    if not route or idx >= len(route):
        return None

    lat = route[idx]['lat'] + random.uniform(-0.00001,0.00001)
    lon = route[idx]['lon'] + random.uniform(-0.00001,0.00001)
    if idx < len(route) - 1:
        heading = calculate_heading(lat, lon, route[idx+1]['lat'], route[idx+1]['lon'])
    else:
        heading = 0

    prv_speed = gl_prv_speed.get(car_id, random.uniform(30,50))
    delta = random.uniform(-5,5)
    speed = max(0, min(prv_speed + delta, 70))
    acc = speed - prv_speed
    gl_prv_speed[car_id] = speed
    brake_status = acc < -1
    engine_tmp = random.uniform(85,100)

    
    coolant_temp = coolant_tmp[car_id]
    battery_lvl = fuel[car_id]
    tire_pressure = tire_press[car_id].copy()
    oil_pressure = oil_press[car_id]

    return {
        'lat': lat,
        'lon': lon,
        'heading': heading,
        'speed': speed,
        'acceleration': acc,
        'brake_status': brake_status,
        'engine_temp': engine_tmp,
        'coolant_temp': coolant_temp,
        'battery_level': battery_lvl,
        'tire_pressure': tire_pressure,
        'oil_pressure': oil_pressure
    }


def schedule_failure_if_eligible(car_id, info, lat, lon, rep_stations):

    max_failures = int(NUM_ACTIVE * TOTAL_FAILS)
    if len(gl_failures) >= max_failures:
        return 

    if (car_id in gl_cars_to_fail) and (car_id not in gl_plan_failures) and (car_id not in gl_failures) and not info['vehicle_failed_once']:
        route = info['route']

        route_len = len(route)
        if route_len < 50: 
            return
        
        start_buff = max(5, int(route_len * 0.1))
        min_idx = start_buff
        max_idx = max(min_idx, int(route_len * 0.9))
        trigger_idx = random.randint(min_idx, max_idx)

        fail_type = random.choice(["coolant_temp","battery_level","tire_pressure","oil_pressure"])
        severity = random.choice(SENSOR_SEVERITY)
        rep_station = nearest_repair_station(lat, lon, rep_stations)

        gl_plan_failures[car_id] = {
            "chosen_sensor": fail_type,
            "severity": severity,
            "trigger_idx": trigger_idx,
            "repair_station": rep_station
        }

        gl_cars_to_fail.discard(car_id)
        info['vehicle_failed_once'] = True


        print(f"{car_id} scheduled failure: Type: {fail_type} (sev={severity}), At idx: {trigger_idx}/{route_len-1}, Repair Station: {rep_station['address']}")


def activate_failure(car_id, info, idx, lat, lon):
    if car_id in gl_plan_failures and car_id not in gl_failures:
        plann_fail = gl_plan_failures[car_id]
        if idx >= plann_fail['trigger_idx']:
            rep_station = plann_fail['repair_station']
            ors_to_repair = get_ors_route(lat, lon, rep_station['lat'], rep_station['lon'])
            if ors_to_repair:
                route_to_repair = interpolate_points(ors_to_repair)
            else:
                route_to_repair = interpolate_points(
                    [
                    {'lat': lat, 'lon': lon},
                    {'lat': rep_station['lat'], 'lon': rep_station['lon']}
                    ])
            
            gl_failures[car_id] = {
                "sensors": [plann_fail['chosen_sensor']],
                "severity": plann_fail['severity'],
                "phase": "to_repair",
                "repair_station": rep_station
            }
            info['route'] = route_to_repair
            info['idx'] = 0
            info['destination'] = {'lat': rep_station['lat'], 'lon': rep_station['lon']}
            
            
            info['vehicle_failed_once'] = True

            gl_plan_failures.pop(car_id, None)
            gl_cars_to_fail.discard(car_id)
            print(f"{car_id}: FAILED. Redirecting to repair station:{rep_station['address']}")



def apply_active_failures(car_id, info, sens_data, current_idx=None):
    sens_fail = []
    lat, lon = sens_data['lat'], sens_data['lon']

    if car_id in gl_failures:
        fs = gl_failures[car_id]
        for s in fs['sensors']:
            if s == "tire_pressure":
                sens_fail.extend([f"tire_{t}_fail" for t in sens_data['tire_pressure']])
                new_tire_press = {}
                for t in sens_data['tire_pressure']:
                    new_tire_press[t] = add_failure(s, sens_data['tire_pressure'][t], fs['severity'])
                sens_data['tire_pressure'] = new_tire_press
            elif s == "coolant_temp":
                sens_data['coolant_temp'] = add_failure(s, sens_data['coolant_temp'], fs['severity'])
                sens_fail.append("coolant_temp_fail")
            elif s == "battery_level":
                sens_data['battery_level'] = add_failure(s, sens_data['battery_level'], fs['severity'])
                sens_fail.append("battery_level_fail")
            elif s == "oil_pressure":
                sens_data['oil_pressure'] = add_failure(s, sens_data['oil_pressure'], fs['severity'])
                sens_fail.append("oil_pressure_fail")

        dest_lat = fs['repair_station']['lat']
        dest_lon = fs['repair_station']['lon']
        dist_to_repair = geodesic((lat, lon), (dest_lat, dest_lon)).meters
        
        idx_to_check = current_idx if current_idx is not None else info['idx']
        at_end = (idx_to_check >= len(info['route'])-1)
        
        if dist_to_repair <= ARRIVAL_THRESHOLD_M or at_end:
            print(f"{car_id}: Fixed at {fs['repair_station']['address']} station.")
            gl_failures.pop(car_id, None)
            info['vehicle_failed_once'] = True
            gl_plan_failures.pop(car_id, None)
            gl_cars_to_fail.discard(car_id)
            sens_fail = []

    return sens_fail

def emit_telemetry_point(car_id, info, sens_data, ts):
    tire_rounn = {}
    for k, v in sens_data['tire_pressure'].items():
        tire_rounn[k] = round(v, 2)
    point = {
        "vehicle_id": car_id,
        "route_id": info["route_id"],
        "segment_id": info["segment_id"], 
        "timestamp": ts.isoformat()+"Z",
        "lat": round(sens_data['lat'],6),
        "lon": round(sens_data["lon"],6),
        "speed": round(sens_data['speed'],2),
        "acceleration": round(sens_data['acceleration'],2),
        "heading": round(sens_data["heading"],2),
        "engine_temp": round(sens_data['engine_temp'],2),
        "brake_status": sens_data['brake_status'],
        "coolant_temp": round(sens_data['coolant_temp'],2),
        "battery_level": round(sens_data['battery_level'],2),
        "tire_pressure": tire_rounn,
        "oil_pressure": round(sens_data['oil_pressure'],2),
        "sensor_failures": sens_data.get('sensor_failures', [])
    }
    seg_buff[car_id] = []
    return point


def handle_finished_vehicles(done_tick,act_cars,stopp_dict,count_processed=False):
    global cars_done

    for car_id in done_tick:
        if car_id in act_cars:
            if act_cars[car_id]['route']:
                last_pt = act_cars[car_id]['route'][-1]
            else:
                last_pt = {'lat': None, 'lon': None}
            stopp_dict[car_id] = {
                "last_lat": last_pt['lat'],
                "last_lon": last_pt['lon'],
                "last_idx": act_cars[car_id].get('idx', 0),
                "vehicle_failed_once": act_cars[car_id].get('vehicle_failed_once', True)
            }
            
            if count_processed:
                cars_done += 1
            del act_cars[car_id]

    existing = load_file(STOPPED_CARS_FILE_PATH)
    existing.update(stopp_dict)

    with open(STOPPED_CARS_FILE_PATH, "w") as f:
        json.dump(existing, f, indent=2)
        
def process_active_vehicles_tick(act_cars, ts, stopp_dict, rep_station, count_processed=False):
    done_tick = []
    tick_points = []  
    act_cars_sort = sorted(list(act_cars.items()))
    for car_id, info in act_cars_sort:
        idx = info['idx']
        route = info['route']

        if not route or idx >= len(route):
            done_tick.append(car_id)
            continue

        sens_data = update_kinematics(car_id, info)

        schedule_failure_if_eligible(car_id, info, sens_data['lat'], sens_data['lon'], rep_station)
        activate_failure(car_id, info, idx, sens_data['lat'], sens_data['lon'])
        
        sens_data['sensor_failures'] = apply_active_failures(car_id, info, sens_data, idx)

        point = emit_telemetry_point(car_id, info, sens_data, ts)
        point['segment_id'] = info['segment_id']
        tick_points.append(point)

        if idx < len(route) - 1:
            info['idx'] += 1
        else:
            done_tick.append(car_id)

    handle_finished_vehicles(done_tick, act_cars, stopp_dict, count_processed=count_processed)

    return tick_points


def failure_eligibility(car_id, vehicle_failed_once):
    if not vehicle_failed_once and random.random() < TOTAL_FAILS:
        gl_cars_to_fail.add(car_id)
    else:
        gl_cars_to_fail.discard(car_id)


