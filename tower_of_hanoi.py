import time
import os

# quick helper to clear terminal so it looks like a real animation
def clear_term():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_board(pegs, total_disks):
    # ITERATION DEMO: Using loops to draw the current state of the board layer by layer
    clear_term()
    print("\n--- Tower of Hanoi ---\n")
    
    # going from top to bottom
    for level in range(total_disks - 1, -1, -1):
        row_str = ""
        for p in ['A', 'B', 'C']:
            if level < len(pegs[p]):
                disk_size = pegs[p][level]
                # build the disk string based on size
                disk = "=" * (disk_size * 2 - 1)
                row_str += disk.center(total_disks * 2)
            else:
                # empty pole
                row_str += "|".center(total_disks * 2)
        print(row_str)
        
    # draw the base
    print("-" * (total_disks * 6))
    print("A".center(total_disks * 2) + "B".center(total_disks * 2) + "C".center(total_disks * 2))
    print("\n")
    
    time.sleep(0.5) # pause so we can actually see it move

def solve_hanoi(n, source, target, aux, pegs, total_disks):
    # RECURSION DEMO: The function calls itself to break down the problem
    
    # base case: only 1 disk left to move
    if n == 1:
        disk = pegs[source].pop()
        pegs[target].append(disk)
        draw_board(pegs, total_disks)
        return

    # step 1: move n-1 disks out of the way to the aux peg
    solve_hanoi(n - 1, source, aux, target, pegs, total_disks)
    
    # step 2: move the biggest disk to the target peg
    disk = pegs[source].pop()
    pegs[target].append(disk)
    
    # print(f"Moved disk {disk} from {source} to {target}") # debug
    
    draw_board(pegs, total_disks)
    
    # step 3: move the n-1 disks from aux to target
    solve_hanoi(n - 1, aux, target, source, pegs, total_disks)


if __name__ == "__main__":
    n_disks = 4
    
    # using a dict of lists to act as stacks for the 3 pegs
    pegs_state = {
        'A': [i for i in range(n_disks, 0, -1)], # starts as [4, 3, 2, 1]
        'B': [],
        'C': []
    }
    
    # draw initial state before solving
    draw_board(pegs_state, n_disks) 
    
    # run the recursive solver
    solve_hanoi(n_disks, 'A', 'C', 'B', pegs_state, n_disks)
    
    print("Puzzle solved! \n")
