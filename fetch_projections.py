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

BASE_URL = "https://api.sleeper.app/v1/"

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
# 3. Sum up live points and dynamic projections for each team's starters
calculated_projections = {}

for team in matchups:
    roster_id = team.get("roster_id")
    starters = team.get("starters") or []
    
    total_blended_projection = 0.0
    
    for player_id in starters:
        p_id_str = str(player_id)
        
        # Grab live stats and base projections
        p_stats = stats_dict.get(p_id_str, {}).get("stats", {})
        p_proj = proj_dict.get(p_id_str, {}).get("stats", {})
        
        # Extract actual points scored right now
        actual_points = p_stats.get("pts_ppr", 0.0)
        
        # Check if the player's game has started or finished
        # If they have played, they will have passing/rushing/receiving snaps recorded
        has_played = p_stats.get("gp", 0) > 0 or p_stats.get("gs", 0) > 0 or actual_points != 0.0
        
        if has_played:
            # Game is live or finished: Use their actual hard points scored
            total_blended_projection += actual_points
        else:
            # Game hasn't started: Use their full pre-game projection baseline
            total_blended_projection += p_proj.get("pts_ppr", 0.0)
            
    calculated_projections[str(roster_id)] = round(total_blended_projection, 2)

# 4. Save results to your lightweight repository database file
with open("live_projections.json", "w") as f:
    json.dump(calculated_projections, f, indent=4)

print(f"🎉 Success! Compiled blended live projections for {len(calculated_projections)} rosters.")
