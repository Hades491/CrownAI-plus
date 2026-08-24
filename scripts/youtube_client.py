"""
Minimal YouTube Data API v3 client using plain requests (no google-api-python-client
dependency needed). Costs are noted per call — see
https://developers.google.com/youtube/v3/determine_quota_cost
"""
import requests
from config import YOUTUBE_API_KEY

BASE = "https://www.googleapis.com/youtube/v3"


def _get(endpoint, params):
    params = {**params, "key": YOUTUBE_API_KEY}
    resp = requests.get(f"{BASE}/{endpoint}", params=params, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube API error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def most_popular_videos(region_code="IN", category_id=None, max_results=50):
    """Cost: 1 unit. Good seed source for 'most viewed' and category leaderboards."""
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
    }
    if category_id:
        params["videoCategoryId"] = category_id
    return _get("videos", params).get("items", [])


def search_videos(query, published_after=None, max_results=25, order="date"):
    """Cost: 100 units — expensive, use sparingly (e.g. to seed 'hidden gems' by keyword)."""
    params = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": max_results,
        "order": order,
    }
    if published_after:
        params["publishedAfter"] = published_after
    return _get("search", params).get("items", [])


def videos_stats(video_ids):
    """Cost: 1 unit per call, up to 50 IDs per call. This is the workhorse for polling."""
    items = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = {"part": "snippet,statistics", "id": ",".join(batch)}
        items.extend(_get("videos", params).get("items", []))
    return items


def channels_stats(channel_ids):
    """Cost: 1 unit per call, up to 50 IDs per call. Used to get subscriber counts
    for normalizing the momentum score against channel size."""
    items = []
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        params = {"part": "snippet,statistics", "id": ",".join(batch)}
        items.extend(_get("channels", params).get("items", []))
    return items
