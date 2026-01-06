import json
import redis
import pymongo
from kafka import KafkaConsumer
from bson import ObjectId
from config import KAFKA_BROKER_LIST,KAFKA_TOPIC,CONSUMER_GROUP,REDIS_HOST,REDIS_PORT,REDIS_DB,MONGO_URI,MONGO_DB,MONGO_HISTORY_COLLECTION,MONGO_DLQ_COLLECTION


consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER_LIST,
    group_id=CONSUMER_GROUP,
    auto_offset_reset='earliest',
    enable_auto_commit=True,        
    auto_commit_interval_ms=5000,   
    session_timeout_ms=30000,       
    heartbeat_interval_ms=8000,     
    max_poll_interval_ms=120000,    
    max_poll_records=100,
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)



r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

mongo_client = pymongo.MongoClient(MONGO_URI)
hist_collect = mongo_client[MONGO_DB][MONGO_HISTORY_COLLECTION]
dlq_collect = mongo_client[MONGO_DB][MONGO_DLQ_COLLECTION]

print("COSUMER STARTED:")


def process_for_redis(d):
    cleaned = {}
    for k, v in d.items():
        v_type = type(v)
        
        if v_type == bool:
            cleaned[k] = int(v)
        elif v_type == ObjectId:
            cleaned[k] = str(v)
        elif v is None:
            cleaned[k] = ''
        elif v_type == int or v_type == float or v_type == str:
            cleaned[k] = v
        else:
            cleaned[k] = json.dumps(v)
    return cleaned


for msg in consumer:
    point = msg.value
    car_id = point.get("vehicle_id", "unknown")
    cleann_pt = process_for_redis(point)

    try:
        
        r.hset(f"vehicle:{car_id}:latest", mapping=cleann_pt)
        r.rpush(f"vehicle:{car_id}:recent", json.dumps(cleann_pt))
        r.ltrim(f"vehicle:{car_id}:recent", -100, -1) 
        r.xadd("vehicle_stream", {"data": json.dumps(cleann_pt)}, maxlen=1000, approximate=True)

        hist_collect.insert_one(point)

        if point.get("sensor_failures"):
            r.publish("vehicle_alerts", json.dumps(cleann_pt))
        r.publish("vehicle_updates", json.dumps(cleann_pt))

        consumer.commit()
        print(f"------- Processed point for {car_id}")

    except Exception as e:
        print(f"ATTETION! Error processing the {car_id}: {e}")

        try:
            dlq_collect.insert_one({"msg": point, "err": str(e)})
            print(f"Sent point to MongoDB-DLQ:{car_id}")
        except Exception as dlq_err:
            print(f"ATTETION! Failed to send to MongoDB-DLQ:{dlq_err}")

        consumer.commit()
