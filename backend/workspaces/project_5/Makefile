CC = gcc
CFLAGS = -Wall -Werror
TARGET = n_queens

all: $(TARGET)

$(TARGET): n_queens.c n_queens.h
	$(CC) $(CFLAGS) -o $(TARGET) n_queens.c

clean:
	rm -f $(TARGET)
