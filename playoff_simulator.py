import json
import random
import numpy as np
import urllib.request

# ----------------- CONFIGURATION -----------------
# To match your repository setup, we dynamically read your LEAGUE_ID from config.json
with open("config.json", "r") as f:
    config = json.load(f)
LEAGUE_ID = config.get("LEAGUE_ID")

if not LEAGUE_ID:
    raise ValueError("LEAGUE_ID not found in config.json")

TOTAL_WEEKS = 14  # Regular season length
PLAYOFF_SLOTS = 6  # Top 6 teams advance
SIMULATIONS = 10000

# ----------------- API FETCHERS -----------------
def fetch_json(url):
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return None

print("Connecting to Sleeper API streams...")
nfl_state = fetch_json("https://api.sleeper.app/v1/state/nfl")
current_week = nfl_state.get("display_week") or nfl_state.get("week") or 1

rosters = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters")

# 1. Map current historical records and compile point trajectories
team_baselines = {}
for r in rosters:
    roster_id = r["roster_id"]
    team_baselines[roster_id] = {
        "roster_id": roster_id,
        "wins": r["settings"].get("wins", 0),
        "losses": r["settings"].get("losses", 0),
        "ties": r["settings"].get("ties", 0),
        "pf": r["settings"].get("fpts", 0) + (r["settings"].get("fpts_decimal", 0) / 100),
        "weekly_scores": []
    }

# 2. Gather historical matchup points scored to calculate scoring average + volatility (Standard Deviation)
for w in range(1, current_week):
    matchups = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{w}") or []
    for m in matchups:
        r_id = m.get("roster_id")
        if r_id in team_baselines:
            team_baselines[r_id]["weekly_scores"].append(m.get("points", 0))

# Assign statistical projections per team
for r_id, stats in team_baselines.items():
    scores = stats["weekly_scores"]
    if len(scores) > 0:
        stats["avg_score"] = float(np.mean(scores))
        stats["std_dev"] = float(np.std(scores)) if len(scores) > 1 else 12.0
    else:
        # Season opening fallbacks if historical stats are empty yet
        stats["avg_score"] = 115.0
        stats["std_dev"] = 15.0

# 3. Compile the remaining schedule calendar matrix
future_schedule = []
for w in range(current_week, TOTAL_WEEKS + 1):
    matchups = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{w}") or []
    # Group opponents matching the same matchup_id
    pairs = {}
    for m in matchups:
        m_id = m.get("matchup_id")
        if m_id:
            if m_id not in pairs:
                pairs[m_id] = []
            pairs[m_id].append({"roster_id": m["roster_id"]})
    
    for m_id, teams in pairs.items():
        if len(teams) == 2:
            future_schedule.append((teams[0]["roster_id"], teams[1]["roster_id"]))

# ----------------- MONTE CARLO CORE -----------------
print(f"Simulating remaining matchups {SIMULATIONS} times via Monte Carlo matrix...")
playoff_appearances = {r_id: 0 for r_id in team_baselines}

for _ in range(SIMULATIONS):
    # Deep clone base records for this iteration loop pass
    sim_standings = {r_id: {k: v for k, v in stats.items() if k != "weekly_scores"} for r_id, stats in team_baselines.items()}
    
    # Simulate every upcoming schedule pairing matching historical profiles
    for team_a_id, team_b_id in future_schedule:
        team_a = sim_standings[team_a_id]
        team_b = sim_standings[team_b_id]
        
        # Sample points scored using normal standard variations
        score_a = random.normalvariate(team_a["avg_score"], team_a["std_dev"])
        score_b = random.normalvariate(team_b["avg_score"], team_b["std_dev"])
        
        team_a["pf"] += score_a
        team_b["pf"] += score_b
        
        if score_a > score_b:
            team_a["wins"] += 1
            team_b["losses"] += 1
        elif score_a < score_b:
            team_b["wins"] += 1
            team_a["losses"] += 1
        else:
            team_a["ties"] += 1
            team_b["ties"] += 1

    # Sort simulated league standings by wins, then points for tiebreakers
    sorted_teams = list(sim_standings.values())
    sorted_teams.sort(key=lambda x: (x["wins"], x["pf"]), reverse=True)
    
    # Register the top 6 teams who clenched the playoffs
    for rank in range(PLAYOFF_SLOTS):
        clenched_team = sorted_teams[rank]
        playoff_appearances[clenched_team["roster_id"]] += 1

# 4. Format outputs into a clean JSON export matrix map
output_odds = {}
for r_id, counts in playoff_appearances.items():
    pct = (counts / SIMULATIONS) * 100
    output_odds[str(r_id)] = round(pct, 1)

with open("playoff_odds.json", "w") as f:
    json.dump(output_odds, f, indent=4)

print("Playoff simulation completed successfully! Saved results to playoff_odds.json")
