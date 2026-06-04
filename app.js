// Configuration variables
const MASTER_PLAYERS_URL = "./public/players.json";
const WEEKLY_STATS_URL = "https://sleeper.app";
const WEEKLY_PROJ_URL = "https://sleeper.app";

// Global data stores
let masterPlayers = {};
let weeklyStats = {};
let weeklyProjections = {};

// Hardcoded sample roster matching standard Sleeper IDs (Mahomes, Jefferson, Kelce, McCaffrey)
const sampleRosterIds = ["4034", "6794", "1466", "4029"];

async function initializeDashboard() {
    const statusEl = document.getElementById("status");
    try {
        statusEl.innerText = "Loading global player metrics from cache...";
        
        // Fetch all dependencies in a single async cluster
        const [playersRes, statsRes, projRes] = await Promise.all([
            fetch(MASTER_PLAYERS_URL),
            fetch(WEEKLY_STATS_URL),
            fetch(WEEKLY_PROJ_URL)
        ]);

        masterPlayers = await playersRes.json();
        weeklyStats = await statsRes.json();
        weeklyProjections = await projRes.json();
        
        statusEl.innerText = "Data loaded successfully. Click a player to view embedded stats.";
        renderRoster(sampleRosterIds);

    } catch (error) {
        console.error("Initialization error:", error);
        statusEl.innerText = "Error loading data. Run your GitHub Action manually to generate the player cache file.";
    }
}

function renderRoster(playerIds) {
    const container = document.getElementById("roster-container");
    container.innerHTML = ""; // Clear existing

    playerIds.forEach(id => {
        const player = masterPlayers[id];
        if (!player) return; // Skip if ID is missing in database

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

    // Map content cleanly to popup elements
    document.getElementById("modal-name").innerText = `${player.first_name} ${player.last_name}`;
    document.getElementById("modal-pos").innerText = player.position || "N/A";
    document.getElementById("modal-team").innerText = player.team || "Free Agent";
    
    // Fallback to 0 if data isn't generated for that target week yet
    document.getElementById("modal-proj").innerText = projections.pts_half_ppr ? projections.pts_half_ppr.toFixed(2) : "0.00";
    document.getElementById("modal-actual").innerText = stats.pts_half_ppr ? stats.pts_half_ppr.toFixed(2) : "0.00";

    // Open modal backdrop and window
    document.getElementById("modal-overlay").classList.add("show");
    document.getElementById("stats-modal").classList.add("show");
}

function closeModal() {
    document.getElementById("modal-overlay").classList.remove("show");
    document.getElementById("stats-modal").classList.remove("show");
}

// Fire application initialization
initializeDashboard();
