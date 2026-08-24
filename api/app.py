"""
Serves precomputed leaderboards. Doesn't touch the YouTube API at all —
just reads leaderboard_cache, which poller.py + momentum.py keep fresh.

Usage:
    python app.py
    curl http://localhost:5000/api/leaderboards/rising_now
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from flask import Flask, jsonify
from flask_cors import CORS
from db import get_conn

app = Flask(__name__)
CORS(app)


@app.route("/api/leaderboards")
def list_leaderboards():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT leaderboard FROM leaderboard_cache").fetchall()
    conn.close()
    return jsonify([r["leaderboard"] for r in rows])


@app.route("/api/leaderboards/<name>")
def get_leaderboard(name):
    conn = get_conn()
    rows = conn.execute("""
        SELECT lc.rank, lc.score, lc.view_growth_24h, lc.like_growth_24h, lc.total_views,
               v.title, v.video_id, v.category, c.title AS channel_title, c.subscriber_count
        FROM leaderboard_cache lc
        JOIN videos v ON lc.video_id = v.video_id
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE lc.leaderboard = ?
        ORDER BY lc.rank ASC
    """, (name,)).fetchall()
    conn.close()
    if not rows:
        return jsonify({"error": f"No data for leaderboard '{name}'. Run seed.py, poller.py, momentum.py first."}), 404
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
