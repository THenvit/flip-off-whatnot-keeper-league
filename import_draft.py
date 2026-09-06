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
    print("Error: LEAGUE_ID missing from config.json.")
    exit(1)

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None

print(f"Connecting to Sleeper draft streams for league {LEAGUE_ID}...")
drafts_list = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/drafts")

# Validate that the drafts endpoint returned a proper list structure
if not drafts_list or not isinstance(drafts_list, list) or len(drafts_list) == 0:
    print("Error: No valid draft history arrays returned by the Sleeper API.")
    exit(1)

# Isolate the main draft ID by looking at the first item in the list
main_draft_id = drafts_list[0].get("draft_id")

if not main_draft_id:
    print("Error: Could not locate a valid draft_id inside the league data.")
    exit(1)

print(f"Successfully located main draft board ID: {main_draft_id}")
print("Downloading completed picks list...")

picks_data = fetch_json(f"https://api.sleeper.app/v1/draft/{main_draft_id}/picks") or []

if not picks_data or len(picks_data) == 0:
    print("Warning: The draft board appears to be empty or has not finished yet.")
    exit(1)

# 2. Rebuild your roster-history JSON mapping database
draft_history_map = {}

for pick in picks_data:
    player_id = pick.get("player_id")
    if player_id:
        # Index the draft round using the player's unique Sleeper ID
        draft_history_map[str(player_id)] = {
            "draft_round": pick.get("round"),
            "keeper_count": 0  # Resets to 0 since they are newly drafted onto rosters
        }

# 3. Export to your static JSON database file
with open("roster-history.json", "w") as f:
    json.dump(draft_history_map, f, indent=4)

print(f"🎉 Import successful! Compiled {len(draft_history_map)} player pick rounds directly into roster-history.json.")
