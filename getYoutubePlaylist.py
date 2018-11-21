import requests
import json

API_KEY = 'AIzaSyD7edp0KrX7oft2f-zL2uEnQFhW4Uj5OvE'



# This was for testing but im pushing it anyways

def getYoutubePlaylist():
    
    numOfResults = 50
    playlistId = 'PLT9vbDD0IgbZZwoTXv3-o2Bg5eGdvy7fJ'
    pageToken = ''

    finished = False

    playlist = []

    while(not finished):
        res = executeRequest(playlistId, numOfResults, pageToken)

        if('nextPageToken' not in res):
            finished = True
        else:
            pageToken = res['nextPageToken']


        for item in res['items']:
            videoId = item['snippet']['resourceId']['videoId']
            videoTitle = item['snippet']['title']

            video = {'videoTitle': videoTitle, 'videoId': videoId}
            playlist.append(video)


    print(JSONEncoder().encode(playlist))
    return playlist

    

def executeRequest(playlistId, numOfResults, nextPageToken=''):
    global API_KEY

    url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId=' + playlistId + '&key=' + API_KEY + '&maxResults=' + str(numOfResults) + '&pageToken=' + nextPageToken
    r = requests.get(url)
    return json.loads(r.text)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId) or isinstance(o, Timestamp) or isinstance(o, bytes):
            return str(o)
        return json.JSONEncoder.default(self, o)

if __name__ == '__main__':
    getYoutubePlaylist()