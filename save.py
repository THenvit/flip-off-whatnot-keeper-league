import json
import urllib.request

# 1. Load central configurations securely
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

BASE_URL = "https://sleeper.app"

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None

print("Checking live NFL week context...")
nfl_state = fetch_json(f"{BASE_URL}state/nfl") or {}
current_week = nfl_state.get("display_week") or nfl_state.get("week") or 1
current_year = nfl_state.get("season") or "2026"

print(f"Fetching Week {current_week} league matchup grids...")
matchups = fetch_json(f"{BASE_URL}league/{LEAGUE_ID}/matchups/{current_week}") or []

# 2. Query Sleeper's master live stats AND projections for the current week
print("Downloading live player statistics matrix...")
positions_query = "&position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=K&position[]=DEF&position[]=FLEX"

# Live Stats URL (Actual points scored so far)
stats_url = f"https://sleeper.app{current_year}/{current_week}?season_type=regular{positions_query}"
# Projections URL (Expected points before/during game)
proj_url = f"https://sleeper.app{current_year}/{current_week}?season_type=regular&order_by=ppr{positions_query}"

raw_stats_list = fetch_json(stats_url) or []
raw_proj_list = fetch_json(proj_url) or []

# Convert both lists into highly searchable dictionary maps
stats_dict = {str(p.get("player_id")): p for p in raw_stats_list if p.get("player_id")}
proj_dict = {str(p.get("player_id")): p for p in raw_proj_list if p.get("player_id")}
