// CONFIGURATION: Replace this with your actual 18-digit Sleeper League ID
const LEAGUE_ID = "1312583156339064832"; 

let globalPlayersDb = {};
let completeLeagueData = [];

async function initDashboard() {
    const statusDiv = document.getElementById('status');
    
    if (LEAGUE_ID === "YOUR_SLEEPER_LEAGUE_ID_HERE") {
        statusDiv.innerText = "Error: Please edit app.js and set your actual LEAGUE_ID variable.";
        return;
    }

    try {
        // 1. Fetch your cached players data from your github workflow file path
        statusDiv.innerText = "Loading cached player database...";
        const playersResponse = await fetch('public/players.json');
        globalPlayersDb = await playersResponse.json();

        // 2. Fetch active league managers/users from Sleeper API
        statusDiv.innerText = "Fetching league managers...";
        const usersResponse = await fetch(`https://sleeper.app{LEAGUE_ID}/users`);
        const usersData = await usersResponse.json();

        // 3. Fetch active league rosters from Sleeper API
        statusDiv.innerText = "Fetching league rosters...";
        const rostersResponse = await fetch(`https://sleeper.app{LEAGUE_ID}/rosters`);
        const rostersData = await rostersResponse.json();

        // 4. Map users to a helper lookup object
        const usersMap = {};
        usersData.forEach(user => {
            usersMap[user.user_id] = {
                teamName: user.metadata.team_name || user.display_name,
                ownerName: user.display_name
            };
        });

        // 5. Combine rosters with user data and player metadata
        completeLeagueData = rostersData.map(roster => {
            const owner = usersMap[roster.owner_id] || { teamName: `Team ${roster.roster_id}`, ownerName: "Unknown" };
            
            // Resolve player strings to database profiles
            const playerProfiles = (roster.players || []).map(id => {
                return globalPlayersDb[id] || { player_id: id, first_name: "Unknown", last_name: `Player (${id})`, position: "N/A", team: "N/A" };
            });

            return {
                rosterId: roster.roster_id,
                teamName: owner.teamName,
                ownerName: owner.ownerName,
                players: playerProfiles
            };
        });

        // Sort teams alphabetically
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
        opt.text = team.teamName;
        select.appendChild(opt);
    });
    select.disabled = false;
    select.addEventListener('change', (e) => renderDashboard(e.target.value));
}

function renderDashboard(filterValue) {
    const container = document.getElementById('dashboard-container');
    container.innerHTML = ""; // Wipe older views

    // Filter teams based on user dropdown selection
    const teamsToDisplay = filterValue === "all" 
        ? completeLeagueData 
        : completeLeagueData.filter(t => t.rosterId.toString() === filterValue);

    teamsToDisplay.forEach(team => {
        // Create a block section for the team container
        const section = document.createElement('div');
        section.className = 'team-section';

        const title = document.createElement('div');
        title.className = 'team-title';
        title.innerText = `${team.teamName} (${team.ownerName})`;
        section.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'roster-grid';

        // Sort players by position (e.g., QB, RB, WR, TE)
        const sortedPlayers = [...team.players].sort((a,b) => (a.position || "").localeCompare(b.position || ""));

        sortedPlayers.forEach(player => {
            const card = document.createElement('div');
            card.className = 'player-card';
            card.onclick = () => openModal(player.player_id);

            const fullName = `${player.first_name || ''} ${player.last_name || ''}`;
            card.innerHTML = `
                <div class="player-name">${fullName}</div>
                <div class="player-meta">${player.position || 'N/A'} - ${player.team || 'FA'}</div>
            `;
            grid.appendChild(card);
        });

        section.appendChild(grid);
        container.appendChild(section);
    });
}

// Modal Functionality
function openModal(playerId) {
    const player = globalPlayersDb[playerId];
    if (!player) return;

    document.getElementById('modal-name').innerText = `${player.first_name || ''} ${player.last_name || ''}`;
    document.getElementById('modal-pos').innerText = player.position || 'N/A';
    document.getElementById('modal-team').innerText = player.team || 'Free Agent';
    document.getElementById('modal-status-txt').innerText = player.status || 'Active';
    document.getElementById('modal-injury').innerText = player.injury_status || 'Healthy';

    document.getElementById('modal-overlay').classList.add('show');
    document.getElementById('stats-modal').classList.add('show');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('show');
    document.getElementById('stats-modal').classList.remove('show');
}

// Boot everything up on load
window.onload = initDashboard;
