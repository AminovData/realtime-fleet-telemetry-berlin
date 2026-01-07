
import os
import json
import threading
import redis
from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO
from helpers import *
from db_dash_handler import fetch_vehicle_docs, redis_listener
from config import REDIS_HOST,REDIS_PORT,REDIS_STREAM,REDIS_GROUP,CONSUMER,MONGO_URI, MONGO_DB, MONGO_HISTORY_COLLECTION

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
socketio = SocketIO(app, cors_allowed_origins="*")

cars_state = {}

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/vehicle_test")
def vehicle_dashboard_test():
    car_id = request.args.get("vehicle_id", "TEST_CAR")
    last_known = r.hgetall(f"vehicle:{car_id}:latest")
    
    if last_known and "sensor_failures" in last_known:
        last_known["sensor_failures"] = json.loads(last_known["sensor_failures"])
    
    if last_known:
        last_known_json = json.dumps(last_known)
    else:
        last_known_json = None
    
    return render_template(
        "specific_car.html",
        vehicle_id=car_id,
        last_known=last_known_json
    )


@app.route("/historical_dashboard")
def historical_dashboard():
    return render_template("historical_dashboard.html")


@app.route("/get_vehicle_overview", methods=["GET"])
def get_vehicle_overview():
    car_id = request.args.get("vehicle_id")
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    if not car_id:
        return jsonify({"error": "Missing vehicle_id"}), 400

    start_dt, end_dt = parse_date_range(start_date, end_date)
    docs = fetch_vehicle_docs(car_id, start_dt, end_dt, MONGO_URI, MONGO_DB, MONGO_HISTORY_COLLECTION)

    
    if not docs:
        return jsonify({"error": "Did not find data for {start_date} - {end_date}"}), 404

    segs = group_by_segments(docs)
    sorted_seg_ids, seg_colors, seg_markers = assign_colors_and_markers(segs)
    metrics = calc_trip_metrics(docs)

    return jsonify({
        "vehicle_id": car_id,
        "metrics": metrics,
        "segments": segs,
        "segment_colors": seg_colors,
        "segment_markers": seg_markers,
        "sorted_segment_ids": sorted_seg_ids
    })

@app.route("/get_vehicle_trends", methods=["GET"])
def get_vehicle_trends():
    car_id = request.args.get("vehicle_id")
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    if not car_id:
        return jsonify({"error": "Missing vehicle_id"}), 400

    start_dt, end_dt = parse_date_range(start_date, end_date)
    docs = fetch_vehicle_docs(car_id, start_dt, end_dt, MONGO_URI, MONGO_DB, MONGO_HISTORY_COLLECTION)

    if not docs:
        return jsonify({"error": "Did not find data for {start_date} - {end_date}"}), 404

    fail_time = extract_failure_timeline(docs)
    daily_labels, daily_speed, engine_tmp, daily_battery, daily_oil = aggregate_daily_metrics(docs)

    return jsonify({
        "vehicle_id": car_id,
        "failure_timeline": fail_time,
        "daily_labels": daily_labels,
        "daily_speed": daily_speed,
        "daily_engine_temp": engine_tmp,
        "daily_battery": daily_battery,
        "daily_oil": daily_oil
    })

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

threading.Thread(
    target=redis_listener,
    args=(r, socketio, cars_state, REDIS_STREAM, REDIS_GROUP, CONSUMER, fail_summary, parse_timestamp),daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8081, debug=False)

