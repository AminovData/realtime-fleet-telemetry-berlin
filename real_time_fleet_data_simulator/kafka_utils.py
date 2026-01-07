from kafka import KafkaProducer
import json

from config import KAFKA_TOPIC, KAFKA_BROKER_LIST



producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER_LIST,
    value_serializer=lambda x: json.dumps(x).encode()
    )

def send_to_kafka(segments):
    if producer:
        for seg in segments:
            producer.send(KAFKA_TOPIC, seg)
        producer.flush()
    else:
        for seg in segments:
            car_id = seg["vehicle_id"]
            print(f"Producer is not available. Skipping {len(segments)} segments")
