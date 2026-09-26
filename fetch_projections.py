import json
import urllib.request

# ============================================================
# CONFIGURATION
# ============================================================

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


API_BASE_URL = "https://api.sleeper.app/v1"
DATA_BASE_URL = "https://api.sleeper.com"


# ============================================================
# API HELPER
# ============================================================

def fetch_json(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode())

    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None


# ============================================================
# GET CURRENT NFL STATE
# ============================================================

print("Checking live NFL week context...")

nfl_state = fetch_json(
    f"{API_BASE_URL}/state/nfl"
) or {}

current_week = (
    nfl_state.get("display_week")
    or nfl_state.get("week")
    or 1
)

current_year = (
    nfl_state.get("season")
    or "2026"
)

print(
    f"Current NFL season: {current_year}, "
    f"Week: {current_week}"
)


# ============================================================
# GET LEAGUE INFORMATION
# ============================================================

print("Fetching league settings...")

league = fetch_json(
    f"{API_BASE_URL}/league/{LEAGUE_ID}"
) or {}

scoring_settings = league.get("scoring_settings", {})

print(
    f"League scoring settings loaded: "
    f"{len(scoring_settings)} scoring rules"
)


# ============================================================
# GET CURRENT WEEK MATCHUPS
# ============================================================

print(
    f"Fetching Week {current_week} league matchup grid..."
)

matchups = fetch_json(
    f"{API_BASE_URL}/league/{LEAGUE_ID}/matchups/{current_week}"
) or []

if not isinstance(matchups, list):
    print("ERROR: Sleeper matchup data was not returned as a list.")
    exit(1)

print(
    f"Received {len(matchups)} roster matchup records."
)

# ============================================================
# GET WEEKLY PLAYER PROJECTIONS
# ============================================================

print("Downloading Sleeper weekly player projections...")

projection_url = (
    f"https://api.sleeper.com/projections/nfl/"
    f"regular/{current_year}/{current_week}"
    f"?season_type=regular"
)

raw_projection_data = fetch_json(projection_url)

if raw_projection_data is None:
    print("WARNING: Could not retrieve projection data.")
    projection_dict = {}

elif isinstance(raw_projection_data, list):
    projection_dict = {
        str(p.get("player_id")): p
        for p in raw_projection_data
        if p.get("player_id")
    }

elif isinstance(raw_projection_data, dict):
    projection_dict = {
        str(player_id): data
        for player_id, data in raw_projection_data.items()
    }

else:
    projection_dict = {}

print(
    f"Loaded projections for {len(projection_dict)} players."
)


def get_projection(player_id):
    """
    Get Sleeper's PPR projection for a player.
    """

    player_id = str(player_id)

    player = projection_dict.get(player_id)

    if not player:
        return 0.0

    # Sleeper projection formats
    for key in [
        "pts_ppr",
        "ppr",
        "points_ppr"
    ]:
        value = player.get(key)

        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass

    return 0.0

print()
print("Projection diagnostic:")

for player_id, projection in list(projection_dict.items())[:5]:
    print(
        player_id,
        projection
    )

print()


# ============================================================
# BUILD LIVE TEAM PROJECTIONS
# ============================================================

live_projection_tracker = {}

for matchup in matchups:

    roster_id = matchup.get("roster_id")

    if roster_id is None:
        continue

    roster_id = str(roster_id)

    starters = matchup.get("starters") or []

    # --------------------------------------------------------
    # CURRENT ACTUAL SCORE
    # --------------------------------------------------------
    #
    # Sleeper's matchup "points" is the actual current score
    # according to the league's scoring settings.
    #
    actual_points = matchup.get("points", 0)

    try:
        actual_points = float(actual_points or 0)
    except (TypeError, ValueError):
        actual_points = 0.0


    # --------------------------------------------------------
    # CURRENT PLAYER POINTS
    # --------------------------------------------------------

    players_points = matchup.get("players_points") or {}


    # --------------------------------------------------------
    # CALCULATE REMAINING STARTERS
    # --------------------------------------------------------

    remaining_players = []

    current_projected_total = actual_points

    for player_id in starters:

        # Sleeper sometimes uses an empty string for an
        # unfilled starting slot.
        if not player_id:
            continue

        player_id = str(player_id)

        # Actual points this player has scored so far.
        actual_player_points = players_points.get(
            player_id,
            0
        )

        try:
            actual_player_points = float(
                actual_player_points or 0
            )
        except (TypeError, ValueError):
            actual_player_points = 0.0


        # Projection for the full game.
        full_game_projection = get_projection(
            player_id
        )


        # ----------------------------------------------------
        # IMPORTANT:
        #
        # We don't want to add the full projection to a player
        # who has already accumulated points.
        #
        # Instead:
        #
        # remaining projection =
        # full projection - points already scored
        #
        # Never allow it to go below zero.
        # ----------------------------------------------------

        remaining_projection = max(
            0.0,
            full_game_projection - actual_player_points
        )


        # If this player has already scored points, determine
        # whether they still have a game remaining.
        #
        # Sleeper's public matchup data doesn't always provide
        # a perfect "game started/game finished" flag, so we
        # use the projection vs. actual score as the fallback.
        #
        # A player with remaining projection is considered
        # potentially active.
        if remaining_projection > 0.01:

            remaining_players.append({
                "player_id": player_id,
                "actual_points": round(
                    actual_player_points,
                    2
                ),
                "projection": round(
                    full_game_projection,
                    2
                ),
                "remaining_projection": round(
                    remaining_projection,
                    2
                )
            })


        # Sleeper's current actual score already includes the
        # points earned by this player.
        #
        # Add only the player's remaining projected points.
        current_projected_total += remaining_projection


    # --------------------------------------------------------
    # STORE TEAM DATA
    # --------------------------------------------------------

    live_projection_tracker[roster_id] = {

        "roster_id": int(roster_id),

        "current_score": round(
            actual_points,
            2
        ),

        "projected_score": round(
            current_projected_total,
            2
        ),

        "points_remaining": round(
            current_projected_total - actual_points,
            2
        ),

        "players_remaining": len(
            remaining_players
        ),

        "remaining_players": remaining_players
    }


# ============================================================
# EXPORT
# ============================================================

with open(
    "live_projections.json",
    "w"
) as f:

    json.dump(
        live_projection_tracker,
        f,
        indent=4
    )


# ============================================================
# CONSOLE SUMMARY
# ============================================================

print()
print("==========================================")
print(" LIVE PROJECTION TRACKER")
print("==========================================")

for roster_id, team in live_projection_tracker.items():

    print(
        f"Roster {roster_id}: "
        f"{team['current_score']:.2f} "
        f"→ "
        f"{team['projected_score']:.2f} "
        f"("
        f"{team['players_remaining']} players remaining"
        f")"
    )

print()
print(
    "Live projection tracker completed successfully!"
)
