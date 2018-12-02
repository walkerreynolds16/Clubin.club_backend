from datetime import datetime, timedelta
import pytz
from pymongo import MongoClient

DBURL = "mongodb+srv://walker:onesouth@thebigcluster-x0vu6.mongodb.net/test?retryWrites=false"

client = MongoClient(DBURL + ":27017")
db = client.PlugDJClone

collection = db['videoHistory']

now = datetime.utcnow()
threshold = now - timedelta(hours=12, minutes=0)

print(threshold)

res = collection.find({'timeStamp':{'$gte': threshold}})

for item in res:
    print(item)