/**
 * App Module
 * Handles DOM interaction, rendering, and event listeners.
 */

// DOM Elements
const rodElements = [
    document.getElementById('rod-1'),
    document.getElementById('rod-2'),
    document.getElementById('rod-3')
];
const resetButton = document.getElementById('reset-button');

// Game State
let selectedRodIndex = null;
let isGameWon = false;

// Disk Colors based on size (Index 0 is unused, 1-5 map to sizes)
// Blueprint colors: #ccc, #aaa, #888, #666, #444
// Mapping: Size 5 (largest) -> #444, Size 1 (smallest) -> #ccc
const getDiskColor = (size) => {
    const colors = {
        5: '#444',
        4: '#666',
        3: '#888',
        2: '#aaa',
        1: '#ccc'
    };
    return colors[size] || '#999';
};

// Initialize Game
function initGame() {
    isGameWon = false;
    selectedRodIndex = null;
    Hanoi.init();
    render();
}

// Render the current state to the DOM
function render() {
    const state = Hanoi.getState();
    
    // Clear all rods visually first
    rodElements.forEach(rod => {
        // Remove existing disks, keep the rod structure
        const existingDisks = rod.querySelectorAll('.disk');
        existingDisks.forEach(d => d.remove());
        rod.classList.remove('selected');
    });

    // Render disks for each rod
    state.rods.forEach((rodData, index) => {
        const rodElement = rodElements[index];
        
        // Highlight selected rod
        if (selectedRodIndex === index) {
            rodElement.classList.add('selected');
        }

        rodData.forEach(diskSize => {
            const diskElement = document.createElement('div');
            diskElement.classList.add('disk');
            
            // Styling based on size
            // Width percentage: larger size = larger width
            // Base width 30%, max 90%
            const widthPercent = 30 + (diskSize * 12); 
            diskElement.style.width = `${widthPercent}%`;
            diskElement.style.backgroundColor = getDiskColor(diskSize);
            
            // Add click event to disk (delegates to rod click logic mostly, but specific for selection)
            diskElement.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent bubbling to rod if not needed, though we handle logic in rod click usually
                handleRodClick(index);
            });

            rodElement.appendChild(diskElement);
        });
    });
}

// Handle Rod Interaction
function handleRodClick(rodIndex) {
    if (isGameWon) return;

    // Case 1: No rod selected yet -> Select source
    if (selectedRodIndex === null) {
        // If clicking an empty rod, do nothing
        const state = Hanoi.getState();
        if (state.rods[rodIndex].length === 0) return;
        
        selectedRodIndex = rodIndex;
        render();
    } 
    // Case 2: Rod already selected
    else {
        // If clicking the same rod, deselect
        if (selectedRodIndex === rodIndex) {
            selectedRodIndex = null;
            render();
            return;
        }

        // Attempt to move
        const result = Hanoi.moveDisk(selectedRodIndex, rodIndex);
        
        if (result.success) {
            selectedRodIndex = null;
            render();
            
            if (Hanoi.checkWin()) {
                isGameWon = true;
                setTimeout(() => {
                    alert("Congratulations! You solved the Tower of Hanoi!");
                    initGame();
                }, 100);
            }
        } else {
            // Invalid move feedback (shake animation or console log)
            console.log(result.message);
            // Deselect on invalid move to reset state cleanly or keep selected? 
            // Usually keeping selected allows user to try another rod.
            // Let's keep it selected but maybe flash red in a more complex app.
        }
    }
}

// Event Listeners
rodElements.forEach((rod, index) => {
    rod.addEventListener('click', () => {
        handleRodClick(index);
    });
});

resetButton.addEventListener('click', () => {
    initGame();
});

// Start the game
initGame();