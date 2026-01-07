import os

from dotenv import load_dotenv
load_dotenv()


# Redis
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")

# AWS
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# MongoDB 
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")
MONGO_HISTORY_COLLECTION = os.getenv("MONGO_HISTORY_COLLECTION")
MONGO_DLQ_COLLECTION = os.getenv("MONGO_DLQ_COLLECTION")


# Kafka
KAFKA_BROKER_LIST = os.getenv("KAFKA_BROKERS").split(",")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP")

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")

# ORS
ORS_API_KEY = os.getenv("ORS_API_KEY")
ORS_RETRIES = 1
ORS_DELAY = 2.5

# Car Simulation Settings
TOTAL_CARS = 100 
NUM_ACTIVE = 10
MAX_UNIQUE_CARS = 20
RESUME_FROM_LAST = False
TICK_SECONDS = 1
BATCH_TIME = 0.2

# Failure and Cordinate Points Parameters
INTERP_STEP_M = 20
TOTAL_FAILS = 0.7
SENSOR_SEVERITY = ["mild", "medium", "serious"]
RESTART_HOURS =  [24,48,72,96,120,144] # EX : in hoours [2,3,4,5,6,7]
ARRIVAL_THRESHOLD_M = 100


# Data File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

ROUTES_FILE_PATH = os.path.join(DATA_DIR, "routes_1000_interpolated.json")
FIXING_STATIONS_FILE_PATH = os.path.join(DATA_DIR, "berlin_fixing_stations.json")
STOPPED_CARS_FILE_PATH = os.path.join(DATA_DIR, "stopped_vehicles.json")






