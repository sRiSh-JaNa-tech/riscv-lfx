import time
import os

def clear_screen():
    """Clears the terminal for simple animation."""
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_pegs(state, num_disks):
    """
    == ITERATION DEMONSTRATION ==
    This function uses loops (iteration) to traverse the current 
    state of the pegs and draw them layer by layer in the console.
    """
    clear_screen()
    print("\n--- Tower of Hanoi ---\n")
    
    # Iterate from the top layer down to the bottom
    for level in range(num_disks - 1, -1, -1):
        row_visual = ""
        for peg in ['A', 'B', 'C']:
            if level < len(state[peg]):
                disk_size = state[peg][level]
                # Draw the disk based on its size
                disk_str = "█" * (disk_size * 2 - 1)
                row_visual += disk_str.center(num_disks * 2)
            else:
                # Draw the empty peg pole
                row_visual += "|".center(num_disks * 2)
        print(row_visual)
        
    # Draw the base
    print("=" * (num_disks * 6))
    print("A".center(num_disks * 2) + "B".center(num_disks * 2) + "C".center(num_disks * 2))
    print("\n")
    time.sleep(0.6) # Pause for animation effect

def move_disks(n, source, target, auxiliary, state, num_disks):
    """
    == RECURSION DEMONSTRATION ==
    This function calls itself to solve smaller sub-problems.
    It moves (n-1) disks out of the way, moves the largest disk, 
    and then moves the (n-1) disks onto the target peg.
    """
    # Base Case for Recursion: Only 1 disk to move
    if n == 1:
        disk = state[source].pop()
        state[target].append(disk)
        draw_pegs(state, num_disks)
        return

    # Recursive Step 1: Move n-1 disks from source to auxiliary peg
    move_disks(n - 1, source, auxiliary, target, state, num_disks)
    
    # Move the largest remaining disk to the target peg
    disk = state[source].pop()
    state[target].append(disk)
    draw_pegs(state, num_disks)
    
    # Recursive Step 2: Move the n-1 disks from auxiliary peg to target peg
    move_disks(n - 1, auxiliary, target, source, state, num_disks)

if __name__ == "__main__":
    NUM_DISKS = 4
    
    # Dictionary representing the 3 pegs as stacks (lists)
    state = {
        'A': [i for i in range(NUM_DISKS, 0, -1)], # Starts as [4, 3, 2, 1]
        'B': [],
        'C': []
    }
    
    # Initial draw before starting
    draw_pegs(state, NUM_DISKS)
    
    # Start the recursive solver
    move_disks(NUM_DISKS, 'A', 'C', 'B', state, NUM_DISKS)
    
    print("Puzzle Solved successfully!\n")