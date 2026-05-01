// app.js - Main application logic for Tower of Hanoi game

// State variables
let disks = [5, 4, 3, 2, 1];
let towers = [[5, 4, 3, 2, 1], [], []];
let selectedDisk = null;
let selectedDiskSize = null;
let sourceTowerIndex = null;
let moveCount = 0;

// DOM Elements
const towerElements = document.querySelectorAll('.tower');
const resetButton = document.getElementById('reset-button');
const moveCounter = document.getElementById('move-counter');

/**
 * Renders all towers based on the current game state
 */
function renderTowers() {
    towerElements.forEach((tower, index) => {
        tower.innerHTML = '';
        
        const towerData = towers[index];
        towerData.forEach((diskSize) => {
            const diskElement = document.createElement('div');
            diskElement.classList.add('disk', `disk-${diskSize}`);
            diskElement.dataset.size = diskSize;
            diskElement.addEventListener('click', handleDiskClick);
            tower.appendChild(diskElement);
        });
    });
    
    updateMoveCounter();
}

/**
 * Handles click event on a disk
 * @param {Event} event - The click event
 */
function handleDiskClick(event) {
    event.stopPropagation();
    
    const diskElement = event.target;
    const diskSize = parseInt(diskElement.dataset.size);
    const towerElement = diskElement.parentNode;
    const towerIndex = parseInt(towerElement.dataset.tower);
    
    // Clear previous selection
    clearSelection();
    
    // Select this disk
    selectedDisk = diskElement;
    selectedDiskSize = diskSize;
    sourceTowerIndex = towerIndex;
    
    diskElement.classList.add('selected');
    towerElement.classList.add('selected');
    
    // Highlight valid and invalid targets
    highlightTargets(diskSize);
}

/**
 * Clears the current selection
 */
function clearSelection() {
    if (selectedDisk) {
        selectedDisk.classList.remove('selected');
    }
    
    towerElements.forEach(tower => {
        tower.classList.remove('selected', 'valid-target', 'invalid-target');
    });
    
    selectedDisk = null;
    selectedDiskSize = null;
    sourceTowerIndex = null;
}

/**
 * Highlights valid and invalid tower targets
 * @param {number} diskSize - The size of the selected disk
 */
function highlightTargets(diskSize) {
    towers.forEach((tower, index) => {
        if (index === sourceTowerIndex) return;
        
        const towerElement = document.getElementById(`tower-${index + 1}`);
        
        if (tower.length === 0 || diskSize < tower[tower.length - 1]) {
            towerElement.classList.add('valid-target');
        } else {
            towerElement.classList.add('invalid-target');
        }
    });
}

/**
 * Handles click event on a tower
 * @param {Event} event - The click event
 */
function handleTowerClick(event) {
    const targetTower = event.currentTarget;
    const targetTowerIndex = parseInt(targetTower.dataset.tower);
    
    // If no disk is selected, do nothing
    if (selectedDisk === null) {
        return;
    }
    
    // If clicking on the same tower, deselect
    if (targetTowerIndex === sourceTowerIndex) {
        clearSelection();
        return;
    }
    
    // Check if move is valid
    const targetTowerData = towers[targetTowerIndex];
    
    if (targetTowerData.length > 0 && selectedDiskSize >= targetTowerData[targetTowerData.length - 1]) {
        // Invalid move - show error
        showError('Cannot place a larger disk on a smaller one!');
        clearSelection();
        return;
    }
    
    // Perform the move
    moveDisk(sourceTowerIndex, targetTowerIndex, selectedDiskSize);
    
    // Clear selection and re-render
    clearSelection();
    renderTowers();
    
    // Check for win condition
    if (checkWin()) {
        showSuccess();
    }
}

/**
 * Moves a disk from one tower to another
 * @param {number} fromIndex - Source tower index
 * @param {number} toIndex - Target tower index
 * @param {number} diskSize - Size of the disk to move
 */
function moveDisk(fromIndex, toIndex, diskSize) {
    // Remove disk from source tower
    const sourceTower = towers[fromIndex];
    const diskIndex = sourceTower.indexOf(diskSize);
    sourceTower.splice(diskIndex, 1);
    
    // Add disk to target tower
    towers[toIndex].push(diskSize);
    
    // Increment move counter
    moveCount++;
}

/**
 * Updates the move counter display
 */
function updateMoveCounter() {
    moveCounter.textContent = `Moves: ${moveCount}`;
}

/**
 * Checks if the player has won (all disks on tower 3)
 * @returns {boolean} True if the player has won
 */
function checkWin() {
    return towers[2].length === 5;
}

/**
 * Shows an error message
 * @param {string} message - The error message to display
 */
function showError(message) {
    // Create temporary error toast
    const errorToast = document.createElement('div');
    errorToast.className = 'error-toast';
    errorToast.textContent = message;
    errorToast.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background-color: #dc3545;
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        z-index: 1000;
        animation: fadeIn 0.3s ease;
    `;
    
    document.body.appendChild(errorToast);
    
    // Remove after 2 seconds
    setTimeout(() => {
        errorToast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(errorToast);
        }, 300);
    }, 2000);
}

/**
 * Shows the success message
 */
function showSuccess() {
    const successOverlay = document.createElement('div');
    successOverlay.className = 'success-overlay';
    successOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 999;
        animation: fadeIn 0.3s ease;
    `;
    
    const successMessage = document.createElement('div');
    successMessage.className = 'success-message';
    successMessage.innerHTML = `
        <h2>🎉 Congratulations!</h2>
        <p>You solved the puzzle in <strong>${moveCount}</strong> moves!</p>
        <p>The minimum moves required: <strong>31</strong></p>
        <button onclick="this.parentElement.remove(); document.querySelector('.success-overlay').remove();">Play Again</button>
    `;
    
    document.body.appendChild(successOverlay);
    document.body.appendChild(successMessage);
}

/**
 * Resets the game to its initial state
 */
function resetGame() {
    disks = [5, 4, 3, 2, 1];
    towers = [[5, 4, 3, 2, 1], [], []];
    selectedDisk = null;
    selectedDiskSize = null;
    sourceTowerIndex = null;
    moveCount = 0;
    
    // Remove any success overlays
    const successOverlay = document.querySelector('.success-overlay');
    const successMessage = document.querySelector('.success-message');
    if (successOverlay) successOverlay.remove();
    if (successMessage) successMessage.remove();
    
    clearSelection();
    renderTowers();
}

// Add event listeners to towers
towerElements.forEach((tower) => {
    tower.addEventListener('click', handleTowerClick);
});

// Add event listener to reset button
resetButton.addEventListener('click', resetGame);

// Add CSS animation for toasts
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initial render
renderTowers();