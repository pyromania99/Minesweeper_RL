import tkinter as tk
import random

# Global variables
rows, cols = 10, 10
buttons = []
revealed_cells = 0
bomb_locations = set()
root = None
label = None
num_bombs = 15

def show_all_bombs():
    for r, c in bomb_locations:
        buttons[r][c].config(text="💣")

def on_right_click(event, r, c):
    if buttons[r][c]['relief'] != tk.SUNKEN and buttons[r][c]['text'] not in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        if buttons[r][c]['text'] == "🚩":
            buttons[r][c].config(text="", bg="SystemButtonFace")
        else:
            buttons[r][c].config(text="🚩", bg="yellow")
    return "break"  # Prevents the default right-click context menu from appearing in some Tkinter environments

def on_click(r, c):
    global revealed_cells
    if buttons[r][c]['text'] == "🚩":
        return

    if (r, c) in bomb_locations:
        buttons[r][c].config(text="💣")
        label.config(text="Game Over!")
        show_all_bombs()
        # Disable all buttons
        for row in buttons:
            for btn in row:
                btn.config(state=tk.DISABLED)
    else:
        revealed_cells += 1
        # Count bombs in adjacent cells
        count = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) in bomb_locations:
                    count += 1
        color_map = {
            1: "blue",
            2: "green",
            3: "red",
            4: "purple",
            5: "maroon",
            6: "turquoise",
            7: "black",
            8: "gray"
        }
        if count > 0:
            buttons[r][c].config(
                text=str(count),
                fg=color_map.get(count, "black"),
                font=("Arial", 14, "bold"),
                width=2,  # Fixed width to prevent resizing
                height=1  # Fixed height to prevent resizing
            )
        else:
            buttons[r][c].config(text="")
        if count == 0:
            buttons[r][c].config(relief=tk.SUNKEN, bg="#d3d3d3")
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if buttons[nr][nc]['text'] == "" and buttons[nr][nc]['relief'] != tk.SUNKEN:
                            on_click(nr, nc)
    if revealed_cells == (rows * cols) - num_bombs:
        label.config(text="You Win!")
        show_all_bombs()
        # Disable all buttons
        for row in buttons:
            for btn in row:
                btn.config(state=tk.DISABLED)    

def create_game():
    global root, buttons, revealed_cells, label, bomb_locations
    
    root = tk.Tk()
    root.title("Sample Game")
    
    buttons = []
    revealed_cells = 0
    frame = tk.Frame(root)
    frame.pack()
    
    # Create buttons
    for r in range(rows):
        row = []
        for c in range(cols):
            btn = tk.Button(frame, width=4, height=2, command=lambda r=r, c=c: on_click(r, c))
            btn.grid(row=r+1, column=c)  # Shift all buttons down by 1 row
            btn.bind("<Button-3>", lambda event, r=r, c=c: on_right_click(event, r, c))
            row.append(btn)
        buttons.append(row)
    
    label = tk.Label(root, text="Welcome to Minesweeper!")
    label.pack()
    
    # Place bombs
    bomb_locations = set()
    while len(bomb_locations) < num_bombs:
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        bomb_locations.add((r, c))
    
    return root

# Only create the game when run directly
if __name__ == "__main__":
    game = create_game()
    game.mainloop()
