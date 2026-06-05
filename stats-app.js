// CONFIGURATION: Replace this with your actual 18-digit Sleeper League ID
const LEAGUE_ID = "1312583156339064832"; 

let globalPlayersDb = {};
let completeLeagueData = [];

async function initDashboard() {
    const statusDiv = document.getElementById('status');
    
    if (LEAGUE_ID === "YOUR_SLEEPER_LEAGUE_ID_HERE") {
        statusDiv.innerText = "Error: Please edit stat-app.js and set your actual LEAGUE_ID variable.";
        return;
    }

    try {
        // 1. Fetch your cached players data from your github workflow file path
        statusDiv.innerText = "Loading cached player database...";
        const playersResponse = await fetch('public/players.json');
        globalPlayersDb = await playersResponse.json();

        // 2. Fetch active league managers/users from Sleeper API
        statusDiv.innerText = "Fetching league managers...";
        const usersResponse = await fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/users`);
        const usersData = await usersResponse.json();

        // 3. Fetch active league rosters from Sleeper API
        statusDiv.innerText = "Fetching league rosters...";
        const rostersResponse = await fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/rosters`);
        const rostersData = await rostersResponse.json();

        // 4. Map users to a helper lookup object
      
        // Sort rosters dynamically to calculate standings ranking (Wins -> Points For)
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
            usersMap[user.user_id] = {
                teamName: user.metadata.team_name || user.display_name,
                ownerName: user.display_name
            };
        });

        // 5. Combine rosters with user data, mapping roster slots and record details
        completeLeagueData = rostersData.map(roster => {
            const owner = usersMap[roster.owner_id] || { teamName: `Team ${roster.roster_id}`, ownerName: "Unknown" };
            
            const startersList = roster.starters || [];
            const taxiList = roster.taxi || [];
            const allPlayersList = roster.players || [];

            // Calculate precise record variables
            const wins = roster.settings?.wins || 0;
            const losses = roster.settings?.losses || 0;
            const ties = roster.settings?.ties || 0;
            const recordStr = ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
            
            // Find numerical position rank out of the sorted standings list array
            const standingRank = sortedRostersForStandings.findIndex(r => r.roster_id === roster.roster_id) + 1;

            // Resolve player strings to database profiles and assign lineup statuses
            const playerProfiles = allPlayersList.map(id => {
                const baseProfile = globalPlayersDb[id] || { 
                    player_id: id, 
                    first_name: "Unknown", 
                    last_name: `Player (${id})`, 
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
                rank: standingRank,
                players: playerProfiles
            };
        });

        // Sort displayed teams alphabetically by name
        completeLeagueData.sort((a, b) => a.teamName.localeCompare(b.teamName));

        // 6. Setup the dropdown choices
        populateDropdown(completeLeagueData);
        
        // 7. Initial render (show everything)
        renderDashboard("all");
        statusDiv.innerText = "Data loaded successfully.";

    } catch (error) {
        console.error(error);
        statusDiv.innerText = "Error loading data. Check console logs and verify your League ID.";
    }
}

function populateDropdown(teams) {
    const select = document.getElementById('team-select');
    teams.forEach(team => {
        const opt = document.createElement('option');
        opt.value = team.rosterId;
        opt.text = `${team.teamName} (Rank: #${team.rank})`;
        select.appendChild(opt);
    });
    select.disabled = false;
    select.addEventListener('change', (e) => renderDashboard(e.target.value));
}

function renderDashboard(filterValue) {
    const container = document.getElementById('dashboard-container');
    container.innerHTML = ""; 

    const teamsToDisplay = filterValue === "all" 
        ? completeLeagueData 
        : completeLeagueData.filter(t => t.rosterId.toString() === filterValue);

    teamsToDisplay.forEach(team => {
        const section = document.createElement('div');
        section.className = 'team-section';

        const title = document.createElement('div');
        title.className = 'team-title';
        title.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${team.teamName} <small style="font-size: 13px; color: #666; font-weight: normal;">(${team.ownerName})</small></span>
                <span style="font-size: 14px; background: #e5e7eb; color: #374151; padding: 4px 10px; border-radius: 20px;">Rank: #${team.rank} (${team.record})</span>
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
            subHeader.style.color = "#555";
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

                card.className = `player-card ${injuryClass}`;
                card.onclick = () => openModal(player.player_id);

                const pos = player.position || 'N/A';
                let posColor = '#6b7280';
                if (pos === 'QB') posColor = '#ff4d4d';
                else if (pos === 'RB') posColor = '#3b82f6';
                else if (pos === 'WR') posColor = '#10b981';
                else if (pos === 'TE') posColor = '#f59e0b';
                else if (pos === 'K') posColor = '#a855f7';
                else if (pos === 'DEF') posColor = '#6b7280';

                const fullName = `${player.first_name || ''} ${player.last_name || ''}`;
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div class="player-name">${fullName}</div>
                        <span style="background: ${posColor}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold;">${pos}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 5px;" class="player-meta">
                        <span>${player.team || 'FA'} — <span class="slot-badge ${badgeClass}">${player.slotType}</span></span>
                        ${player.injury_status ? `<b style="color: #dc2626; font-size: 11px;">[${player.injury_status}]</b>` : ''}
                    </div>
                `;
                grid.appendChild(card);
            });
            section.appendChild(grid);
        };

        createSubSection("Starters", starters, "badge-starter");
        createSubSection("Bench", bench, "badge-bench");
        createSubSection("Taxi Squad", taxi, "badge-taxi");

        container.appendChild(section);
    });
}

// Modal Functionality for Detailed Stats View
function openModal(playerId) {
    const player = globalPlayersDb[playerId];
    if (!player) return;

    // Resolve dynamic player metadata metrics embedded inside Sleeper records
    const positionRank = player.fantasy_positions_rankings || player.search_rank || "N/A";
    const pos = player.position || "N/A";
    const explicitRankText = positionRank !== "N/A" ? `${pos}${positionRank}` : "N/A";

    // Grab fantasy projection arrays if present, otherwise set baseline metrics
    const projectedPPR = player.fantasy_points_ppr || player.projected_points || "N/A";

    document.getElementById('modal-name').innerText = `${player.first_name || ''} ${player.last_name || ''}`;
    document.getElementById('modal-pos').innerText = pos;
    document.getElementById('modal-team').innerText = player.team || 'Free Agent';
    document.getElementById('modal-status-txt').innerText = player.status || 'Active';
    document.getElementById('modal-injury').innerText = player.injury_status || 'Healthy';
    
    // Write properties directly to our interface hooks
    document.getElementById('modal-rank').innerText = explicitRankText;
    document.getElementById('modal-proj-ppr').innerText = projectedPPR;

    document.getElementById('modal-overlay').classList.add('show');
    document.getElementById('stats-modal').classList.add('show');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('show');
    document.getElementById('stats-modal').classList.remove('show');
}

window.onload = initDashboard;
