import json
import urllib.request

# 1. Load configuration safely
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    LEAGUE_ID = config.get("LEAGUE_ID")
except Exception as e:
    print(f"Error reading config.json: {e}")
    LEAGUE_ID = None

if not LEAGUE_ID:
    print("Warning: LEAGUE_ID missing or config.json unreadable. Saving blank fallback.")
    with open("roster-history.json", "w") as f:
        json.dump({}, f)
    exit(0)

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None

print("Connecting to Sleeper league draft streams...")
drafts_list = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/drafts")

if not drafts_list or len(drafts_list) == 0:
    print("Warning: No completed draft history found for this league ID yet. Saving empty template.")
    with open("roster-history.json", "w") as f:
        json.dump({}, f)
    exit(0)

# Isolate the primary completed draft ID from your league context array
# Sleeper returns drafts as a list of dicts
main_draft_id = drafts_list[0].get("draft_id") if isinstance(drafts_list, list) else drafts_list.get("draft_id")

if not main_draft_id:
    print("Could not locate a valid draft_id. Saving empty fallback.")
    with open("roster-history.json", "w") as f:
        json.dump({}, f)
    exit(0)

print(f"Downloading picks list from draft board ID: {main_draft_id}...")
picks_data = fetch_json(f"https://api.sleeper.app/v1/{main_draft_id}/picks") or []

# 2. Build your local tracking dictionary mapping template
draft_history_map = {}

for pick in picks_data:
    player_id = pick.get("player_id")
    if player_id:
        # Map the exact round they were selected in to their unique player ID token string
        draft_history_map[str(player_id)] = {
            "draft_round": pick.get("round"),
            "keeper_count": 0  # Resets to 0 since they were newly selected on the board
        }

# 3. Export to your static JSON database file
with open("roster-history.json", "w") as f:
    json.dump(draft_history_map, f, indent=4)

print(f"Import successful! Map compiled for {len(draft_history_map)} draft slots inside roster-history.json.")
