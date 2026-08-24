"""
Turns raw snapshots into leaderboards. Run this right after poller.py.

Core idea: a video's growth only means something relative to its channel's
usual scale. +500K views/day is huge for a 50K-subscriber channel and
unremarkable for a channel with 50M subscribers. So most scores here are
normalized by sqrt(subscriber_count) — sqrt rather than linear so giant
channels don't totally dominate, but they aren't ignored either.

Usage:
    python momentum.py
"""
import math
from db import get_conn

HIDDEN_GEM_SUB_THRESHOLD = 200_000  # channels below this qualify for "Hidden Gems"


def get_growth_24h(conn):
    """
    For every active video, compare its latest snapshot to the snapshot closest
    to 24h before that. Returns a dict of video_id -> growth metrics.
    Videos with <2 snapshots spanning ~24h are skipped (not enough history yet).
    """
    rows = conn.execute("""
        SELECT s.video_id, s.captured_at, s.view_count, s.like_count, s.comment_count
        FROM snapshots s
        ORDER BY s.video_id, s.captured_at
    """).fetchall()

    by_video = {}
    for r in rows:
        by_video.setdefault(r["video_id"], []).append(r)

    results = {}
    for video_id, snaps in by_video.items():
        if len(snaps) < 2:
            continue
        latest = snaps[-1]
        # find the snapshot at least ~20h before latest (approximating 24h window
        # with whatever polling cadence you're actually running)
        baseline = snaps[0]
        for s in snaps:
            hours_gap = _hours_between(s["captured_at"], latest["captured_at"])
            if hours_gap >= 20:
                baseline = s
        hours_elapsed = max(_hours_between(baseline["captured_at"], latest["captured_at"]), 1)

        results[video_id] = {
            "total_views": latest["view_count"],
            "view_growth": latest["view_count"] - baseline["view_count"],
            "like_growth": (latest["like_count"] or 0) - (baseline["like_count"] or 0),
            "comment_growth": (latest["comment_count"] or 0) - (baseline["comment_count"] or 0),
            "hours_elapsed": hours_elapsed,
            "total_likes": latest["like_count"] or 0,
            "total_comments": latest["comment_count"] or 0,
        }
    return results


def _hours_between(t1, t2):
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    d1 = datetime.strptime(t1, fmt)
    d2 = datetime.strptime(t2, fmt)
    return abs((d2 - d1).total_seconds()) / 3600


def compute_leaderboards(conn):
    growth = get_growth_24h(conn)
    videos = {r["video_id"]: r for r in conn.execute("""
        SELECT v.video_id, v.title, v.category, v.channel_id,
               c.title AS channel_title, c.subscriber_count
        FROM videos v JOIN channels c ON v.channel_id = c.channel_id
        WHERE v.is_active = 1
    """).fetchall()}

    scored = []
    for video_id, g in growth.items():
        v = videos.get(video_id)
        if not v:
            continue
        subs = max(v["subscriber_count"] or 1000, 1000)  # floor to avoid div-by-tiny-number spikes
        norm = math.sqrt(subs)

        momentum_score = (
            (g["view_growth"] / norm) * 1.0 +
            (g["like_growth"] / norm) * 2.0 +
            (g["comment_growth"] / norm) * 3.0
        )

        scored.append({
            "video_id": video_id,
            "title": v["title"],
            "channel_title": v["channel_title"],
            "category": v["category"],
            "subscriber_count": subs,
            "total_views": g["total_views"],
            "view_growth_24h": g["view_growth"],
            "like_growth_24h": g["like_growth"],
            "comment_growth_24h": g["comment_growth"],
            "momentum_score": momentum_score,
        })

    leaderboards = {
        "rising_now": sorted(scored, key=lambda x: x["view_growth_24h"], reverse=True),
        "most_viewed": sorted(scored, key=lambda x: x["total_views"], reverse=True),
        "most_discussed": sorted(scored, key=lambda x: x["comment_growth_24h"], reverse=True),
        "fan_favorite": sorted(scored, key=lambda x: x["like_growth_24h"], reverse=True),
        "hidden_gems": sorted(
            [s for s in scored if s["subscriber_count"] < HIDDEN_GEM_SUB_THRESHOLD],
            key=lambda x: x["momentum_score"], reverse=True
        ),
    }

    # Category-specific momentum boards
    for category in {"gaming", "music", "entertainment"}:
        leaderboards[f"top_{category}"] = sorted(
            [s for s in scored if s["category"] == category],
            key=lambda x: x["momentum_score"], reverse=True
        )

    return leaderboards


def save_leaderboards(conn, leaderboards, top_n=25):
    conn.execute("DELETE FROM leaderboard_cache")
    for name, ranked in leaderboards.items():
        for rank, item in enumerate(ranked[:top_n], start=1):
            conn.execute("""
                INSERT INTO leaderboard_cache
                    (leaderboard, rank, video_id, score, view_growth_24h, like_growth_24h, total_views)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                name, rank, item["video_id"], item["momentum_score"],
                item["view_growth_24h"], item["like_growth_24h"], item["total_views"]
            ))
    conn.commit()


def run():
    conn = get_conn()
    leaderboards = compute_leaderboards(conn)
    save_leaderboards(conn, leaderboards)
    for name, ranked in leaderboards.items():
        print(f"{name}: {len(ranked)} videos ranked")
    conn.close()


if __name__ == "__main__":
    run()
