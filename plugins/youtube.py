import re
import time

import isodate
import requests

from spanky.plugin import hook
from spanky.utils import timeformat
from spanky.utils.formatting import pluralize

youtube_re = re.compile(
    r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)([-_a-zA-Z0-9]+)', re.I)

base_url = 'https://www.googleapis.com/youtube/v3/'
api_url = base_url + 'videos?part=contentDetails%2C+snippet%2C+statistics&id={}&key={}'
search_api_url = base_url + 'search?part=id&maxResults=1'
playlist_api_url = base_url + 'playlists?part=snippet%2CcontentDetails%2Cstatus'
video_url = "http://youtu.be/%s"
err_no_api = "The YouTube API is off in the Google Developers Console."


def get_video_description(video_id):
    request = requests.get(api_url.format(video_id, dev_key))
    json = request.json()

    if json.get('error'):
        if json['error']['code'] == 403:
            return err_no_api
        else:
            return

    data = json['items']
    snippet = data[0]['snippet']
    statistics = data[0]['statistics']
    content_details = data[0]['contentDetails']

    out = '**{}**'.format(snippet['title'])

    if not content_details.get('duration'):
        return out

    length = isodate.parse_duration(content_details['duration'])
    out += ' - length {}'.format(timeformat.format_time(
        int(length.total_seconds()), simple=True))
    try:
        total_votes = float(statistics['likeCount']) + \
            float(statistics['dislikeCount'])
    except (LookupError, ValueError):
        total_votes = 0

    if total_votes != 0:
        # format
        likes = pluralize(int(statistics['likeCount']), "like")
        dislikes = pluralize(int(statistics['dislikeCount']), "dislike")

        percent = 100 * float(statistics['likeCount']) / total_votes
        out += ' - {}, {} (*{:.1f}*%)'.format(likes,
                                              dislikes, percent)

    if 'viewCount' in statistics:
        views = int(statistics['viewCount'])
        out += ' - {:,} view{}'.format(views, "s"[views == 1:])

    uploader = snippet['channelTitle']

    upload_time = time.strptime(
        snippet['publishedAt'][:-1], "%Y-%m-%dT%H:%M:%S")
    out += ' - {} on {}'.format(uploader,
                                time.strftime("%Y.%m.%d", upload_time))

    return out


@hook.on_start()
def load_key(bot):
    global dev_key
    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)


@hook.command("youtube")
def youtube(text, reply, send_embed):
    """<query> - Returns the first YouTube search result for <query>."""
    if not dev_key:
        return "This command requires a Google Developers Console API key."

    try:
        request = requests.get(search_api_url, params={
                               "q": text, "key": dev_key, "type": "video"})
        request.raise_for_status()
    except Exception:
        reply("Error performing search.")
        raise

    json = requests.get(search_api_url, params={
                        "q": text, "key": dev_key, "type": "video"}).json()

    if json.get('error'):
        if json['error']['code'] == 403:
            return err_no_api
        else:
            return 'Error performing search.'

    if json['pageInfo']['totalResults'] == 0:
        return 'No results found.'

    video_id = json['items'][0]['id']['videoId']

    return get_video_description(video_id) + " - " + video_url % video_id
