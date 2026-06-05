// Mathematical weighting structure based on Chase Stuart valuation indices
const BASE_PICK_VALS = [
    28.6, 25.4, 23.3, 21.8, 20.6, 19.6, 18.7, 18.0, 17.3, 16.7, 16.2, 15.7, // Rnd 1
    15.3, 14.8, 14.5, 14.1, 13.8, 13.5, 13.2, 12.9, 12.6, 12.4, 12.1, 11.9, // Rnd 2
    11.6, 11.4, 11.2, 11.0, 10.8, 10.6, 10.4, 10.2, 10.0, 9.9,  9.7,  9.5,  // Rnd 3
    9.4,  9.2,  9.1,  8.9,  8.8,  8.6,  8.5,  8.3,  8.2,  8.1,  7.9,  7.8,  // Rnd 4
    7.7,  7.6,  7.4,  7.3,  7.2,  7.1,  7.0,  6.9,  6.8,  6.7,  6.6,  6.5,  // Rnd 5
    6.4,  6.3,  6.2,  6.1,  6.0,  5.9,  5.8,  5.7,  5.6,  5.5,  5.4,  5.4,  // Rnd 6
    5.3,  5.2,  5.1,  5.0,  5.0,  4.9,  4.8,  4.7,  4.7,  4.6,  4.5,  4.5,  // Rnd 7
    4.4,  4.3,  4.3,  4.2,  4.1,  4.1,  4.0,  4.0,  3.9,  3.8,  3.8,  3.7,  // Rnd 8
    3.7,  3.6,  3.6,  3.5,  3.5,  3.4,  3.4,  3.3,  3.3,  3.2,  3.2,  3.1,  // Rnd 9
    3.1,  3.0,  3.0,  2.9,  2.9,  2.8,  2.8,  2.7,  2.7,  2.6,  2.6,  2.5,  // Rnd 10
    2.5,  2.4,  2.4,  2.4,  2.3,  2.3,  2.2,  2.2,  2.1,  2.1,  2.1,  2.0,  // Rnd 11
    2.0,  2.0,  1.9,  1.9,  1.8,  1.8,  1.8,  1.7,  1.7,  1.7,  1.6,  1.6,  // Rnd 12
    1.6,  1.5,  1.5,  1.5,  1.4,  1.4,  1.4,  1.3,  1.3,  1.3,  1.2,  1.2,  // Rnd 13
    1.2,  1.2,  1.1,  1.1,  1.1,  1.0,  1.0,  1.0,  0.9,  0.9,  0.9,  0.9,  // Rnd 14
    0.8,  0.8,  0.8,  0.8,  0.7,  0.7,  0.7,  0.6,  0.6,  0.6,  0.6,  0.5   // Rnd 15
];

let selectedA = [];
let selectedB = [];

function initCalculator() {
    const selectA = document.getElementById('select-pick-a');
    const selectB = document.getElementById('select-pick-b');
    
    // Generate dropdown option fields for a 12-team, 15-round draft matrix (180 total picks)
    for (let round = 1; round <= 15; round++) {
        for (let pick = 1; pick <= 12; pick++) {
            const overallIndex = (round - 1) * 12 + (pick - 1);
            const value = BASE_PICK_VALS[overallIndex] || 0.5;
            
            const pickLabel = `Round ${round}, Pick ${pick} (#${overallIndex + 1} Overall)`;
            
            const optA = document.createElement('option');
            optA.value = JSON.stringify({ label: `Pick ${round}.${pick}`, val: value, id: overallIndex });
            optA.text = `${pickLabel} [Value: ${value}]`;
            selectA.appendChild(optA);

            const optB = document.createElement('option');
            optB.value = JSON.stringify({ label: `Pick ${round}.${pick}`, val: value, id: overallIndex });
            optB.text = `${pickLabel} [Value: ${value}]`;
            selectB.appendChild(optB);
        }
    }

    // Set up active event listeners for your add buttons
    document.getElementById('btn-add-a').onclick = () => addPick('A');
    document.getElementById('btn-add-b').onclick = () => addPick('B');
}

function addPick(side) {
    const select = document.getElementById(`select-pick-${side.toLowerCase()}`);
    if (!select.value) return;

    const data = JSON.parse(select.value);
    
    // Generate a unique identifier timestamp to clear duplicates out safely
    const item = { ...data, uid: Date.now() + Math.random() };

    if (side === 'A') selectedA.push(item);
    else selectedB.push(item);

    renderPicks();
}

function removePick(side, uid) {
    if (side === 'A') selectedA = selectedA.filter(p => p.uid !== uid);
    else selectedB = selectedB.filter(p => p.uid !== uid);
    renderPicks();
}

function renderPicks() {
    const listA = document.getElementById('list-picks-a');
    const listB = document.getElementById('list-picks-b');
    
    listA.innerHTML = "";
    listB.innerHTML = "";

    let totalA = 0;
    let totalB = 0;

    // Render Side A Assets
    selectedA.forEach(pick => {
        totalA += pick.val;
        listA.appendChild(createPickElement('A', pick));
    });

    // Render Side B Assets
    selectedB.forEach(pick => {
        totalB += pick.val;
        listB.appendChild(createPickElement('B', pick));
    });

    document.getElementById('total-val-a').innerText = totalA.toFixed(1);
    document.getElementById('total-val-b').innerText = totalB.toFixed(1);

    evaluateTradeFairness(totalA, totalB);
}

function createPickElement(side, pick) {
    const div = document.createElement('div');
    div.className = 'pick-item';
    div.innerHTML = `
        <span class="pick-label">${pick.label} <span class="pick-value-tag">(Value: ${pick.val})</span></span>
        <button class="btn-remove">×</button>
    `;
    div.querySelector('.btn-remove').onclick = () => removePick(side, pick.uid);
    return div;
}

function evaluateTradeFairness(valA, valB) {
    const panel = document.getElementById('summary-panel');
    const text = document.getElementById('verdict-text');
    const subtext = document.getElementById('verdict-subtext');

    // Clean old style class configurations out
    panel.className = "summary-panel";

    if (valA === 0 && valB === 0) {
        text.innerText = "Add picks to evaluate trade fairness";
        subtext.innerText = "Calculator ready.";
        panel.classList.add('fair-trade');
        return;
    }

    const diff = Math.abs(valA - valB);
    const higher = Math.max(valA, valB);
    
    // A trade is considered "fair" if asset margins sit within a 12% discrepancy threshold
    const percentDiff = higher > 0 ? (diff / higher) * 100 : 0;

    if (percentDiff <= 12) {
        text.innerText = "⚖️ Fair Trade";
        subtext.innerText = `Value discrepancy is minor (${diff.toFixed(1)} pts). Both sides receive equivalent asset value.`;
        panel.classList.add('fair-trade');
    } else if (valA > valB) {
        text.innerText = "🔵 Team A Wins the Trade";
        subtext.innerText = `Team A receives significantly lower pick value. Side B has an advantage of +${diff.toFixed(1)} pts.`;
        panel.classList.add('side-a-wins');
    } else {
        text.innerText = "💗 Team B Wins the Trade";
        subtext.innerText = `Team B receives significantly lower pick value. Side A has an advantage of +${diff.toFixed(1)} pts.`;
        panel.classList.add('side-b-wins');
    }
}

window.onload = initCalculator;
