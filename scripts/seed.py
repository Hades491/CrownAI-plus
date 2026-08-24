"""
Populates channels + videos tables from YouTube's trending charts.
Run this occasionally (e.g. daily) to keep discovering new videos to track.
Doesn't touch snapshots — that's poller.py's job.

Usage:
    python seed.py                    # default: IN region, general trending
    python seed.py --region US
"""
import argparse
from db import get_conn, init_db
from youtube_client import most_popular_videos, channels_stats

# YouTube category IDs worth tracking separately (region-dependent, these are common ones)
CATEGORIES = {
    "gaming": "20",
    "music": "10",
    "entertainment": "24",
    "general": None,  # no filter = overall trending
}


def upsert_channel(conn, channel_id, title, category, subscriber_count, country):
    conn.execute("""
        INSERT INTO channels (channel_id, title, category, subscriber_count, country, last_updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(channel_id) DO UPDATE SET
            subscriber_count = excluded.subscriber_count,
            last_updated_at = datetime('now')
    """, (channel_id, title, category, subscriber_count, country))


def upsert_video(conn, video_id, channel_id, title, category, published_at):
    conn.execute("""
        INSERT INTO videos (video_id, channel_id, title, category, published_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO NOTHING
    """, (video_id, channel_id, title, category, published_at))


def run(region="IN"):
    init_db()
    conn = get_conn()

    all_channel_ids = set()
    video_rows = []  # (video_id, channel_id, title, category, published_at)

    for category, cat_id in CATEGORIES.items():
        items = most_popular_videos(region_code=region, category_id=cat_id, max_results=50)
        print(f"[{category}] fetched {len(items)} trending videos")
        for item in items:
            vid = item["id"]
            snippet = item["snippet"]
            channel_id = snippet["channelId"]
            all_channel_ids.add(channel_id)
            video_rows.append((vid, channel_id, snippet["title"], category, snippet["publishedAt"]))

    # Fetch channel details (subscriber counts) in batches
    channel_details = channels_stats(list(all_channel_ids))
    for ch in channel_details:
        stats = ch.get("statistics", {})
        snippet = ch["snippet"]
        upsert_channel(
            conn,
            ch["id"],
            snippet["title"],
            None,
            int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount") else None,
            snippet.get("country"),
        )

    for row in video_rows:
        upsert_video(conn, *row)

    conn.commit()
    print(f"Seeded {len(video_rows)} videos across {len(all_channel_ids)} channels.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="IN")
    args = parser.parse_args()
    run(region=args.region)
