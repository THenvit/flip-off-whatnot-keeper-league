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
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None

print(f"Connecting to Sleeper draft streams for league {LEAGUE_ID}...")

# Fetch all required live data feeds concurrently
drafts_list = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/drafts")
rosters_list = fetch_json(f"https://sleeper.app/v1/league/{LEAGUE_ID}/rosters") or []

# 2. LOCAL FILE READ: Open your local master player data and your EXISTING history log
print("Loading local public/players.json database track...")
try:
    with open("public/players.json", "r") as f:
        master_players = json.load(f) or {}
except Exception as e:
    print(f"Error loading local public/players.json: {e}")
    master_players = {}

print("Loading existing roster-history.json database layer...")
try:
    with open("roster-history_SAVED.json", "r") as f:
        existing_history = json.load(f) or {}
except Exception as e:
    print(f"Warning: No existing roster-history.json found or file empty. Starting clean matrix map.")
    existing_history = {}

# Validate drafts structure
if not drafts_list:
    print("Error: No valid draft history arrays returned by Sleeper.")
    exit(1)

if isinstance(drafts_list, list):
    if len(drafts_list) == 0:
        print("Error: Sleeper returned an empty drafts list.")
        exit(1)
    main_draft_id = drafts_list.get("draft_id")
else:
    main_draft_id = drafts_list.get("draft_id")

if not main_draft_id:
    print("Error: Could not locate a valid draft_id.")
    exit(1)

print(f"Located main draft board ID: {main_draft_id}")
picks_data = fetch_json(f"https://sleeper.app/v1/draft/{main_draft_id}/picks") or []

# 3. Cache draft round positions and automated keeper status flags by Player ID
draft_lookup = {}
for pick in picks_data:
    p_id = pick.get("player_id")
    if p_id:
        is_keeper_pick = pick.get("is_keeper", False)
        pick_metadata = pick.get("metadata") or {}
        if pick_metadata.get("is_keeper") in [True, "true", "1"]:
            is_keeper_pick = True

        draft_lookup[str(p_id)] = {
            "round": pick.get("round"),
            "is_keeper": is_keeper_pick
        }

# 4. Generate the complete master database matching your original structure
draft_history_map = {}

# Process ALL players currently on team rosters
for roster in rosters_list:
    r_id = roster.get("roster_id")
    p_ids = roster.get("players") or []
    
    for p_id in p_ids:
        p_id_str = str(p_id)
        player_profile = master_players.get(p_id_str) or {}
        
        full_name = player_profile.get("full_name") or player_profile.get("search_full_name")
        if not full_name:
            first_name = player_profile.get("first_name", "")
            last_name = player_profile.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else f"Player {p_id_str}"
        
        # Retrieve cached draft record metrics
        pick_info = draft_lookup.get(p_id_str) or {}
        draft_round = pick_info.get("round", None)
        is_currently_keeper = pick_info.get("is_keeper", False)
        
        # Look up what their count was LAST season inside your old JSON file
        previous_player_record = existing_history.get(p_id_str) or {}
        previous_keeper_count = previous_player_record.get("keeper_count", 0)
        previous_draft_round = previous_player_record.get("draft_round", None)

        # --- ADVANCED ACCUMULATOR FORMULA ---
        # A player is a consecutive keeper if:
        # 1. Sleeper explicitly marks them as a keeper this year
        # OR 2. They were a keeper last year (count > 0) AND their draft round hasn't changed or has decreased (penalty applied)
        if is_currently_keeper or (previous_keeper_count > 0 and draft_round is not None):
            updated_keeper_count = previous_keeper_count + 1
        else:
            # If they were drafted completely fresh or picked up via free agency, reset to 1 if it's their first year kept
            updated_keeper_count = 1 if is_currently_keeper else 0

        # Build the exact dictionary structure
        draft_history_map[p_id_str] = {
            "name": full_name,
            "position": player_profile.get("position", "N/A"),
            "nfl_team": player_profile.get("team", "FA"),
            "roster_id": r_id,
            "draft_round": draft_round,
            "keeper_count": updated_keeper_count
        }

# 5. Export to your static JSON database file
with open("roster-history.json", "w") as f:
    json.dump(draft_history_map, f, indent=4)

print(f"🎉 Import successful! Compiled results for {len(draft_history_map)} players inside roster-history.json.")
