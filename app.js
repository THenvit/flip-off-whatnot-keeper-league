const GITHUB_USERNAME = "thenvit"; 
const REPO_NAME = "flip-off-whatnot-keeper-league";
const MASTER_PLAYERS_URL = `https://${GITHUB_USERNAME}.github.io/${REPO_NAME}/public/players.json`;

const WEEKLY_STATS_URL = "https://sleeper.app";
const WEEKLY_PROJ_URL = "https://sleeper.app";

let masterPlayers = {};
let weeklyStats = {};
let weeklyProjections = {};

const sampleRosterIds = ["4034", "6794", "1466", "4029"];

async function initializeDashboard() {
    const statusEl = document.getElementById("status");
    try {
        statusEl.innerText = `Connecting to your database stream...`;
        console.log("Requesting data from absolute path:", MASTER_PLAYERS_URL);
        
        // Added 'reload' cache flag to destroy old browser memory loop errors
        const playersRes = await fetch(MASTER_PLAYERS_URL, { cache: "reload" });
        
        if (!playersRes.ok) {
            throw new Error(`HTTP Error Status: ${playersRes.status}`);
        }
        
        // Parse the text data safely into JSON memory
        masterPlayers = await playersRes.json();

        statusEl.innerText = "Connecting to Sleeper live feeds...";
        try {
            const statsRes = await fetch(WEEKLY_STATS_URL);
            if (statsRes.ok) weeklyStats = await statsRes.json();
        } catch(e) { console.warn("Live stats currently offline (Off-season)."); }

        try {
            const projRes = await fetch(WEEKLY_PROJ_URL);
            if (projRes.ok) weeklyProjections = await projRes.json();
        } catch(e) { console.warn("Live projections currently offline (Off-season)."); }
        
        statusEl.innerText = "Data loaded successfully! Click any player card below.";
        renderRoster(sampleRosterIds);

    } catch (error) {
        console.error("Detailed failure context:", error);
        statusEl.innerText = `Error processing data. Check your browser console (F12) to see if security software or a browser extension is blocking the file download.`;
    }
}

function renderRoster(playerIds) {
    const container = document.getElementById("roster-container");
    container.innerHTML = ""; 

    playerIds.forEach(id => {
        const player = masterPlayers[id];
        if (!player) return; 

        const card = document.createElement("div");
        card.className = "player-card";
        card.setAttribute("onclick", `openPlayerStats("${id}")`);
        
        card.innerHTML = `
            <div class="player-name">${player.first_name} ${player.last_name}</div>
            <div class="player-meta">${player.position || 'N/A'} — ${player.team || 'FA'}</div>
        `;
        container.appendChild(card);
    });
}

function openPlayerStats(playerId) {
    const player = masterPlayers[playerId];
    if (!player) return;

    const stats = weeklyStats[playerId] || {};
    const projections = weeklyProjections[playerId] || {};

    document.getElementById("modal-name").innerText = `${player.first_name} ${player.last_name}`;
    document.getElementById("modal-pos").innerText = player.position || "N/A";
    document.getElementById("modal-team").innerText = player.team || "Free Agent";
    
    document.getElementById("modal-proj").innerText = projections.pts_half_ppr ? projections.pts_half_ppr.toFixed(2) : "0.00";
    document.getElementById("modal-actual").innerText = stats.pts_half_ppr ? stats.pts_half_ppr.toFixed(2) : "0.00";

    document.getElementById("modal-overlay").classList.add("show");
    document.getElementById("stats-modal").classList.add("show");
}

function closeModal() {
    document.getElementById("modal-overlay").classList.remove("show");
    document.getElementById("stats-modal").classList.remove("show");
}

initializeDashboard();
