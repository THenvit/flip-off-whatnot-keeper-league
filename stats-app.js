// Global variables dynamically assigned on load
let LEAGUE_ID = ""; 
let globalPlayersDb = {};
let completeLeagueData = [];

async function initDashboard() {
    const statusDiv = document.getElementById('status');
    try {
        statusDiv.innerText = "Loading configuration setup...";
        
        // 1. Fetch dynamic config.json settings to parse your current league ID
        const configRes = await fetch("config.json");
        const configData = await configRes.json();
        LEAGUE_ID = configData.LEAGUE_ID;

        if (!LEAGUE_ID) {
            throw new Error("LEAGUE_ID variable missing from config.json");
        }

        // 2. Fetch cached player data assets from your morning cron job file
        statusDiv.innerText = "Loading cached player database (this can take a few seconds)...";
        const playersResponse = await fetch('public/players.json');
        globalPlayersDb = await playersResponse.json() || {};

        // 3. Construct API endpoints securely using standard concatenation
        const baseUrl = 'https://api.sleeper.app/v1/league/' + LEAGUE_ID;
        const usersUrl = baseUrl + '/users';
        const rostersUrl = baseUrl + '/rosters';

        statusDiv.innerText = "Connecting to Sleeper: Fetching league managers...";
        const usersResponse = await fetch(usersUrl);
        const usersData = await usersResponse.json() || [];

        statusDiv.innerText = "Connecting to Sleeper: Fetching league rosters...";
        const rostersResponse = await fetch(rostersUrl);
        const rostersData = await rostersResponse.json() || [];

        statusDiv.innerText = "Processing standings and calculating records...";

            // Bulletproof standings calculation with fallback safeguards
        const sortedRostersForStandings = [...rostersData].sort((a, b) => {
            const winsA = a.settings?.wins || 0;
            const winsB = b.settings?.wins || 0;
            if (winsB !== winsA) return winsB - winsA;
            
            const pointsA = (a.settings?.fpts || 0) + (a.settings?.fpts_decimal || 0) / 100;
            const pointsB = (b.settings?.fpts || 0) + (b.settings?.fpts_decimal || 0) / 100;
            return pointsB - pointsA;
        });

        // 4. Map users to a helper lookup object
        const usersMap = {};
        usersData.forEach(user => {
            if (user && user.user_id) {
                usersMap[user.user_id] = {
                    teamName: user.metadata?.team_name || user.display_name || "Unknown Team",
                    ownerName: user.display_name || "Unknown Owner"
                };
            }
        });

        // 5. Combine rosters with user data and player metadata
        completeLeagueData = rostersData.map(roster => {
            if (!roster) return null;
            const owner = usersMap[roster.owner_id] || { teamName: 'Team ' + (roster.roster_id || ''), ownerName: "Unknown Owner" };
            
            const startersList = roster.starters || [];
            const taxiList = roster.taxi || [];
            const allPlayersList = roster.players || [];

            // Calculate precise record variables safely
            const wins = roster.settings?.wins || 0;
            const losses = roster.settings?.losses || 0;
            const ties = roster.settings?.ties || 0;
            const recordStr = ties > 0 ? (wins + '-' + losses + '-' + ties) : (wins + '-' + losses);
            
            // Find numerical position rank out of the sorted standings list array
            const standingRank = sortedRostersForStandings.findIndex(r => r.roster_id === roster.roster_id) + 1;

            // Resolve player strings to database profiles and assign lineup statuses
            const playerProfiles = allPlayersList.map(id => {
                const baseProfile = globalPlayersDb[id] || { 
                    player_id: id, 
                    first_name: "Unknown", 
                    last_name: "Player (" + id + ")", 
                    position: "N/A", 
                    team: "N/A",
                    injury_status: null
                };
                let slotType = "Bench";
                let starterIndex = startersList.indexOf(id);
                
                if (starterIndex !== -1) {
                    slotType = "Starter";
                } else if (taxiList.includes(id)) {
                    slotType = "Taxi";
                }
                return {
                    ...baseProfile,
                    slotType: slotType,
                    starterOrder: starterIndex
                };
            });

            return {
                rosterId: roster.roster_id,
                teamName: owner.teamName,
                ownerName: owner.ownerName,
                record: recordStr,
                rank: standingRank || 1,
                players: playerProfiles
            };
        }).filter(Boolean); // Cleans out null items safely

        // Sort displayed teams alphabetically by name
        completeLeagueData.sort((a, b) => (a.teamName || "").localeCompare(b.teamName || ""));

        // 6. Setup the dropdown choices
        populateDropdown(completeLeagueData);
        
        // 7. Initial render (show everything)
        statusDiv.innerText = "Building user interface...";
        renderDashboard("all");
        statusDiv.style.display = "none"; // Hide standard message logs cleanly on success

    } catch (error) {
        console.error("Dashboard error detail log:", error);
        statusDiv.innerText = "Error loading metrics! Check browser console logs for context.";
    }
}

function populateDropdown(teams) {
    const select = document.getElementById('team-select');
    if (!select) return;
    
    // Reset options
    select.innerHTML = '<option value="all">-- All Teams --</option>';
    
    teams.forEach(team => {
        if (!team) return;
        const opt = document.createElement('option');
        opt.value = team.rosterId;
        // Restructured selection labels to include parenthetical formatting
        opt.text = team.teamName + " (" + team.ownerName + ") [Rank: #" + team.rank + "]";
        select.appendChild(opt);
    });
    select.disabled = false;
    
    // Clear old listener references
    select.onchange = (e) => renderDashboard(e.target.value);
}

function renderDashboard(filterValue) {
    const container = document.getElementById('dashboard-container');
    if (!container) return;
    container.innerHTML = ""; 

    const teamsToDisplay = filterValue === "all" 
        ? completeLeagueData 
        : completeLeagueData.filter(t => t && t.rosterId.toString() === filterValue);

    teamsToDisplay.forEach(team => {
        if (!team) return;

        const section = document.createElement('div');
        section.className = 'team-section';

        const title = document.createElement('div');
        title.className = 'team-title';
        title.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; flex-wrap: wrap; gap: 8px;">
                <span><strong>${team.teamName}</strong> <small style="font-size: 13px; color: var(--text-muted); font-weight: normal;">(${team.ownerName})</small></span>
                <span style="font-size: 13px; background: #e2e8f0; color: #334155; padding: 4px 12px; border-radius: 20px; font-weight: 600;">Rank: #${team.rank} (${team.record})</span>
            </div>
        `;
        section.appendChild(title);

        const starters = team.players.filter(p => p.slotType === "Starter").sort((a, b) => a.starterOrder - b.starterOrder);
        const bench = team.players.filter(p => p.slotType === "Bench").sort((a, b) => (a.position || "").localeCompare(b.position || ""));
        const taxi = team.players.filter(p => p.slotType === "Taxi").sort((a, b) => (a.position || "").localeCompare(b.position || ""));

        const createSubSection = (label, playerArray, badgeClass) => {
            if (playerArray.length === 0) return;

            const subHeader = document.createElement('h4');
            subHeader.style.margin = "20px 0 10px 0";
            subHeader.style.color = "var(--text-muted)";
            subHeader.style.fontSize = "0.9rem";
            subHeader.style.textTransform = "uppercase";
            subHeader.style.letterSpacing = "0.05em";
            subHeader.innerText = label;
            section.appendChild(subHeader);

            const grid = document.createElement('div');
            grid.className = 'roster-grid';

            playerArray.forEach(player => {
                const card = document.createElement('div');
                
                // Determine injury CSS modifier classes
                let injuryClass = "";
                const statusLower = (player.injury_status || "").toLowerCase();
                
                if (statusLower === "out") injuryClass = "injury-out";
                else if (statusLower === "questionable") injuryClass = "injury-questionable";
                else if (statusLower === "ir" || statusLower === "injured") injuryClass = "injury-ir";
                else if (statusLower === "doubtful") injuryClass = "injury-doubtful";

                card.className = 'player-card ' + injuryClass;
                card.onclick = () => openModal(player.player_id);

                const pos = player.position || 'N/A';
                
                // 🎨 CUSTOM THEME COLOR MAPPINGS
                let posColor = '#64748b';
                if (pos === 'QB') posColor = '#dc2626';      // Crisp Red
                else if (pos === 'RB') posColor = '#2563eb'; // Crisp Blue
                else if (pos === 'WR') posColor = '#16a34a'; // Crisp Green
                else if (pos === 'TE') posColor = '#ea580c'; // Warm Orange
                else if (pos === 'K') posColor = '#7c3aed';  // Purple
                else if (pos === 'DEF') posColor = '#4b5563'; // Slate Gray

                const fullName = (player.first_name || '') + ' ' + (player.last_name || '');
                
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
                        <div class="player-name">${fullName}</div>
                        <span style="background: ${posColor}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; min-width: 32px; text-align: center;">${pos}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 5px; width: 100%;" class="player-meta">
                        <span>${player.team || 'FA'} — <span class="slot-badge ${badgeClass}">${player.slotType}</span></span>
                        ${player.injury_status ? `<b style="color: #dc2626; font-size: 11px;">[${player.injury_status}]</b>` : ''}
                    </div>
                `;
                grid.appendChild(card);
            });
            section.appendChild(grid);
        };

        // Build the True Team Roster breakdown sub-sections in order
        createSubSection("Starters Lineup", starters, "badge-starter");
        createSubSection("Bench Depth", bench, "badge-bench");
        createSubSection("Taxi Squad", taxi, "badge-taxi");

        container.appendChild(section);
    });
}

// 5. Detail Stats Modal Controller (Fixed Crashes)
function openModal(playerId) {
    const player = globalPlayersDb[playerId];
    if (!player) return;

    const positionRank = player.fantasy_positions_rankings || player.search_rank || "N/A";
    const pos = player.position || "N/A";
    const explicitRankText = positionRank !== "N/A" ? (pos + positionRank) : "N/A";
    const projectedPPR = player.fantasy_points_ppr || player.projected_points || "N/A";

    const nameElem = document.getElementById('modal-name');
    const posElem = document.getElementById('modal-pos');
    const teamElem = document.getElementById('modal-team');
    const statusElem = document.getElementById('modal-status-txt');
    const injuryElem = document.getElementById('modal-injury');
    const rankElem = document.getElementById('modal-rank');
    const projPprElem = document.getElementById('modal-proj-ppr');

    if (nameElem) nameElem.innerText = (player.first_name || '') + ' ' + (player.last_name || '');
    if (posElem) posElem.innerText = pos;
    if (teamElem) teamElem.innerText = player.team || 'Free Agent';
    if (statusElem) statusElem.innerText = player.status || 'Active';
    if (injuryElem) injuryElem.innerText = player.injury_status || 'Healthy';
    if (rankElem) rankElem.innerText = explicitRankText;
    if (projPprElem) projPprElem.innerText = projectedPPR;

    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('stats-modal');
    if (overlay) overlay.classList.add('show');
    if (modal) modal.classList.add('show');
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('stats-modal');
    if (overlay) overlay.classList.remove('show');
    if (modal) modal.classList.remove('show');
}

// Boot up dashboard logic once DOM assets are parsed
window.addEventListener('DOMContentLoaded', initDashboard);


// Boot up dashboard logic once DOM assets are parsed
window.addEventListener('DOMContentLoaded', initDashboard);
