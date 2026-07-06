import { solveNQueens } from './nqueens.js';

// DOM Elements
const boardContainer = document.getElementById('board');
const boardOverlay = document.getElementById('board-overlay');
const nInput = document.getElementById('n');
const solveBtn = document.getElementById('solve-btn');

// Queen SVG icon (crown)
const queenSvg = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/></svg>`;

// Toast notification system
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Trigger reflow
    toast.offsetHeight;
    
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Validate input
function validateInput(value) {
    const n = parseInt(value);
    
    if (isNaN(n)) {
        return { valid: false, message: 'Please enter a valid number' };
    }
    
    if (n < 4) {
        return { valid: false, message: 'Board size must be at least 4' };
    }
    
    if (n > 12) {
        return { valid: false, message: 'Board size must be at most 12' };
    }
    
    return { valid: true, n };
}

// Render the chess board
function renderBoard(solution, n) {
    // Clear existing board
    boardContainer.innerHTML = '';
    
    // Update grid columns
    boardContainer.style.gridTemplateColumns = `repeat(${n}, 1fr)`;
    
    // Hide overlay
    boardOverlay.classList.add('hidden');
    
    // Create cells with staggered animation
    for (let row = 0; row < n; row++) {
        for (let col = 0; col < n; col++) {
            const cell = document.createElement('div');
            const isDark = (row + col) % 2 === 1;
            
            cell.classList.add('cell', isDark ? 'dark' : 'light');
            cell.style.opacity = '0';
            cell.style.transform = 'scale(0.8)';
            cell.style.animation = `none`;
            
            // Check if queen should be placed
            const hasQueen = solution && solution[row] && solution[row][col] === 1;
            
            if (hasQueen) {
                cell.classList.add('queen-cell');
                const queenSpan = document.createElement('span');
                queenSpan.classList.add('queen');
                queenSpan.innerHTML = queenSvg;
                // Color the queen based on cell color for contrast
                const queenColor = isDark ? '#f1f5f9' : '#1a1a2e';
                queenSpan.querySelector('svg').style.color = queenColor;
                cell.appendChild(queenSpan);
            }
            
            boardContainer.appendChild(cell);
            
            // Staggered fade-in
            const delay = (row * n + col) * 15;
            setTimeout(() => {
                cell.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
                cell.style.opacity = '1';
                cell.style.transform = 'scale(1)';
            }, delay);
        }
    }
}

// Show empty state
function showEmptyState() {
    boardContainer.innerHTML = '';
    boardContainer.style.gridTemplateColumns = 'repeat(8, 1fr)';
    boardOverlay.classList.remove('hidden');
}

// Handle solve button click
async function handleSolve() {
    const validation = validateInput(nInput.value);
    
    if (!validation.valid) {
        nInput.classList.add('input-error');
        showToast(validation.message, 'error');
        
        setTimeout(() => {
            nInput.classList.remove('input-error');
        }, 500);
        
        return;
    }
    
    const n = validation.n;
    
    // Show loading state
    solveBtn.classList.add('loading');
    solveBtn.querySelector('span').textContent = 'Solving...';
    
    // Small delay to show loading state
    await new Promise(resolve => setTimeout(resolve, 100));
    
    try {
        const solution = solveNQueens(n);
        
        if (!solution) {
            showToast('No solution found', 'error');
            showEmptyState();
            return;
        }
        
        renderBoard(solution, n);
        showToast(`Solution found for ${n}×${n} board!`, 'success');
        
    } catch (error) {
        console.error('Error solving N-Queens:', error);
        showToast('An error occurred while solving', 'error');
        showEmptyState();
    } finally {
        solveBtn.classList.remove('loading');
        solveBtn.querySelector('span').textContent = 'Solve';
    }
}

// Event Listeners
solveBtn.addEventListener('click', handleSolve);

nInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        handleSolve();
    }
});

nInput.addEventListener('input', () => {
    nInput.classList.remove('input-error');
});

// Initialize with empty state
showEmptyState();

// Add keyframes for cell animation dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes cell-appear {
        0% { opacity: 0; transform: scale(0.8); }
        100% { opacity: 1; transform: scale(1); }
    }
`;
document.head.appendChild(style);