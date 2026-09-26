import json
import random
import numpy as np
import urllib.request

with open("config.json", "r") as f:
    config = json.load(f)
LEAGUE_ID = config.get("LEAGUE_ID")

if not LEAGUE_ID:
    raise ValueError("LEAGUE_ID missing from config.json")

TOTAL_WEEKS = 14  
PLAYOFF_SLOTS = 6  
SIMULATIONS = 10000
BASE_URL = "https://api.sleeper.app/v1/"

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return None

print("Connecting to Sleeper API data streams...")
nfl_state = fetch_json(f"{BASE_URL}state/nfl") or {}
current_week = nfl_state.get("display_week") or nfl_state.get("week") or 1

rosters = fetch_json(f"{BASE_URL}league/{LEAGUE_ID}/rosters") or []

team_baselines = {}
for r in rosters:
    roster_id = r["roster_id"]
    team_baselines[roster_id] = {
        "roster_id": roster_id,
        "wins": 0, "losses": 0, "ties": 0, "pf": 0.0,
        "weekly_scores": []
    }
# 3. Pull completed historical scores (Weeks 1 and 2)
for w in range(1, current_week):
    matchups = fetch_json(f"{BASE_URL}league/{LEAGUE_ID}/matchups/{w}") or []
    pairs = {}
    for m in matchups:
        r_id = m.get("roster_id")
        m_id = m.get("matchup_id")
        points = m.get("points", 0)
        
        if r_id in team_baselines:
            team_baselines[r_id]["weekly_scores"].append(points)
            team_baselines[r_id]["pf"] += points
        
        if m_id is not None:
            if m_id not in pairs:
                pairs[m_id] = []
            pairs[m_id].append({"roster_id": r_id, "points": points})

    for m_id, teams in pairs.items():
        if len(teams) == 2:
            t1, t2 = teams[0], teams[1]
            if t1["points"] > t2["points"]:
                team_baselines[t1["roster_id"]]["wins"] += 1
                team_baselines[t2["roster_id"]]["losses"] += 1
            elif t2["points"] > t1["points"]:
                team_baselines[t2["roster_id"]]["wins"] += 1
                team_baselines[t1["roster_id"]]["losses"] += 1
            else:
                team_baselines[t1["roster_id"]]["ties"] += 1
                team_baselines[t2["roster_id"]]["ties"] += 1

for r_id, stats in team_baselines.items():
    scores = stats["weekly_scores"]
# League-wide scoring baseline
all_scores = []
for stats in team_baselines.values():
    all_scores.extend(stats["weekly_scores"])

if all_scores:
    league_avg = float(np.mean(all_scores))
else:
    league_avg = 115.0

# How strongly we regress early-season performance toward the league average.
# Higher = more regression.
REGRESSION_GAMES = 8

for r_id, stats in team_baselines.items():
    scores = stats["weekly_scores"]
    games_played = len(scores)

    if games_played > 0:
        observed_avg = float(np.mean(scores))

        # Regression toward league average.
        #
        # 1 game  -> heavily regressed
        # 2 games -> still heavily regressed
        # 8+ games -> mostly trust actual performance
        weight = games_played / (games_played + REGRESSION_GAMES)

        stats["avg_score"] = (
            observed_avg * weight +
            league_avg * (1 - weight)
        )

        # Use a reasonable fantasy scoring variance.
        if games_played > 1:
            calc_std = float(np.std(scores, ddof=1))
        else:
            calc_std = 18.0

        # Don't allow small samples to create unrealistically
        # narrow scoring distributions.
        stats["std_dev"] = max(18.0, calc_std)

    else:
        stats["avg_score"] = league_avg
        stats["std_dev"] = 18.0

# 4. Build future schedule safely by handling dictionary/error fallbacks
future_schedule = []
print(f"Parsing remaining weeks from Week {current_week} to {TOTAL_WEEKS}...")

for w in range(current_week, TOTAL_WEEKS + 1):
    url = f"{BASE_URL}league/{LEAGUE_ID}/matchups/{w}"
    matchups = fetch_json(url)
    
    # If Sleeper returns a dictionary error or is empty, we must skip or log it
    if not matchups or not isinstance(matchups, list):
        print(f"⚠️ Warning: Week {w} matchups are not generated or locked by Sleeper yet.")
        continue

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
expected_future_games = (
    len(team_baselines) * (TOTAL_WEEKS - (current_week - 1)) // 2
)

print(
    f"Future games found: {len(future_schedule)} "
    f"(expected approximately {expected_future_games})"
)

print(f"Simulating future schedule calendar {SIMULATIONS} times...")

# FIXED NAME ERROR: Explicitly defines the appearances tracking dictionary matrix baseline
playoff_appearances = {}
for r_id in team_baselines:
    playoff_appearances[r_id] = 0

# 5. Execute Monte Carlo loops with fair, stacked sorting metrics
for _ in range(SIMULATIONS):
    sim_standings = {}
    for r_id, stats in team_baselines.items():
        sim_standings[r_id] = {
            "roster_id": r_id,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "ties": stats["ties"],
            "pf": stats["pf"]
        }
    
    for team_a_id, team_b_id in future_schedule:
        team_a = sim_standings[team_a_id]
        team_b = sim_standings[team_b_id]
        
# League-wide weekly scoring environment
weekly_environment = random.normalvariate(0, 6)

score_a = random.normalvariate(
    team_baselines[team_a_id]["avg_score"] + weekly_environment,
    team_baselines[team_a_id]["std_dev"]
)

score_b = random.normalvariate(
    team_baselines[team_b_id]["avg_score"] + weekly_environment,
    team_baselines[team_b_id]["std_dev"]
)
        
        team_a["pf"] += score_a
        team_b["pf"] += score_b
        
        if score_a > score_b:
            team_a["wins"] += 1
            team_b["losses"] += 1
        elif score_b > score_a:
            team_b["wins"] += 1
            team_a["losses"] += 1
        else:
            team_a["ties"] += 1
            team_b["ties"] += 1

    sorted_teams = list(sim_standings.values())
    # Sort logically by wins, then ties, then total simulated points for as the ultimate tiebreaker
    sorted_teams.sort(key=lambda x: (x["wins"], x["ties"], x["pf"]), reverse=True)
    
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
