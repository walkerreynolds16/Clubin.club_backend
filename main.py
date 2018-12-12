import eventlet
eventlet.monkey_patch()

import os
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

from flask import Flask, request, jsonify, json
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId, Timestamp, json_util
from flask_socketio import SocketIO, send, emit


import isodate
import json
import requests
from datetime import datetime, timedelta
import threading
import time
import pytz


version = '0.453'

youtubeAPIKey = 'AIzaSyD7edp0KrX7oft2f-zL2uEnQFhW4Uj5OvE'
isSomeoneDJing = False

currentDJ = ''
currentVideoStartTime = None
currentVideoId = None
delayTime = 1.0
currentVideoTitle = ''

determiningVideo = False
recentInsertedId = None

chaosSkipMode = False

videoTimer = None

clients = []
djQueue = []
unfinishedClients = []

wooters = []
mehers = []
grabbers = []
skippers = []

DBURL = "mongodb+srv://walker:onesouth@thebigcluster-x0vu6.mongodb.net/test?retryWrites=true"
# DBURL = 'localhost'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'onesouth'
socketio = SocketIO(app)
CORS(app)


@app.route('/getPlaylists')
def getPlaylists():
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['playlists']

    playlist = collection.find_one({'username': request.args['username']})

    if(playlist != None):
        return JSONEncoder().encode(playlist)
    else:
        return JSONEncoder().encode([])


@app.route('/getAdmins', methods=['GET'])
def getAdmins():
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['admins']

    q = collection.find({})

    admins = []
    for admin in q:
        admins.append(admin['username'])

    return JSONEncoder().encode(admins)

@app.route('/addVideoToPlaylist', methods=['POST'])
def addVideoToPlaylist():

    username = request.json['username']
    playlistTitle = request.json['playlistTitle']
    videoId = request.json['videoId']
    videoTitle = request.json['videoTitle']

    # If the user that just added a video doesn't have an entry in the playlist db, change the playlist title to default
    if(playlistTitle is ''):
        playlistTitle = 'default'

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    newVideo = {'videoId': videoId, 'videoTitle': videoTitle}

    # print(videoTitle)

    doesUserExist = collection.find_one({'username': username})

    # If the user doesn't exist in the playlists db, make a new entry for them
    if(not doesUserExist):
        result = collection.insert_one({'username': username, 'playlists': [
                                       {'playlistTitle': playlistTitle, 'playlistVideos': []}]})

    # # Try to find a document that has the requested username
    result = collection.update_one(
        {'$and': [{'playlists.playlistTitle': playlistTitle},
                  {'username': username}]},
        {'$push': {'playlists.$.playlistVideos': newVideo}},
        upsert=True)

    return JSONEncoder().encode(result.raw_result)


@app.route('/setPlaylist', methods=['POST'])
def setPlaylist():

    playlistVideos = request.json['playlistVideos']
    playlistTitle = request.json['playlistTitle']
    username = request.json['username']

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    # Check if user exists yet
    doesUserExist = collection.find_one({'username': username})

    # If user doesn't exist, make a new document for them
    if(not doesUserExist):
        playlist = {'playlistTitle': playlistTitle, 'playlistVideos': playlistVideos}
        result = collection.insert_one({'username': username, 'playlists': [playlist], 'currentPlaylist': playlist})
        return JSONEncoder().encode(result.acknowledged)

    else: # If user exist, just set the playlist like normal
        doesPlaylistExist = collection.find_one({'$and': [{'playlists.playlistTitle': playlistTitle}, {'username': username}]})
        # print(doesPlaylistExist)
        result = None

        if(doesPlaylistExist == None):
            newPlaylist = {'playlistTitle': playlistTitle,
                        'playlistVideos': playlistVideos}
            result = collection.update_one(
                {'username': username},
                {'$push': {'playlists': newPlaylist}})

        else:
            result = collection.update_one(
                {'$and': [{'playlists.playlistTitle': playlistTitle},{'username': username}]},
                {'$set': {'playlists.$.playlistVideos': playlistVideos}},
                upsert=True)

        return JSONEncoder().encode(result.raw_result)

@app.route('/getRecentVideos', methods=['GET'])
def getRecentVideos():
    mins = request.args['minutes']
    hrs = request.args['hours']

    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['videoHistory']

    now = datetime.utcnow()
    threshold = now - timedelta(hours=int(hrs), minutes=int(mins))


    res = collection.find({'timeStamp':{'$gte': threshold}})

    resList = []

    for item in res:
        print(item)
        resList.append(item)

    return json.dumps(resList, default=json_util.default)



@app.route('/deleteVideoInPlaylist', methods=['POST'])
def deleteVideoInPlaylist():

    username = request.json['username']
    playlistTitle = request.json['playlistTitle']
    videoId = request.json['videoId']
    videoTitle = request.json['videoTitle']

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    video = {'videoId': videoId, 'videoTitle': videoTitle}

    print(videoTitle)

    # # Try to find a document that has the requested username
    result = collection.update_one(
        {'$and': [{'playlists.playlistTitle': playlistTitle},
                  {'username': username}]},
        {'$pull': {'playlists.$.playlistVideos': video}},
        upsert=False)

    return JSONEncoder().encode(result.raw_result)


@app.route('/setCurrentPlaylist', methods=['POST'])
def setCurrentPlaylist():
    playlist = request.json['newCurrentPlaylist']
    username = request.json['username']

    # print(playlist)

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    currentPlaylist = collection.find_one({'username': username})

    if(currentPlaylist != None):
        res = collection.update_one(
            {'username': username},
            {'$set': {'currentPlaylist': playlist}})


        return json.dumps([])
    else:
        return "User doesn't exist yet"

@app.route('/setAllPlaylist', methods=['POST'])
def setAllPlaylist():
    username = request.json['username']
    playlists = request.json['playlists']

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    # Check if user exists yet
    doesUserExist = collection.find_one({'username': username})

    if(doesUserExist):
        res = collection.update_one(
            {'username': username},
            {'$set': {'playlists': playlists}})

        return JSONEncoder().encode(res.raw_result)
    else:
        return "User not in database"

@app.route('/deletePlaylistDocument', methods=['POST'])
def deletePlaylistDocument():
    username = request.json['username']

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    res = collection.delete_one({'username': username})

    return JSONEncoder().encode(res.deleted_count)


def isUsernameInClients(username):
    for user in clients:
        if(user['user'] == username):
            return True

    return False

@app.route('/login', methods=['POST'])
def login():
    username = request.json['username']
    password = request.json['password']

    if(len(username) > 32 or len(password) > 128 or 'accounts' in username or 'accounts' in password or 'playlist' in username or 'playlist' in password):
        return 'fuck you'

    print(clients)
    if(isUsernameInClients(username)):
        print('user already connected')
        return 'user already connected'

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['accounts']

    doesUsernameExist = collection.find_one({'username': username})
    # print(JSONEncoder().encode(doesUsernameExist))

    # print("logging in...")

    # The username does not exist, make a new entry in the accounts DB
    if(doesUsernameExist == None):
        result = collection.insert_one({'username': username, 'password': password})

        # To make things easier down the line, generate a new playlists record in the db
        # generateNewPlaylistRecord(username)
        return 'success'

    else:
        if(doesUsernameExist['password'] == password):
            # print("***** Right Password ******")
            return 'success'
        else:
            # print("***** Wrong Password ******")
            return 'failure'


def generateNewPlaylistRecord(username):
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    document = {"username":username, "playlists":[], "currentPlaylist":{"playlistTitle":"default", "playlistVideos":[]}}

    result = collection.insert_one(document)

    print("Generating new playlist record result")
    print(result)


@app.route('/getCurrentVideo', methods=['GET'])
def getCurrentVideoPlaying():
    global currentVideoStartTime
    global currentVideoId
    global currentDJ
    global currentVideoTitle

    if(currentVideoId != None):
        currentTime = time.time()
        timeElapsed = int(currentTime - currentVideoStartTime)


        videoData = {'videoId': currentVideoId, 'startTime': timeElapsed, 'currentDJ': currentDJ, 'currentVideoTitle': currentVideoTitle}
        return json.dumps(videoData)
    else:
        # No video is playing
        return 'No one playing'

@app.route('/getYoutubePlaylist', methods=['GET'])
def getYoutubePlaylist():
    playlistId = request.args['playlistId']
    playlist = createYoutubePlaylistObject(playlistId)

    return JSONEncoder().encode(playlist)

@app.route('/createPlugDJPlaylistFromYoutubePlaylist', methods=['POST'])
def createPlugDJPlaylistFromYoutubePlaylist():
    playlistId = request.json['playlistId']
    newPlaylistTitle = request.json['newPlaylistTitle']
    username = request.json['username']

    # Create playlist Object from YouTube data
    newPlaylistVideos = createYoutubePlaylistObject(playlistId)

    newPlaylist = {'playlistVideos': newPlaylistVideos, 'playlistTitle': newPlaylistTitle}

    # Connect to database and get instance of the DB
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['playlists']

    doesUserExist = collection.find_one({'username': username})

    # User doesn't exist yet in the playlists collection
    if(not doesUserExist):
        result = collection.insert_one({'username': username, 'playlists': [newPlaylist], 'currentPlaylist': newPlaylist})
        return JSONEncoder().encode(result.acknowledged)
    else:
        res = collection.update_one({'username': username}, {'$push': {'playlists': newPlaylist}})
        return JSONEncoder().encode(res.raw_result)


def createYoutubePlaylistObject(playlistId):
    numOfResults = 50
    pageToken = ''
    finished = False
    playlist = []

    while(not finished):
        # Get json data for the next 50 videos in the playlist
        res = executeRequest(playlistId, numOfResults, pageToken)
        
        # If nextPageToken is not in the response, then we have received all of the videos and can now finish our requests
        if('nextPageToken' not in res):
            finished = True
        else:
            pageToken = res['nextPageToken']

        # Extract the data that we want from the response and add it to a playlist list
        for item in res['items']:
            videoId = item['snippet']['resourceId']['videoId']
            videoTitle = item['snippet']['title']

            video = {'videoTitle': videoTitle, 'videoId': videoId}
            playlist.append(video)


    return playlist
    

def executeRequest(playlistId, numOfResults, nextPageToken=''):
    url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId=' + playlistId + '&key=' + youtubeAPIKey + '&maxResults=' + str(numOfResults) + '&pageToken=' + nextPageToken
    r = requests.get(url)
    return json.loads(r.text)

@app.route('/getCurrentVersion', methods=['GET'])
def getCurrentVersion():
    global version

    return json.dumps({'version': version})

@app.route('/getCurrentVideoMetrics', methods=['GET'])
def getCurrentVideoMetrics():
    global wooters
    global mehers
    global grabbers

    return json.dumps({'wooters': wooters, 'mehers': mehers, 'grabbers': grabbers})

@app.route('/getDJQueue', methods=['GET'])
def getDJQueue():
    global djQueue
    return json.dumps(djQueue)


@socketio.on('Event_userConnected')
def handleConnection(user):
    print(user + ' is connecting')

    clients.append({"user": user, "clientId": request.sid})

    print(user + ' is joining the unfinished clients')
    

    # if someone is playing a video, the new connection must be added to the unfinished clients
    if(isSomeoneDJing):
        unfinishedClients.append({'user': user, 'clientId': request.sid})

    print("unfinishedClients")
    print(unfinishedClients)

    print("clients")
    print(clients)

    data = {"user": user, "clients": clients, 'djQueue': djQueue, 'skippers': skippers, 'chaosSkipMode': chaosSkipMode}

    socketio.emit('Event_userConnecting', data, broadcast=True)
    handleChatMessage({'user': 'Server', 'message': user + ' has connected'})
    sendUpdatedLeaderboards()


@socketio.on('Event_userDisconnected')
def handleDisconnection(user):
    global unfinishedClients
    global clients
    global djQueue
    global skippers

    print(user + " has disconnected")
    
    # find user in clients and remove them
    for item in clients:
        if(item['user'] == user):
            clients.remove(item)

    for item in unfinishedClients:
        if(item['user'] == user):
            unfinishedClients.remove(item)

    for item in djQueue:
        if(item == user):
            djQueue.remove(item)

    for item in skippers:
        if(item == user):
            skippers.remove(item)

    global currentDJ
    global isSomeoneDJing

    if(user == currentDJ):
        currentDJ = ''
        isSomeoneDJing = False
        stopVideo()
        determineNextVideo()

    


    print("clients")
    print(clients)

    handleChatMessage({'user': 'Server', 'message': user + ' has disconnected'})

    data = {'user': user, 'clients': clients, 'djQueue': djQueue, 'skippers': skippers}

    socketio.emit('Event_userDisconnecting', data, broadcast=True)



@socketio.on('Event_joinDJ')
def handleJoinDJ(data):
    print(json.dumps(data))

    global isSomeoneDJing
    global currentDJ

    user = data['user']

    djQueue.append(user)

    print(user + ' has joined the dj queue')
    print(djQueue)
    print('\n')

    if(isSomeoneDJing == False):
        nextDJ = djQueue.pop(0)
        currentDJ = nextDJ
        print('CurrentDJ in handle join dj = ' + currentDJ)
        sendNewVideoToClients(nextDJ)
        isSomeoneDJing = True


    socketio.emit('Event_DJQueueChanging', djQueue, broadcast=True)


@socketio.on('Event_sendChatMessage')
def handleChatMessage(data):
    user = data['user']
    message = data['message']
    tz = pytz.timezone('America/New_York')
    time = datetime.now(tz).strftime("%H:%M:%S")

    # print(user + ' : ' + message)

    emit('Event_receiveChatMessage', {'time':time, 'user': user, 'message': message}, broadcast=True)


@socketio.on('Event_leaveDJ')
def handleLeavingDJ(data):
    
    print(json.dumps(data))

    global currentDJ
    global isSomeoneDJing
    global unfinishedClients

    user = data['user']
    print(user + " is leaving the dj queue")

    if(user == currentDJ):
        currentDJ = ''
        isSomeoneDJing = False
        unfinishedClients = []

        determineNextVideo()

    else:
        djQueue.remove(user)
        socketio.emit('Event_DJQueueChanging', djQueue, broadcast=True)


    print("DJ Queue after leaving")
    print(djQueue)
        

@socketio.on('Event_skipCurrentVideo')
def handleSkipRequest(data):
    # for now, i guess just determine the next video
    # TODO count the amount of skip requests and only skip when the majority of people want to skip

    global unfinishedClients
    global clients
    global chaosSkipMode

    username = data['user']
    isSkipping = data['isSkipping']
    override = data['overrideSkip']
    
    if(override):
        handleChatMessage({'user':'Server', 'message': 'This video has been skipped by the DJ or an admin'})
        determineNextVideo()
    elif(chaosSkipMode):
        handleChatMessage({'user':'Server', 'message': 'This video has been skipped by ' + username})
        determineNextVideo()
    else:
        if(isSkipping):
            skippers.append(username)
        else:
            skippers.remove(username)

        print("Skippers = ")
        print(skippers)


        resData = {'skippers': skippers}    

        socketio.emit('Event_skipChanged', resData, broadcast=True)

        skipPercent = float(len(skippers) / len(clients))

        if(skipPercent > .50):
            handleChatMessage({'user':'Server', 'message':'The video has been skipped by ' + str(skippers)})
            determineNextVideo()
    
@socketio.on('Event_toggleChaosSkipMode')
def toggleChaosSkipMode():
    global chaosSkipMode

    chaosSkipMode = not chaosSkipMode
    
    socketio.emit('Event_chaosSkipModeChanged', chaosSkipMode, broadcast=True)

    if(chaosSkipMode):
        handleChatMessage({'user': 'Server', 'message': 'Chaos Skip Mode has been enabled'})
    else:
        handleChatMessage({'user': 'Server', 'message': 'Chaos Skip Mode has been disabled'})


@socketio.on('Event_userFinishedVideo')
def handleUserFinishingVideo(user):
    global unfinishedClients
    global clients
    global determiningVideo

    print(user + ' finishing watching the video')

    if(not determiningVideo):
        for item in unfinishedClients:
            if(item['user'] == user):
                unfinishedClients.remove(item)

        clientsLength = len(clients)
        unfinishedClientsLength = len(unfinishedClients)
        numOfFinishedClients = clientsLength - unfinishedClientsLength

        print('All Clients')
        print(clients)
        print()

        print('Unfinished clients')
        print(unfinishedClients)
        print()

        finishedClientsPercentage = float(numOfFinishedClients / clientsLength)

        print('finishedClientsPercentage = ' + str(finishedClientsPercentage))

        if(finishedClientsPercentage >= .66):
            determiningVideo = True
            determineNextVideo()
    

@socketio.on('Event_Woot')
def handleUserWooting(data):
    global wooters

    if(data['wooting']):
        wooters.append(data['user'])
    else:
        wooters.remove(data['user'])

    resData = {'wooters': wooters}

    socketio.emit('Event_wootChanged', resData, broadcast=True)

    # Ternary Operator, but i dont like how it looks
    # updateaccountMetrics(currentDJ, 'woot', 1) if data['wooting'] else updateaccountMetrics(currentDJ, 'woot', -1)
    if(data['wooting']):
        updateaccountMetrics(currentDJ, 'woot', 1)
    else:
        updateaccountMetrics(currentDJ, 'woot', -1)

    sendUpdatedLeaderboards()
    
    


@socketio.on('Event_Meh')
def handleUserMehing(data):
    global mehers

    if(data['mehing']):
        mehers.append(data['user'])
    else:
        mehers.remove(data['user'])

    resData = {'mehers': mehers}

    socketio.emit('Event_mehChanged', resData, broadcast=True)

    if(data['mehing']):
        updateaccountMetrics(currentDJ, 'meh', 1)
    else:
        updateaccountMetrics(currentDJ, 'meh', -1)

    sendUpdatedLeaderboards()
    

@socketio.on('Event_Grab')
def handleUserGrabbing(data):
    global grabbers

    grabbers.append(data['user'])

    data = {'grabbers': grabbers}

    socketio.emit('Event_grabChanged', data, broadcast=True)

    updateaccountMetrics(currentDJ, 'grab', 1)

    sendUpdatedLeaderboards()


def sendUpdatedLeaderboards():
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['accountMetrics']

    sortedWoots = collection.find({}).sort("woots", -1)

    resWoots = []

    for item in sortedWoots:
        item.pop('_id', None)
        resWoots.append(item)
    
    socketio.emit('Event_leaderboardChanged', resWoots, broadcast=True)    




# Function called when woot/meh/grab is received, updates DB with new woots metrics
# type = "woot" or "meh" or "grab"
# inc = 1 or -1
def updateaccountMetrics(username, type, inc):
    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    # Get instance of the playlist collection
    collection = db['accountMetrics']

    doesUserExit = collection.find_one({'username': username})

    if(doesUserExit == None):
        woots = 0
        mehs = 0
        grabs = 0

        if(type == 'woot'):
            woots += 1
        elif(type == 'meh'):
            mehs += 1
        elif(type == 'grab'):
            grabs += 1

        res = collection.insert_one({'username': username, 'woots': woots, 'mehs': mehs, 'grabs': grabs})

        # print("Update account Metrics Res")
        # print(res)

    else:
        woots = doesUserExit["woots"]
        mehs = doesUserExit["mehs"]
        grabs = doesUserExit["grabs"]

        res = None

        if(type == 'woot'):
            # woots += inc
            res = collection.update_one({'username': username}, {'$set': {'woots': doesUserExit['woots'] + inc}})
        elif(type == 'meh'):
            # mehs += inc
            res = collection.update_one({'username': username}, {'$set': {'mehs': doesUserExit['mehs'] + inc}})
        elif(type == 'grab'):
            # grabs += inc
            res = collection.update_one({'username': username}, {'$set': {'grabs': doesUserExit['grabs'] + inc}})

        # print("Update account Metrics Res")
        # print(res)
        



def sendNewVideoToClients(nextUser):
    # Get next video from next DJ
    user = None
    for item in clients:
        if(item['user'] == nextUser):
            user = item

    currentPlaylist = None

    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['playlists']

    playlist = collection.find_one({'username': nextUser})['currentPlaylist']

    if(playlist != None):
        if(len(playlist['playlistVideos']) != 0):
            nextVideo = playlist['playlistVideos'].pop(0)
        else:
            print('Next User doesn\'t have videos in their current playlist. Next User = ' + nextUser)
            determineNextVideo()
            return
    else:
        print('Next User doesn\'t exists. Next User = ' + nextUser)
        determineNextVideo()
        return


    data = {'videoId': nextVideo['videoId'], 'videoTitle': nextVideo['videoTitle'], 'username': nextUser}

    global currentVideoId
    global currentVideoTitle
    global determiningVideo
    currentVideoId = data['videoId']
    currentVideoTitle = data['videoTitle']

    print('\n ****************** \n')

    print("Username = " + str(data['username']))
    print("Video Id = " + str(data['videoId']))
    print("Video Title = " + str(data['videoTitle'].encode("utf-8")))
    global currentDJ
    print("Current DJ = " + str(currentDJ))

    print('\n ****************** \n')

    
    print('emitting to clients \n')
    socketio.emit('Event_nextVideo', data, broadcast=True)

    determiningVideo = False

    global unfinishedClients
    unfinishedClients = []
    # Adding all connected clients to a waiting list
    unfinishedClients.extend(clients)

    global currentVideoStartTime
    global delayTime
    global videoTimer

    duration = getVideoDuration(data['videoId'])

    print('Video Duration = ' + str(duration))
    # videoTimer = threading.Timer(duration + delayTime, determineNextVideo)
    # videoTimer.start()
    currentVideoStartTime = time.time()

    playlist['playlistVideos'].append(nextVideo)

    collection.update_one({'username': nextUser}, {'$set': {'currentPlaylist': playlist}})

    storeVideoInHistory({"videoId": nextVideo['videoId'], 'videoTitle': nextVideo['videoTitle']}, nextUser)


    return None

def storeVideoInHistory(video, nextUser):
    tz = pytz.timezone('America/New_York')
    currentTime2 = datetime.now(tz)
    print(currentTime2)

    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['videoHistory']

    data = {"video": video, "username": nextUser, "timeStamp": currentTime2, "woots": 0, "mehs": 0, "grabs": 0}

    res = collection.insert_one(data)
    print(res.inserted_id)

    global recentInsertedId
    recentInsertedId = res.inserted_id

def updateVideoHistoryMetrics(wooters, mehers, grabbers):
    global recentInsertedId

    client = MongoClient(DBURL + ":27017")
    db = client.PlugDJClone

    collection = db['videoHistory']

    if(recentInsertedId != None):
        res = collection.update_one({'_id': ObjectId(recentInsertedId)},{"$set": {
                                                                                    "woots": len(wooters),
                                                                                    "mehs": len(mehers),
                                                                                    "grabs": len(grabbers)
                                                                                }})
        print(res)


def determineNextVideo():
    # print('timer done ***************')
    global currentDJ
    global currentVideoId
    global isSomeoneDJing

    global wooters
    global mehers
    global grabbers
    global skippers

    updateVideoHistoryMetrics(wooters, mehers, grabbers)

    wooters = []
    mehers = []
    grabbers = []
    skippers = []
    unfinishedClients = []

    print("** Determining next video **")
    print('Current DJ in determineVideo = ' + currentDJ)

    if(currentDJ != ''):
        print("Adding " + currentDJ + " to queue")
        djQueue.append(currentDJ)

    print("Current DJ Queue")
    print(djQueue)

    if(len(djQueue) != 0):
        nextUser = djQueue.pop(0)
        currentDJ = nextUser
        isSomeoneDJing = True
        sendNewVideoToClients(nextUser)
        
        socketio.emit('Event_DJQueueChanging', djQueue, broadcast=True)
    else:
        currentVideoId = None
        print('No more DJs in queue')
        stopVideo()

def stopVideo():
    # This works but it isn't graceful
    # data = {'videoId': '', 'videoTitle': '', 'username': ''}
    # socketio.emit('Event_nextVideo', data, broadcast=True)
    print("Stopping video")
    # global videoTimer
    # if(videoTimer != None):
    #     videoTimer.cancel()
    #     videoTimer = None

    global unfinishedClients
    unfinishedClients = []
    
    socketio.emit('Event_stopVideo', broadcast=True)
    


def getVideoDuration(videoId):
    url = 'https://www.googleapis.com/youtube/v3/videos?key=' + youtubeAPIKey + '&id=' + str(videoId) + '&part=contentDetails'
    r = requests.get(url)
    res = json.loads(r.text)
    duration = res['items'][0]['contentDetails']['duration']

    duration = isodate.parse_duration(duration).total_seconds()
    return duration




class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId) or isinstance(o, Timestamp) or isinstance(o, bytes):
            return str(o)
        return json.JSONEncoder.default(self, o)


if __name__ == '__main__':
    socketio.run(app, debug=True)
