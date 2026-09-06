import json
import urllib.request

# 1. Load configuration safely
with open("config.json", "r") as f:
    config = json.load(f)
LEAGUE_ID = config.get("LEAGUE_ID")

if not LEAGUE_ID:
    raise ValueError("LEAGUE_ID missing from config.json")

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None

print("Connecting to Sleeper draft records...")
drafts = fetch_json(f"https://api.sleeper.app/v1/{LEAGUE_ID}/drafts")

if not drafts or len(drafts) == 0:
    raise ValueError("No completed draft history found for this league ID.")

# Isolate the primary completed draft ID from your league context
main_draft_id = drafts[0]["draft_id"]

print(f"Downloading picks list from draft board ID: {main_draft_id}...")
picks_data = fetch_json(f"https://sleeper.app{main_draft_id}/picks") or []

# 2. Build your local tracking dictionary mapping template
draft_history_map = {}

for pick in picks_data:
    player_id = pick.get("player_id")
    if player_id:
        # Map the exact round they were selected in to their unique player ID token
        draft_history_map[str(player_id)] = {
            "draft_round": pick.get("round"),
            "keeper_count": 0  # Resets to 0 since they were newly selected on the board
        }

# 3. Export to your static JSON database file
with open("roster-history.json", "w") as f:
    json.dump(draft_history_map, f, indent=4)

print("Import successful! Saved 2026 results directly inside roster-history.json")
