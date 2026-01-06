import os
import json
import time
import random
from datetime import datetime, timedelta
from kafka_utils import send_to_kafka
from config import NUM_ACTIVE, MAX_UNIQUE_CARS, RESUME_FROM_LAST, TICK_SECONDS, BATCH_TIME, RESTART_HOURS,ROUTES_FILE_PATH,FIXING_STATIONS_FILE_PATH,STOPPED_CARS_FILE_PATH
from helpers import get_ors_route, interpolate_points, load_file
from vehicle import (
    spawn_vehicle,
    process_active_vehicles_tick,
    failure_eligibility,
    __initialize_vehicle_sensors
)


def load_routes_and_stations():
    with open(ROUTES_FILE_PATH, "r") as f:
        all_routes = json.load(f)
    with open(FIXING_STATIONS_FILE_PATH, "r") as f:
        rep_stations = json.load(f)
    return all_routes, rep_stations

def load_stopped_cars():
    if RESUME_FROM_LAST and os.path.exists(STOPPED_CARS_FILE_PATH):
        try:
            with open(STOPPED_CARS_FILE_PATH, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def main_simulation():
    all_routes, rep_stations = load_routes_and_stations()
    stopp_dict = load_stopped_cars()

    act_cars = {}
    ts = datetime.utcnow()
    uniq_created = 0

    try: 
        while uniq_created < MAX_UNIQUE_CARS and NUM_ACTIVE != 0:

            while len(act_cars) < NUM_ACTIVE:
                if uniq_created < MAX_UNIQUE_CARS:
                    rc = random.choice(all_routes)
                    car_id, info = spawn_vehicle(rc)
                    act_cars[car_id] = info
                    uniq_created += 1
                    print(f"Spawned new {car_id} ({uniq_created}/{MAX_UNIQUE_CARS})")
                else:
                    break

            ts += timedelta(seconds=TICK_SECONDS)
            tick_points = process_active_vehicles_tick(act_cars, ts, stopp_dict, rep_stations, count_processed=True)

            send_to_kafka(tick_points)
            time.sleep(BATCH_TIME)

            finished = [car_id for car_id, v in act_cars.items() if v['idx'] >= len(v['route'])]
            for car_id in finished:
                del act_cars[car_id]

            if uniq_created >= MAX_UNIQUE_CARS:
                print("Successes. All vehicles processed and repaired. Stopping simulation.")
                break
            
    except KeyboardInterrupt:
        print("Stopped Simulation")

    print(f"Processed {uniq_created}/{MAX_UNIQUE_CARS} unique vehicles")

    with open(STOPPED_CARS_FILE_PATH, "w") as f:
        json.dump(stopp_dict, f, indent=2)



def restart_stopped_cars():
    all_routes, rep_stations = load_routes_and_stations()

    stopp_dict = load_file(STOPPED_CARS_FILE_PATH)

    for hr in RESTART_HOURS:
        ts = datetime.utcnow() + timedelta(hours=hr)
        print(f"\nRestarting vehicles after +{hr}hr")

        act_cars = {}
        stopped_items = list(stopp_dict.items())
        for car_id, data in stopped_items:
            start_lat, start_lon = data['last_lat'], data['last_lon']
            failed_before = data['vehicle_failed_once']
            

            dest_route = random.choice(all_routes)
            dest = dest_route['route'][-1] 

            ors_route = get_ors_route(start_lat, start_lon, dest['lat'], dest['lon'])

            if ors_route:
                route = interpolate_points(ors_route)
            else:
                route = interpolate_points([{'lat': start_lat, 'lon': start_lon}, {'lat': dest['lat'], 'lon': dest['lon']}])

            info = {
                'route_id': dest_route['route_id'],
                'segment_id': f"seg_{car_id}_{int(time.time())}",
                'route': route,
                'idx': 0,  
                'destination': route[-1],
                'vehicle_failed_once': failed_before
            }

            __initialize_vehicle_sensors(car_id)

            failure_eligibility(car_id, failed_before)

            act_cars[car_id] = info
            print(f"Restarted {car_id}")

        while act_cars:
            ts += timedelta(seconds=TICK_SECONDS)
            segs_tick = process_active_vehicles_tick(act_cars, ts, stopp_dict, rep_stations, count_processed=True)
            send_to_kafka(segs_tick)
            time.sleep(0.8)

        print(f"Done with +{hr}h restart")




MENU = {
    "run_main": True,
    "run_restart": False , 
}

if __name__ == "__main__":
    if MENU["run_main"]:
        main_simulation()

    if MENU["run_restart"]:
        print("Restarting simulation!")
        restart_stopped_cars()