#ifndef N_QUEENS_H
#define N_QUEENS_H

/* ------------------------------------------------------------ */
/*  Constants & Global Variables                                   */
/* ------------------------------------------------------------ */
#define BOARD_SIZE 8

/* Global board and queen count – fixed size as required */
extern int board[BOARD_SIZE][BOARD_SIZE];
extern int queens;

/* ------------------------------------------------------------ */
/*  Function Prototypes                                            */
/* ------------------------------------------------------------ */

/* Print the board using 'Q' for queens and '.' for empty cells */
void print_board(int board[BOARD_SIZE][BOARD_SIZE]);

/* Return 1 if a queen can be safely placed at (row, col) */
int is_safe(int board[BOARD_SIZE][BOARD_SIZE], int row, int col);

/* Recursive back‑tracking solver – tries to place all queens */
int solve_n_queens(int board[BOARD_SIZE][BOARD_SIZE], int row);

#endif /* N_QUEENS_H */