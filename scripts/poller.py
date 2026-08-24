"""
The pipeline's heartbeat. Run this on a schedule (cron / systemd timer / GitHub Actions)
every 1-6 hours. Each run costs ~1 API unit per 50 tracked videos.

Usage:
    python poller.py
"""
from db import get_conn
from youtube_client import videos_stats


def run():
    conn = get_conn()
    video_ids = [r["video_id"] for r in conn.execute(
        "SELECT video_id FROM videos WHERE is_active = 1"
    ).fetchall()]

    if not video_ids:
        print("No tracked videos. Run seed.py first.")
        return

    print(f"Polling stats for {len(video_ids)} videos...")
    items = videos_stats(video_ids)

    inserted = 0
    seen_ids = set()
    for item in items:
        vid = item["id"]
        seen_ids.add(vid)
        stats = item.get("statistics", {})
        conn.execute("""
            INSERT INTO snapshots (video_id, view_count, like_count, comment_count)
            VALUES (?, ?, ?, ?)
        """, (
            vid,
            int(stats.get("viewCount", 0)),
            int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
            int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
        ))
        inserted += 1

    # Videos that no longer come back from the API (deleted/private) — deactivate them
    missing = set(video_ids) - seen_ids
    if missing:
        conn.executemany(
            "UPDATE videos SET is_active = 0 WHERE video_id = ?",
            [(v,) for v in missing]
        )
        print(f"Deactivated {len(missing)} videos no longer available.")

    conn.commit()
    conn.close()
    print(f"Inserted {inserted} snapshots.")


if __name__ == "__main__":
    run()
