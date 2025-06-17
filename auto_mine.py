import random
import time
import sys

def run_minesweeper_bot():
    """Run a bot that directly controls the Minesweeper game"""
    # Import the game module but don't run it yet
    import gui
    
    # Statistics tracking
    stats = {"games": 0, "wins": 0, "losses": 0}
    
    def start_new_game():
        """Start or restart a game"""
        nonlocal root, buttons
        
        # Clean up previous game if it exists
        if 'root' in locals() and root:
            root.destroy()
            
        # Create a new game
        root = gui.create_game()
        buttons = gui.buttons
        stats["games"] += 1
        print(f"\nStarting game #{stats['games']}...")
        
        # Schedule the bot to start playing after a delay
        root.after(500, lambda: make_random_moves(50, 0.01))
        return root
    
    def make_random_moves(num_moves=50, delay=0.01):
        rows = len(buttons)
        cols = len(buttons[0])
        
        for _ in range(num_moves):
            # Pick a random cell
            r = random.randint(0, rows-1)
            c = random.randint(0, cols-1)
            
            # Skip cells that are already revealed
            if buttons[r][c]['relief'] == 'sunken':
                continue

            print(f"Left clicking cell at ({r}, {c})")
            buttons[r][c].invoke()  # Simulate left click
           
            # Check if game is over
            if "Win" in gui.label['text'] or "Over" in gui.label['text']:
                if "Win" in gui.label['text']:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1
                
                print(f"Game ended: {gui.label['text']}")
                print(f"Stats: Games={stats['games']}, Wins={stats['wins']}, Losses={stats['losses']}")
                
                # Schedule a new game to start after a short delay
                root.after(100, start_new_game)
                return
                
            # Process UI updates and add delay
            root.update()
            time.sleep(delay)
        
        # If we run out of moves but game isn't over, continue with more moves
        root.after(500, lambda: make_random_moves(50, delay))
    
    # Create the first game
    root = None
    buttons = None
    root = start_new_game()
    
    # Start the game mainloop
    root.mainloop()

if __name__ == "__main__":
    # Launch the bot with its own game instance
    run_minesweeper_bot()