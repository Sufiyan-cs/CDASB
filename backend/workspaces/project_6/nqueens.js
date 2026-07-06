/**
 * N-Queens Solver
 * Uses backtracking algorithm to find a valid placement of N queens
 * on an N×N chessboard where no two queens threaten each other.
 */

function solveNQueens(n) {
    // Validate input
    if (!Number.isInteger(n) || n < 1) {
        return null;
    }
    
    // Edge case: no solution for n = 2 or n = 3
    if (n === 2 || n === 3) {
        return null;
    }
    
    // Edge case: single queen
    if (n === 1) {
        return [[1]];
    }
    
    // Initialize empty board
    const board = Array(n).fill(0).map(() => Array(n).fill(0));
    const solutions = [];
    
    /**
     * Check if placing a queen at (row, col) is safe
     * Only need to check above since we place row by row
     */
    function isSafe(row, col) {
        // Check column
        for (let i = 0; i < row; i++) {
            if (board[i][col] === 1) {
                return false;
            }
        }
        
        // Check upper-left diagonal
        for (let i = row - 1, j = col - 1; i >= 0 && j >= 0; i--, j--) {
            if (board[i][j] === 1) {
                return false;
            }
        }
        
        // Check upper-right diagonal
        for (let i = row - 1, j = col + 1; i >= 0 && j < n; i--, j++) {
            if (board[i][j] === 1) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Recursive backtracking solver
     */
    function solve(row) {
        // Base case: all queens placed successfully
        if (row === n) {
            // Deep copy the board to store solution
            solutions.push(board.map(r => r.slice()));
            return;
        }
        
        // Try placing queen in each column of current row
        for (let col = 0; col < n; col++) {
            if (isSafe(row, col)) {
                // Place queen
                board[row][col] = 1;
                
                // Recursively solve for next row
                solve(row + 1);
                
                // Backtrack: remove queen
                board[row][col] = 0;
            }
        }
    }
    
    // Start solving from first row
    solve(0);
    
    // Return first solution found, or null if no solution exists
    return solutions.length > 0 ? solutions[0] : null;
}

export { solveNQueens };