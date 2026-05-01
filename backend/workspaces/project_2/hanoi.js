/**
 * Hanoi Module
 * Contains the core logic and rules for the Tower of Hanoi game.
 */
const Hanoi = (() => {
    const NUM_DISKS = 5;
    
    // State
    let rods = [[], [], []];
    let moves = 0;

    // Initialize game state
    const init = () => {
        rods = [[], [], []];
        moves = 0;
        // Create disks (largest at bottom, so we push in reverse order or unshift)
        // Let's create array [5, 4, 3, 2, 1] for Rod 1
        for (let i = NUM_DISKS; i >= 1; i--) {
            rods[0].push(i);
        }
        return getState();
    };

    // Get current state snapshot
    const getState = () => ({
        rods: JSON.parse(JSON.stringify(rods)),
        moves: moves
    });

    // Validate and execute move
    const moveDisk = (fromRodIndex, toRodIndex) => {
        const fromRod = rods[fromRodIndex];
        const toRod = rods[toRodIndex];

        if (fromRod.length === 0) {
            return { success: false, message: "Source rod is empty" };
        }

        const diskToMove = fromRod[fromRod.length - 1];
        const topDiskOnTarget = toRod.length > 0 ? toRod[toRod.length - 1] : null;

        if (topDiskOnTarget && diskToMove > topDiskOnTarget) {
            return { success: false, message: "Invalid move: Cannot place larger disk on smaller one" };
        }

        // Execute move
        fromRod.pop();
        toRod.push(diskToMove);
        moves++;

        return { success: true, message: "Move successful" };
    };

    // Check win condition
    const checkWin = () => {
        // Win if all disks are on the last rod (index 2)
        return rods[2].length === NUM_DISKS;
    };

    return {
        init,
        getState,
        moveDisk,
        checkWin
    };
})();