import os

from dotenv import load_dotenv
load_dotenv()

#REDIS
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_STREAM = os.getenv("REDIS_STREAM")
REDIS_GROUP = os.getenv("REDIS_GROUP")
CONSUMER = os.getenv("CONSUMER")



#MONGO
MONGO_URI= os.getenv("MONGO_URI")
MONGO_DB= os.getenv("MONGO_DB")
MONGO_HISTORY_COLLECTION = os.getenv("MONGO_HISTORY_COLLECTION")






