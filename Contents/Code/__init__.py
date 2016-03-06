NAME = 'CNN'
PREFIX = '/video/cnn'

BASE_URL = "http://www.cnn.com"
VIDEOS = "http://www.cnn.com/video/#"
DIGITAL_SHORTS = "http://www.cnn.com/specials/videos/digital-shorts"
# This gets the related video sections http://www.cnn.com/specials/videos/digital-shorts
RELATED_JSON = 'http://www.cnn.com/video/data/3.0/video/%s/relateds.json'
RELATED_SECTION = ['Business', 'Entertainment', 'Health', 'Justice', 'Living', 'CNNMoney', 'Politics', 'Style', 'Technology', 'Travel', 'TV', 'US', 'World', 'Weather']
# Search for just videos with options for pages(page), npp(number per page), searchquery(text)
SEARCH_URL  = 'http://searchapp.cnn.com/search/query.jsp?page=%s&npp=30&start=%s&text=%s&type=all&sort=relevance&collection=VIDEOS'
RE_SEARCH_JSON  = Regex('"results":\[(.+?)\],"didYouMean"')

# REGEX for pulling the json for the video carousel at the top of a page
RE_JSON  = Regex('currentVideoCollection = (.+?),currentVideoCollectionId')
# Also the playlists vary and can be chosen by adding this to the end of a video url - /video/playlists/climate-change/
# or /video/playlists/top-news-videos/, /video/playlists/most-popular-domestic/, /video/playlists/stories-worth-watching/
# BUT YOU CAN ONLY FIND THEM WHEN YOU OPEN A VIDEO. PROBABLY BEST TO PULL THE MAIN PAGE AND ATTACH A PLYALIST TO EACH
####################################################################################################
def Start():

    ObjectContainer.title1 = NAME
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'

####################################################################################################
@handler(PREFIX, NAME)
def MainMenu():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key = Callback(VideoSections, title = 'All Videos', url=VIDEOS), title = 'All Videos'))
    oc.add(DirectoryObject(key = Callback(VideoSections, title = 'Digital Shorts', url='http://www.cnn.com/specials/videos/digital-shorts'), title = 'Digital Shorts'))
    oc.add(DirectoryObject(key = Callback(PlaylistPull, title = 'Video Playlists'), title = 'Video Playlists'))
    oc.add(InputDirectoryObject(key=Callback(VideoSearch), title='Search for CNN Videos', summary="Click here to search for videos", prompt="Search for videos by entering key words"))

    return oc

####################################################################################################
# This function pulls the sections listed in a video page
@route(PREFIX + '/videosections')
def VideoSections(title, url):

    oc = ObjectContainer()
    html = HTML.ElementFromURL(url)

    for section in html.xpath('//section'):
        try: title = section.xpath('./@data-zone-label')[0]
        except: continue
        Log('this is a test %s' %title)
        oc.add(DirectoryObject(
            key = Callback(VideosMenu, title = title, url = url), 
            title = title))
           
    return oc

####################################################################################################
# This function pulls the videos listed in a section of the main video page
@route(PREFIX + '/videosmenu')
def VideosMenu(title, url):

    oc = ObjectContainer(title2 = title)

    html = HTML.ElementFromURL(url)

    for video in html.xpath('//section[@data-zone-label="%s"]//article' %title):
        vid_url = video.xpath('.//h3/a/@href')[0].split('/video/playlists')[0]
        if not vid_url.startswith('http'):
            vid_url = BASE_URL + vid_url
        # these are videos that go to the cnn.go website and do not work
        if vid_url.startswith('http://cnn.it'):
            continue
        if not '/video' in vid_url:
            continue
        title = video.xpath('.//h3/a/span[@class="cd__headline-text"]//text()')[0].strip()
        try: thumb = video.xpath('.//img/@data-src-large')[0]
        except: thumb = ''
        try: duration = Datetime.MillisecondsFromString(video.xpath('.//i/@data-post-text')[0])
        except: duration = 0

        oc.add(VideoClipObject(
            url = vid_url,
            title = title,
            thumb = Resource.ContentsOfURLWithFallback(url=thumb),
            duration = duration))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    else:
        return oc
####################################################################################################
# This function creates the list of known sections for the related json playlists
@route(PREFIX + '/playlistpull')
def PlaylistPull(title):  

    oc = ObjectContainer(title2 = title)

    for item in RELATED_SECTION:
        playlist_url = RELATED_JSON %item.lower()
        oc.add(DirectoryObject(
            key = Callback(PlaylistJSON, title = item, url = playlist_url), 
            title = item))

    return oc

####################################################################################################
# This function uses the related json url to pull a playlist of top videos
@route(PREFIX + '/playlistjson')
def PlaylistJSON(title, url):  

    oc = ObjectContainer(title2 = title)

    json = JSON.ObjectFromURL(url)

    for item in json['videos']:
        url = BASE_URL + item['clickback_url']
        duration = Datetime.MillisecondsFromString(item['duration'])

        oc.add(VideoClipObject(
            url = url,
            title = item['headline'],
            summary = item['description'],
            thumb = Resource.ContentsOfURLWithFallback(url=item['fullsize_url']),
            duration = duration))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    else:
        return oc

####################################################################################################
@route(PREFIX + '/videosearch', page=int, start=int)
def VideoSearch(query, page=1, start=1):

    oc = ObjectContainer()

    query_url = SEARCH_URL %(str(page), str(start), String.Quote(query, usePlus = True))
    content = HTTP.Request(query_url).content
    json_data = RE_SEARCH_JSON.search(content).group(1)
    json = JSON.ObjectFromString(json_data)

    for item in json:
        url = item['url']
        if not url.startswith('http'):
            url = BASE_URL + url
        date = item['mediaDateUts'].split(', ')[1]
        try: date = Datetime.ParseDate(date).date()
        except: date = Datetime.Now()
        try: duration = int(item['duration']) * 1000
        except: duration = 0

        oc.add(VideoClipObject(
            url = url,
            title = item['title'],
            originally_available_at = date,
            summary = item['description'],
            duration = duration,
            thumb = Resource.ContentsOfURLWithFallback(url=item['thumbnail'])))

    if len(oc) == 30:
        oc.add(NextPageObject(key = Callback(VideoSearch, query=query, page=page+1, start=start+30), title = L("Next Page ...")))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    else:
        return oc
####################################################################################################
# This function will create a list of videos from the json for the playlist under a player
# IT IS NOT CURRENTLY USED
@route(PREFIX + '/pagejson')
def PageJSON(title, url):  

    oc = ObjectContainer(title2 = title)

    content = HTTP.Request(url).content
    json_data = RE_JSON.search(content).group(1)
    try: json = JSON.ObjectFromString(json_data)
    except: return ObjectContainer(header="Empty", message="There are no videos to list right now.")

    for item in json:
        title = item['title']
        url = BASE_URL + '/videos/' + item['videoId']
        duration = Datetime.MillisecondsFromString(item['duration'])

        oc.add(VideoClipObject(
            url = url,
            title = title,
            duration = duration))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    else:
        return oc
