from datetime import datetime, timedelta
import pytz
from pymongo import MongoClient
from bson.objectid import ObjectId


DBURL = "mongodb+srv://walker:onesouth@thebigcluster-x0vu6.mongodb.net/test?retryWrites=false"

client = MongoClient(DBURL + ":27017")
db = client.PlugDJClone

collection = db['accountMetrics']

# res = collection.find({'_id': ObjectId('5c0371f2abad402084fbfd9d')})

# res = collection.update_one({'_id': ObjectId('5c0371f2abad402084fbfd9d')},{"$set": {
#                                                                                     "woots": 5,
#                                                                                     "mehs": 0,
#                                                                                     "grabs": 3
#                                                                                 }})

# from socketIO_client import SocketIO

# def handleNextVideo(data):
#     print(data['videoTitle'])
#     with open(file, 'w') as f:
#         f.write(data['videoTitle'])


# socketIO = SocketIO('https://plug-dj-clone-api.herokuapp.com)
# socketIO.on('Event_nextVideo', handleNextVideo)
# socketIO.wait()

sortedWoots = collection.find({}).sort("woots", -1)
sortedMehs = collection.find({}).sort("mehs", -1)
sortedGrabs = collection.find({}).sort("grabs", -1)

for item in sortedWoots:
    print(item)

print("***********")

for item in sortedMehs:
    print(item)

print("***********")

for item in sortedGrabs:
    print(item)


