import json
import urllib.request

# 1. Load your central league configurations
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    LEAGUE_ID = config.get("LEAGUE_ID")
except Exception as e:
    print(f"Error reading config.json: {e}")
    LEAGUE_ID = None

if not LEAGUE_ID:
    print("Warning: LEAGUE_ID missing or config.json unreadable. Defaulting to empty fallback.")
    # Safe empty fallback mapping so the file writes empty structure instead of breaking with Exit Code 1
    with open("live_projections.json", "w") as f:
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

print("Checking NFL state context...")
nfl_state = fetch_json("https://api.sleeper.app/v1/state/nfl") or {}
current_week = nfl_state.get("display_week") or nfl_state.get("week") or 1
current_year = nfl_state.get("season") or "2026"

print(f"Fetching Week {current_week} matchup grids...")
matchups = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{current_week}") or []

# 2. Query Sleeper's raw master projections matrix using specific position tracking tags
print("Downloading live player projections stream...")
positions_query = "&position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=K&position[]=DEF&position[]=FLEX"
proj_url = f"https://api.sleeper.app/projections/nfl/{current_year}/{current_week}?season_type=regular&order_by=ppr{positions_query}"
raw_projections = fetch_json(proj_url) or {}

# 3. Sum up the live player projections for each team's starters
calculated_projections = {}
for team in matchups:
    roster_id = team.get("roster_id")
    starters = team.get("starters") or []
    
    total_team_projection = 0.0
    for player_id in starters:
        # Match player ID against Sleeper's live player projections mapping
        player_data = raw_projections.get(str(player_id)) or {}
        # Default to a standard zero projection if player is on a bye or out
        total_team_projection += player_data.get("stats", {}).get("pts_ppr", 0.0)
    
    calculated_projections[str(roster_id)] = round(total_team_projection, 2)

# 4. Save results to a lightweight JSON database file
with open("live_projections.json", "w") as f:
    json.dump(calculated_projections, f, indent=4)

print("Projections updated successfully inside live_projections.json!")
