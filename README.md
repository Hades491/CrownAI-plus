# Pulse — YouTube Momentum Tracker

Ranks YouTube videos by growth speed, not just total views. Normalizes growth
against each channel's subscriber count so small creators can surface
alongside giants ("Hidden Gems").

## How it works

```
seed.py     → discovers videos from trending charts, populates channels/videos tables
poller.py   → runs on a schedule, snapshots view/like/comment counts for tracked videos
momentum.py → compares snapshots ~24h apart, computes growth + momentum score, caches leaderboards
api/app.py  → serves cached leaderboards as JSON
web/index.html → dashboard UI (ships with sample data; point it at the API for live data)
```

The reason there's a `snapshots` table instead of just storing "current views":
YouTube's API only gives you a point-in-time count. To know a video gained
500K views *today*, you need yesterday's count on file. That's what the
poller is for — it's the whole reason this can't just be a wrapper around the
API.

## Setup

```bash
cd youtube-pulse
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste in your YouTube Data API key
```

## Run it

```bash
# 1. Initialize the database
python scripts/db.py

# 2. Seed with trending videos (run daily-ish to discover new content)
python scripts/seed.py --region IN

# 3. Take a snapshot right now
python scripts/poller.py

# --- wait a few hours, or run poller.py again with older test data ---

# 4. Compute leaderboards (needs at least 2 snapshots per video, ideally ~24h apart)
python scripts/momentum.py

# 5. Serve the API
python api/app.py
# → http://localhost:5000/api/leaderboards/rising_now

# 6. Open web/index.html in a browser (uses sample data by default —
#    uncomment the loadLive() function to wire it to the API above)
```

## Automating the poller (the actual product)

The pipeline only becomes interesting once it's been running for a few days.
Set up a cron job:

```cron
# Poll every 4 hours
0 */4 * * * cd /path/to/youtube-pulse && python scripts/poller.py && python scripts/momentum.py

# Reseed daily at 3am to discover newly-trending videos
0 3 * * * cd /path/to/youtube-pulse && python scripts/seed.py --region IN
```

Or use a GitHub Actions scheduled workflow / a small VPS with systemd timers
if you don't want to leave your own machine running.

## Quota math

- `videos.list` costs 1 unit per call, up to 50 video IDs per call.
- Tracking 2,000 videos, polled every 4 hours = 2,000/50 × 6 times/day = **240 units/day**.
- Free tier is 10,000 units/day — plenty of headroom to grow to ~15-20K tracked videos
  before you'd need to request a quota increase.
- `search.list` (used only in seeding, if you add keyword-based discovery) costs
  100 units/call — use it sparingly.

## Where to take this next

- **Postgres + TimescaleDB** once SQLite's single-writer model becomes a bottleneck.
- **Category IDs are region-dependent** — the ones in `seed.py` (`CATEGORIES`) work
  for most regions but double-check via the `videoCategories.list` endpoint for yours.
- **Better "hidden gem" discovery**: trending charts skew toward already-large channels.
  Consider keyword/hashtag search sweeps, or a public submission form, to surface
  genuinely small creators.
- **Auth + saved leaderboards** if you want users to follow specific niches.
- **Deploy**: API on Render/Railway/Fly.io, poller as a scheduled job on the same
  platform or GitHub Actions, frontend on Vercel/Netlify pointed at the API's public URL.
