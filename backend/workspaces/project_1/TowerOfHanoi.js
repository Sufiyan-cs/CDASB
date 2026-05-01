// TowerOfHanoi.js - Tower of Hanoi game logic module

/**
 * Tower of Hanoi Game Logic
 * A module that handles the core game logic for the Tower of Hanoi puzzle
 */
class TowerOfHanoi {
    constructor(numDisks = 5) {
        this.numDisks = numDisks;
        this.towers = this.initializeTowers();
        this.moveCount = 0;
        this.minMoves = Math.pow(2, numDisks) - 1;
    }

    /**
     * Initializes the towers with disks in the correct order
     * @returns {Array<Array<number>>} Array of three towers
     */
    initializeTowers() {
        const disks = [];
        for (let i = this.numDisks; i >= 1; i--) {
            disks.push(i);
        }
        return [disks, [], []];
    }

    /**
     * Resets the game to its initial state
     */
    reset() {
        this.towers = this.initializeTowers();
        this.moveCount = 0;
    }

    /**
     * Checks if a move is valid
     * @param {number} fromTower - Source tower index (0, 1, or 2)
     * @param {number} toTower - Target tower index (0, 1, or 2)
     * @returns {boolean} True if the move is valid
     */
    isValidMove(fromTower, toTower) {
        if (fromTower < 0 || fromTower > 2 || toTower < 0 || toTower > 2) {
            return false;
        }

        if (fromTower === toTower) {
            return false;
        }

        if (this.towers[fromTower].length === 0) {
            return false;
        }

        const sourceDisk = this.towers[fromTower][this.towers[fromTower].length - 1];
        const targetDisk = this.towers[toTower].length > 0 
            ? this.towers[toTower][this.towers[toTower].length - 1] 
            : Infinity;

        return sourceDisk < targetDisk;
    }

    /**
     * Moves a disk from one tower to another
     * @param {number} fromTower - Source tower index (0, 1, or 2)
     * @param {number} toTower - Target tower index (0, 1, or 2)
     * @returns {boolean} True if the move was successful
     */
    moveDisk(fromTower, toTower) {
        if (!this.isValidMove(fromTower, toTower)) {
            return false;
        }

        const disk = this.towers[fromTower].pop();
        this.towers[toTower].push(disk);
        this.moveCount++;
        
        return true;
    }

    /**
     * Checks if the puzzle is solved (all disks on the last tower)
     * @returns {boolean} True if the puzzle is solved
     */
    isSolved() {
        return this.towers[2].length === this.numDisks;
    }

    /**
     * Gets the current state of a tower
     * @param {number} towerIndex - Tower index (0, 1, or 2)
     * @returns {Array<number>} Array of disk sizes on the tower
     */
    getTower(towerIndex) {
        return [...this.towers[towerIndex]];
    }

    /**
     * Gets the top disk of a tower
     * @param {number} towerIndex - Tower index (0, 1, or 2)
     * @returns {number|null} The size of the top disk, or null if tower is empty
     */
    getTopDisk(towerIndex) {
        const tower = this.towers[towerIndex];
        return tower.length > 0 ? tower[tower.length - 1] : null;
    }

    /**
     * Gets the current move count
     * @returns {number} Number of moves made
     */
    getMoveCount() {
        return this.moveCount;
    }

    /**
     * Gets the minimum number of moves required to solve
     * @returns {number} Minimum moves
     */
    getMinMoves() {
        return this.minMoves;
    }

    /**
     * Checks if the current solution is optimal
     * @returns {boolean} True if using minimum moves
     */
    isOptimal() {
        return this.moveCount === this.minMoves;
    }

    /**
     * Gets a string representation of the current game state
     * @returns {string} Game state as a string
     */
    toString() {
        return this.towers.map((tower, index) => {
            return `Tower ${index + 1}: [${tower.join(', ') || 'empty'}]`;
        }).join('\n');
    }

    /**
     * Solves the puzzle automatically using the recursive algorithm
     * @param {number} n - Number of disks
     * @param {number} from - Source tower
     * @param {number} to - Target tower
     * @param {number} via - Auxiliary tower
     * @returns {Array<{from: number, to: number}>} Array of moves
     */
    static solve(n, from = 0, to = 2, via = 1) {
        const moves = [];
        
        function hanoi(n, from, to, via) {
            if (n === 0) return;
            
            hanoi(n - 1, from, via, to);
            moves.push({ from, to });
            hanoi(n - 1, via, to, from);
        }
        
        hanoi(n, from, to, via);
        return moves;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TowerOfHanoi;
}