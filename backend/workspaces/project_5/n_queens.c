#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include "n_queens.h"

/* ------------------------------------------------------------ */
/*  Global Data                                                   */
/* ------------------------------------------------------------ */
int board[BOARD_SIZE][BOARD_SIZE] = {{0}};
int queens = 0;

/* ------------------------------------------------------------ */
/*  Helper Functions                                             */
/* ------------------------------------------------------------ */

/* Print the board – each row on its own line */
void print_board(int board[BOARD_SIZE][BOARD_SIZE]) {
    for (int i = 0; i < BOARD_SIZE; ++i) {
        for (int j = 0; j < BOARD_SIZE; ++j) {
            putchar(board[i][j] ? 'Q' : '.');
            if (j < BOARD_SIZE - 1) putchar(' ');
        }
        putchar('
');
    }
}

/* Check column and both diagonals for existing queens */
int is_safe(int board[BOARD_SIZE][BOARD_SIZE], int row, int col) {
    /* Column check */
    for (int i = 0; i < row; ++i) {
        if (board[i][col]) return 0;
    }
    /* Upper‑left diagonal */
    for (int i = row - 1, j = col - 1; i >= 0 && j >= 0; --i, --j) {
        if (board[i][j]) return 0;
    }
    /* Upper‑right diagonal */
    for (int i = row - 1, j = col + 1; i >= 0 && j < BOARD_SIZE; --i, ++j) {
        if (board[i][j]) return 0;
    }
    return 1;
}

/* ------------------------------------------------------------ */
/*  Core Solver                                                   */
/* ------------------------------------------------------------ */

int solve_n_queens(int board[BOARD_SIZE][BOARD_SIZE], int row) {
    if (row == queens) {
        /* All required queens placed */
        return 1;
    }
    for (int col = 0; col < BOARD_SIZE; ++col) {
        if (is_safe(board, row, col)) {
            board[row][col] = 1;
            if (solve_n_queens(board, row + 1))
                return 1;
            board[row][col] = 0; /* backtrack */
        }
    }
    return 0; /* No valid placement in this row */
}

/* ------------------------------------------------------------ */
/*  Main Entry Point                                              */
/* ------------------------------------------------------------ */

static int is_number(const char *s) {
    if (!s || *s == '\0') return 0;
    while (*s) {
        if (!isdigit((unsigned char)*s)) return 0;
        ++s;
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <number_of_queens (1‑%d)>
", argv[0], BOARD_SIZE);
        return EXIT_FAILURE;
    }
    if (!is_number(argv[1])) {
        fprintf(stderr, "Error: argument must be a positive integer.
");
        return EXIT_FAILURE;
    }
    int n = atoi(argv[1]);
    if (n < 1 || n > BOARD_SIZE) {
        fprintf(stderr, "Error: number of queens must be between 1 and %d.
", BOARD_SIZE);
        return EXIT_FAILURE;
    }
    queens = n;

    if (solve_n_queens(board, 0)) {
        print_board(board);
    } else {
        printf("No solution exists for %d queens on a %dx%d board.
", queens, BOARD_SIZE, BOARD_SIZE);
    }
    return EXIT_SUCCESS;
}
