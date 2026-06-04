// Automatically detects your GitHub URL pathing structure
const REPO_NAME = window.location.pathname.split('/')[1] || "";
const IS_GITHUB_PAGES = window.location.hostname.includes("github.io");
const BASE_PATH = IS_GITHUB_PAGES ? `/${REPO_NAME}` : "";

// Fixed URL targeting
const MASTER_PLAYERS_URL = `${BASE_PATH}/public/players.json`;
const WEEKLY_STATS_URL = "https://sleeper.app";
const WEEKLY_PROJ_URL = "https://sleeper.app";

let masterPlayers = {};
let weeklyStats = {};
let weeklyProjections = {};

const sampleRosterIds = ["4034", "6794", "1466", "4029"];

async function initializeDashboard() {
    const statusEl = document.getElementById("status");
    try {
        statusEl.innerText = "Loading global player metrics from cache...";
        
        // 1. Fetch player master data first (Critical dependency)
        const playersRes = await fetch(MASTER_PLAYERS_URL);
        if (!playersRes.ok) throw new Error("Could not load local players.json cache");
        masterPlayers = await playersRes.json();

        // 2. Fetch live endpoints individually so an off-season error won't crash the page
        statusEl.innerText = "Connecting to Sleeper live feeds...";
        try {
            const statsRes = await fetch(WEEKLY_STATS_URL);
            if (statsRes.ok) weeklyStats = await statsRes.json();
        } catch(e) { console.warn("Live stats currently unavailable (Off-season)."); }

        try {
            const projRes = await fetch(WEEKLY_PROJ_URL);
            if (projRes.ok) weeklyProjections = await projRes.json();
        } catch(e) { console.warn("Live projections currently unavailable (Off-season)."); }
        
        statusEl.innerText = "Data loaded successfully. Click a player to view embedded stats.";
        renderRoster(sampleRosterIds);

    } catch (error) {
        console.error("Initialization error:", error);
        statusEl.innerText = `Error: Path issue or missing cache. Double-check that 'public/players.json' exists in your repo.`;
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
