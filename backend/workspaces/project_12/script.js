/**
 * Etch-a-Sketch — Core Logic
 * Handles grid creation, drawing, rainbow mode, and clear functionality
 */

// DOM Element References
const gridContainer = document.getElementById('grid-container');
const clearButton = document.getElementById('clear-button');
const rainbowButton = document.getElementById('rainbow-button');
const modeText = document.getElementById('mode-text');

// Application State
let rainbowMode = false;
const GRID_SIZE = 16;
const TOTAL_SQUARES = GRID_SIZE * GRID_SIZE;

/**
 * Initialize the application
 */
function init() {
    createGrid();
    attachEventListeners();
}

/**
 * Create the 16x16 grid dynamically
 */
function createGrid() {
    // Clear any existing content (defensive)
    gridContainer.innerHTML = '';
    
    // Create grid squares
    for (let i = 0; i < TOTAL_SQUARES; i++) {
        const gridSquare = document.createElement('div');
        gridSquare.classList.add('grid-square');
        gridSquare.dataset.index = i;
        
        // Add mouseover event for drawing
        gridSquare.addEventListener('mouseover', handleSquareHover);
        
        // Also support click for single square coloring
        gridSquare.addEventListener('click', handleSquareClick);
        
        gridContainer.appendChild(gridSquare);
    }
}

/**
 * Handle mouse hover on grid square
 * @param {MouseEvent} e - The mouse event
 */
function handleSquareHover(e) {
    const square = e.target;
    applyColor(square);
}

/**
 * Handle click on grid square (for mobile/touch support)
 * @param {MouseEvent} e - The mouse event
 */
function handleSquareClick(e) {
    const square = e.target;
    applyColor(square);
}

/**
 * Apply the appropriate color to a grid square
 * @param {HTMLElement} square - The grid square element
 */
function applyColor(square) {
    if (rainbowMode) {
        square.style.backgroundColor = getRandomColor();
    } else {
        square.style.backgroundColor = '#0f172a'; // Dark slate for normal mode
    }
}

/**
 * Generate a random hex color
 * @returns {string} Random hex color string
 */
function getRandomColor() {
    const hue = Math.floor(Math.random() * 360);
    const saturation = 70 + Math.floor(Math.random() * 30); // 70-100%
    const lightness = 50 + Math.floor(Math.random() * 20);  // 50-70%
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

/**
 * Clear all grid squares back to default state
 */
function clearGrid() {
    const gridSquares = document.getElementsByClassName('grid-square');
    
    for (let i = 0; i < gridSquares.length; i++) {
        gridSquares[i].style.backgroundColor = '';
    }
    
    // Reset rainbow mode on clear
    if (rainbowMode) {
        rainbowMode = false;
        updateRainbowButtonState();
        updateModeIndicator();
    }
}

/**
 * Toggle rainbow mode on/off
 */
function toggleRainbowMode() {
    rainbowMode = !rainbowMode;
    updateRainbowButtonState();
    updateModeIndicator();
}

/**
 * Update the rainbow button visual state
 */
function updateRainbowButtonState() {
    if (rainbowMode) {
        rainbowButton.classList.add('active');
        rainbowButton.textContent = 'Normal Mode';
        // Re-add icon since textContent overwrites it
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('class', 'btn-icon');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('stroke-width', '2');
        icon.setAttribute('stroke-linecap', 'round');
        icon.setAttribute('stroke-linejoin', 'round');
        icon.innerHTML = '<circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path>';
        rainbowButton.prepend(icon);
    } else {
        rainbowButton.classList.remove('active');
        rainbowButton.textContent = 'Rainbow Mode';
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('class', 'btn-icon');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('stroke-width', '2');
        icon.setAttribute('stroke-linecap', 'round');
        icon.setAttribute('stroke-linejoin', 'round');
        icon.innerHTML = '<circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path>';
        rainbowButton.prepend(icon);
    }
}

/**
 * Update the mode indicator text
 */
function updateModeIndicator() {
    if (rainbowMode) {
        modeText.textContent = 'Rainbow';
        modeText.classList.add('rainbow');
    } else {
        modeText.textContent = 'Normal';
        modeText.classList.remove('rainbow');
    }
}

/**
 * Attach all event listeners
 */
function attachEventListeners() {
    clearButton.addEventListener('click', clearGrid);
    rainbowButton.addEventListener('click', toggleRainbowMode);
}

// Initialize the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}