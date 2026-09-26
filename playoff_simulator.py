import json
import random
import numpy as np
import urllib.request

# 1. Load central configurations securely
with open("config.json", "r") as f:
    config = json.load(f)
LEAGUE_ID = config.get("LEAGUE_ID")

if not LEAGUE_ID:
    raise ValueError("LEAGUE_ID missing from config.json")

TOTAL_WEEKS = 14  
PLAYOFF_SLOTS = 6  
SIMULATIONS = 10000

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return None

print("Connecting to Sleeper API data streams...")
nfl_state = fetch_json("https://api.sleeper.app/v1/state/nfl") or {}
# Safely isolate what week we are currently playing
current_week = nfl_state.get("display_week") or nfl_state.get("week") or 1

rosters = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters") or []

# 2. Map baseline records from the live standings data
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
# 3. Pull historical scores to build pure current-season records
# We reset baseline wins/losses to 0 and calculate purely from the active calendar
for w in range(1, current_week):
    matchups = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{w}") or []
    
    if w == 1:
        for r_id in team_baselines:
            team_baselines[r_id]["wins"] = 0
            team_baselines[r_id]["losses"] = 0
            team_baselines[r_id]["ties"] = 0

    pairs = {}
    for m in matchups:
        r_id = m.get("roster_id")
        m_id = m.get("matchup_id")
        if r_id in team_baselines:
            team_baselines[r_id]["weekly_scores"].append(m.get("points", 0))
        
        if m_id is not None:
            if m_id not in pairs:
                pairs[m_id] = []
            pairs[m_id].append(m)

    # Tally pure current-season head-to-head records
    for m_id, teams in pairs.items():
        if len(teams) == 2:
            t1, t2 = teams[0], teams[1]
            p1, p2 = t1.get("points", 0), t2.get("points", 0)
            id1, id2 = t1.get("roster_id"), t2.get("roster_id")
            
            if p1 > p2:
                team_baselines[id1]["wins"] += 1
                team_baselines[id2]["losses"] += 1
            elif p2 > p1:
                team_baselines[id2]["wins"] += 1
                team_baselines[id1]["losses"] += 1
            else:
                team_baselines[id1]["ties"] += 1
                team_baselines[id2]["ties"] += 1

# Assign statistical averages and force a minimum 12-point volatility floor
for r_id, stats in team_baselines.items():
    scores = stats["weekly_scores"]
    if len(scores) > 0:
        stats["avg_score"] = float(np.mean(scores))
        calc_std = float(np.std(scores)) if len(scores) > 1 else 12.0
        stats["std_dev"] = max(12.0, calc_std) 
    else:
        stats["avg_score"] = 115.0
        stats["std_dev"] = 15.0

# 4. Build the REMAINING calendar schedule matrix
future_schedule = []
for w in range(current_week + 1, TOTAL_WEEKS + 1):
    matchups = fetch_json(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{w}") or []
    pairs = {}
    for m in matchups:
        m_id = m.get("matchup_id")
        if m_id is not None:
            if m_id not in pairs:
                pairs[m_id] = []
            pairs[m_id].append(m.get("roster_id"))
    
    for m_id, teams in pairs.items():
        if len(teams) == 2:
            future_schedule.append((teams[0], teams[1]))

# 5. Execute Monte Carlo core simulation loops
print(f"Simulating future schedule calendar {SIMULATIONS} times...")
playoff_appearances = {r_id: 0 for r_id in team_baselines}

for _ in range(SIMULATIONS):
    sim_standings = {r_id: {k: v for k, v in stats.items() if k != "weekly_scores"} for r_id, stats in team_baselines.items()}
    
    for team_a_id, team_b_id in future_schedule:
        team_a = sim_standings[team_a_id]
        team_b = sim_standings[team_b_id]
        
        score_a = random.normalvariate(team_a["avg_score"], team_a["std_dev"])
        score_b = random.normalvariate(team_b["avg_score"], team_b["std_dev"])
        
        team_a["pf"] += score_a
        team_b["pf"] += score_b
        
        if score_a > score_b:
            team_a["wins"] += 1
            team_b["losses"] += 1
        else:
            team_b["wins"] += 1
            team_a["losses"] += 1

    sorted_teams = list(sim_standings.values())
    sorted_teams.sort(key=lambda x: (x["wins"], x["pf"]), reverse=True)
    
    for rank in range(PLAYOFF_SLOTS):
        playoff_appearances[sorted_teams[rank]["roster_id"]] += 1

# 6. Format and export output data
output_odds = {}
total_wins_recorded = sum(stats["wins"] for stats in team_baselines.values())

for r_id, counts in playoff_appearances.items():
    if total_wins_recorded == 0:
        output_odds[str(r_id)] = 50.0
    else:
        output_odds[str(r_id)] = round((counts / SIMULATIONS) * 100, 1)

with open("playoff_odds.json", "w") as f:
    json.dump(output_odds, f, indent=4)

print("Playoff simulation completed successfully!")
