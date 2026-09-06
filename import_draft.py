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

# Fetch all required data feeds concurrently
drafts_list = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/drafts")
rosters_list = fetch_json(f"https://sleeper.app/v1/league/{LEAGUE_ID}/rosters") or []

# 2. LOCAL FILE READ: Open your local public directory player database asset directly
print("Loading local public/players.json database track...")
try:
    with open("public/players.json", "r") as f:
        master_players = json.load(f) or {}
except Exception as e:
    print(f"Error loading local public/players.json: {e}")
    master_players = {}

# Validate drafts structure
if not drafts_list:
    print("Error: No valid draft history arrays returned by Sleeper.")
    exit(1)

# Handle cases where Sleeper wraps drafts inside a list array container
main_draft_id = drafts_list[0].get("draft_id") if isinstance(drafts_list, list) else drafts_list.get("draft_id")

if not main_draft_id:
    print("Error: Could not locate a valid draft_id.")
    exit(1)

print(f"Located main draft board ID: {main_draft_id}")
picks_data = fetch_json(f"https://api.sleeper.app/v1/draft/{main_draft_id}/picks") or []

# 3. Build map of which player belongs to which roster currently
player_to_roster_map = {}
for roster in rosters_list:
    r_id = roster.get("roster_id")
    p_ids = roster.get("players") or []
    for p_id in p_ids:
        player_to_roster_map[str(p_id)] = r_id

# 4. Cache draft round positions by Player ID
draft_lookup = {}
for pick in picks_data:
    p_id = pick.get("player_id")
    if p_id:
        draft_lookup[str(p_id)] = pick.get("round")

# 5. Generate the complete master database matching your original structure
draft_history_map = {}

# Process ALL players currently on team rosters
for roster in rosters_list:
    r_id = roster.get("roster_id")
    p_ids = roster.get("players") or []
    
    for p_id in p_ids:
        p_id_str = str(p_id)
        player_profile = master_players.get(p_id_str) or {}
        
        # SLeper Native API data structure keys allocation lookup overrides
        full_name = player_profile.get("full_name") or player_profile.get("search_full_name")
        
        # Construct names mapping using native fallback segments if combined string doesn't map
        if not full_name:
            first_name = player_profile.get("first_name", "")
            last_name = player_profile.get("last_name", "")
            if not first_name and not last_name:
                full_name = "Player " + p_id_str
            else:
                full_name = f"{first_name} {last_name}".strip()
        
        # Build the exact dictionary structure you had before
        draft_history_map[p_id_str] = {
            "name": full_name,
            "position": player_profile.get("position", "N/A"),
            "nfl_team": player_profile.get("team", "FA"),
            "roster_id": r_id,
            "draft_round": draft_lookup.get(p_id_str, None), # Defaults to null if picked up on waivers
            "keeper_count": 0
        }

# 6. Export to your static JSON database file
with open("roster-history.json", "w") as f:
    json.dump(draft_history_map, f, indent=4)

print(f"🎉 Import successful! Restored complete metadata grid for {len(draft_history_map)} players into roster-history.json.")
