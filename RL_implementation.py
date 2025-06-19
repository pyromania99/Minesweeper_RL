import random
import time
import sys
import os
import numpy as np
import cv2
from PIL import ImageGrab, Image
import tkinter as tk
from datetime import datetime
import pyautogui
import keyboard
# Import only the gui module - we'll implement player_view functionality inline
import gui

def run_minesweeper_bot():
    """Run a bot that plays Minesweeper by combining GUI, visual analysis and random clicking"""
    
    # Create debug directory if it doesn't exist
    debug_dir = "debug_screenshots"
    # Clean the debug directory on init
    if os.path.exists(debug_dir):
        for f in os.listdir(debug_dir):
            file_path = os.path.join(debug_dir, f)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Could not remove {file_path}: {e}")
    else:
        os.makedirs(debug_dir)
    
    # Statistics tracking
    stats = {"games": 0, "wins": 0, "losses": 0}
    scheduled_afters = []  # Track scheduled callbacks
    board_state = None  # Store the current board state
    cell_contours = None
    organized_cells = None

    def save_debug_screenshot(img, name_prefix):
        """Save a screenshot with timestamp for debugging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{debug_dir}/{name_prefix}_{stats['games']}_{timestamp}.png"
        cv2.imwrite(filename, img)
        print(f"Saved debug screenshot: {filename}")
        return filename
    
    def capture_screenshot():
        """Capture a screenshot of the game window using PyAutoGUI"""
        # Force window update and focus
        root.update_idletasks()
        root.update()
        root.focus_force()
        root.lift()
        
        # Small delay to ensure window is rendered
        time.sleep(0.1)
        
        # Get window position and dimensions
        x, y = root.winfo_rootx(), root.winfo_rooty() 
        width, height = root.winfo_width(), root.winfo_height()
        
        print(f"Window position: ({x},{y}), size: ({width}x{height})")
        
        # Verify coordinates are valid
        if width <= 10 or height <= 10 or x < 0 or y < 0:
            print(f"Invalid window dimensions")
            return None
        
        # Use PyAutoGUI to capture screenshot of the region
        try:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            # Convert PIL image to numpy array for OpenCV
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            save_debug_screenshot(screenshot, "pyautogui_screenshot")
            return screenshot
        except Exception as e:
            print(f"Error capturing screenshot with PyAutoGUI: {e}")
            return None
    
    def detect_grid_cells(image):
        """Detect individual cells using contrast detection (from player_view)"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to handle different lighting conditions
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        # Inflate the edges to make them more pronounced
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)
        save_debug_screenshot(thresh, "threshold_debug")

        # Find contours of all cells
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours to find cells (looking for squares of similar size)
        cell_contours = []
        areas = []
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter by aspect ratio (cells should be roughly square)
            aspect_ratio = float(w) / h
            if 0.5 <= aspect_ratio <= 1.2:
                # Filter by size (cells should be reasonably sized)
                if 20 <= w <= 100 and 20 <= h <= 100:
                    cell_contours.append((x, y, w, h))
                    areas.append(w * h)
        
        # If we found cells, filter by area to remove outliers
        if areas:
            # Sort areas and get median
            areas.sort()
            median_area = areas[len(areas) // 2]
            
            # Keep only cells with area close to median
            filtered_contours = []
            for contour in cell_contours:
                x, y, w, h = contour
                area = w * h
                # Accept cells within 50% of median area
                if 0.5 * median_area <= area <= 1.5 * median_area:
                    filtered_contours.append(contour)
            
            cell_contours = filtered_contours
        
        # Visualization for debugging
        debug_image = image.copy()
        for x, y, w, h in cell_contours:
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        save_debug_screenshot(debug_image, "detected_cells")
        print(f"Detected {len(cell_contours)} potential cells")
        
        return cell_contours
    
    def organize_cells_into_grid(cell_contours):
        """Organize detected cells into a grid structure (from player_view)"""
        if not cell_contours:
            return None
            
        # Sort cells by y-coordinate (row) first
        cell_contours.sort(key=lambda c: c[1])
        
        # Identify rows by grouping cells with similar y-coordinates
        rows = []
        current_row = [cell_contours[0]]
        row_height = cell_contours[0][3]  # Height of first cell
        
        for cell in cell_contours[1:]:
            # If this cell is significantly below the previous row, start a new row
            if abs(cell[1] - current_row[0][1]) > row_height * 0.5:
                rows.append(current_row)
                current_row = [cell]
            else:
                current_row.append(cell)
        
        # Add the last row
        if current_row:
            rows.append(current_row)
        
        # Sort each row by x-coordinate
        for i in range(len(rows)):
            rows[i].sort(key=lambda c: c[0])
        
        return rows

    def create_grid_visualization(image, organized_cells):
        """Create a visualization of the detected grid"""
        if organized_cells is None:
            return image.copy()
            
        # Create a copy of the original image
        viz_image = image.copy()
        
        # Draw grid with row/column numbers
        for row_idx, row in enumerate(organized_cells):
            for col_idx, cell in enumerate(row):
                if cell:
                    x, y, w, h = cell
                    # Draw rectangle
                    cv2.rectangle(viz_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    # Add row,col coordinates
                    cv2.putText(viz_image, f"{row_idx},{col_idx}", (x+5, y+h-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        return viz_image
    
    def start_new_game():
        """Start or restart a game"""
        nonlocal root, buttons, cell_contours, organized_cells

        # Cancel any pending callbacks
        for after_id in scheduled_afters:
            try:
                if root:
                    root.after_cancel(after_id)
            except:
                pass
        scheduled_afters.clear()
        
        # Clean up previous game if it exists
        if 'root' in locals() and root:
            root.destroy()
        
        # Create a new game
        root = gui.create_game()
        buttons = gui.buttons
        stats["games"] += 1
        print(f"\nStarting game #{stats['games']}...")
        
        # Ensure window is properly initialized and visible
        root.update_idletasks()
        root.update()
        root.focus_force()
        root.lift()
        
        # Add significant delay to ensure UI is fully rendered
        time.sleep(0.5)
        
        # Initialize board analysis
        try:
            # Capture screenshot
            screenshot = capture_screenshot()
            if screenshot is not None:
                save_debug_screenshot(screenshot, "initial_game")
                
                # Detect cells
                print("Detecting cells...")
                cell_contours = detect_grid_cells(screenshot)
                
                # Create a visualization of detected cells
                if cell_contours and len(cell_contours) > 0:
                    cells_viz = screenshot.copy()
                    for x, y, w, h in cell_contours:
                        cv2.rectangle(cells_viz, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    save_debug_screenshot(cells_viz, "detected_cells")
                    
                    # Try to organize cells into a grid
                    try:
                        organized_cells = organize_cells_into_grid(cell_contours)
                        
                        # Create visualization
                        grid_viz = create_grid_visualization(screenshot, organized_cells)
                        save_debug_screenshot(grid_viz, "grid_visualization")
                        
                        print(f"Successfully organized cells into a grid with {len(organized_cells)} rows")
                        for i, row in enumerate(organized_cells):
                            print(f"Row {i}: {len(row)} cells")
                    except Exception as e:
                        print(f"Error organizing cells into grid: {e}")
            
            # Schedule the bot to start playing after a delay
            after_id = root.after(100, start_playing)
            scheduled_afters.append(after_id)
                
        except Exception as e:
            print(f"Error initializing board analysis: {e}")
            # Try again after a delay if initialization fails
            after_id = root.after(100, start_playing)
            scheduled_afters.append(after_id)
        
        return root
    
    def start_playing():
        make_random_moves(20, 0.2)
        # Listen for 's' key to end the script
        if keyboard.is_pressed('s'):
            print("Detected 's' key press. Exiting script.")
            root.destroy()
            sys.exit()
    
    def click_cell_with_pyautogui(row, col):
        try:
            # Get button's position
            button = buttons[row][col]
            # Get global coordinates of button
            x = root.winfo_rootx() + button.winfo_x() + button.winfo_width() // 2
            y = root.winfo_rooty() + button.winfo_y() + button.winfo_height() // 2
            
            print(f"PyAutoGUI clicking at position ({x}, {y})")
            
            # Move mouse to position and click
            pyautogui.click(x, y)
            
            # Small delay to allow game to process the click
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error clicking with PyAutoGUI: {e}")
            return False
    
    def analyze_cell_numbers(image, organized_cells):
        """Extract the number from each cell using color analysis (like player_view)"""
        board = []
        # Color ranges for different numbers (BGR format)
        color_ranges = {
            '1': {'lower': (220, 0, 0), 'upper': (255, 100, 100)},     # Blue
            '2': {'lower': (50, 100, 0), 'upper': (150, 255, 200)},     # Green
            '3': {'lower': (50, 100, 100), 'upper': (100, 150, 255)},   # Red
            '4': {'lower': (128, 0, 128), 'upper': (255, 100, 255)},    # Purple
            '5': {'lower': (0, 0, 128), 'upper': (100, 100, 180)},      # Dark Red
            '6': {'lower': (128, 128, 0), 'upper': (255, 255, 100)},    # Turquoise
            '7': {'lower': (0, 0, 0), 'upper': (50, 50, 50)},           # Black
            '8': {'lower': (100, 100, 100), 'upper': (150, 150, 150)}   # Gray
        }
        for row in organized_cells:
            board_row = []
            for x, y, w, h in row:
                center_x, center_y = x + w//2, y + h//2
                cell_region = image[center_y-5:center_y+5, center_x-5:center_x+5]
                if cell_region.size == 0:
                    board_row.append("?")
                    continue
                avg_color = np.mean(cell_region, axis=(0, 1))
                if np.mean(avg_color) > 200:  # Light background = unrevealed
                    board_row.append(" ")
                    continue
                number = " "
                for digit, range_data in color_ranges.items():
                    lower = np.array(range_data['lower'])
                    upper = np.array(range_data['upper'])
                    # Check if any pixel in the region matches the color range
                    mask = cv2.inRange(cell_region, lower, upper)
                    if np.any(mask):
                        number = digit
                        break
                board_row.append(number)
            board.append(board_row)
        return board

    def print_board(board):
        """Print the board state in a readable format"""
        for row in board:
            print(" ".join(row))

    def make_random_moves(num_moves=20, delay=0.2):
        rows = len(buttons)
        cols = len(buttons[0])
        nonlocal board_state

        for move_num in range(num_moves):
            # Pick a random cell
            r = random.randint(0, rows-1)
            c = random.randint(0, cols-1)
            # Skip cells that are already revealed
            if buttons[r][c]['relief'] == 'sunken':
                continue

            print(f"Left clicking cell at ({r}, {c})")
            click_success = click_cell_with_pyautogui(r, c)
            if not click_success:
                print("Falling back to Tkinter invoke method")
                buttons[r][c].invoke()

            # After each move, capture and analyze the board state
            try:
                screenshot = capture_screenshot()
                if screenshot is not None and organized_cells is not None:
                    board_state = analyze_cell_numbers(screenshot, organized_cells)
                    print("Current board state:")
                    print_board(board_state)
            except Exception as e:
                print(f"Error analyzing board state: {e}")

            root.update()
            if "Win" in gui.label['text'] or "Over" in gui.label['text']:
                if "Win" in gui.label['text']:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1
                
                # Capture final state
                try:
                    final_screenshot = capture_screenshot()
                    if final_screenshot is not None:
                        save_debug_screenshot(final_screenshot, "game_end")
                except Exception as e:
                    print(f"Error capturing final state: {e}")
                
                print(f"Game ended: {gui.label['text']}")
                print(f"Stats: Games={stats['games']}, Wins={stats['wins']}, Losses={stats['losses']}")
                
                # Schedule a new game to start after a short delay
                after_id = root.after(100, start_new_game)
                scheduled_afters.append(after_id)
                return
                
            root.update()
            time.sleep(delay)
        
        # If we run out of moves but game isn't over, continue with more moves
        after_id = root.after(500, lambda: make_random_moves(20, delay))
        scheduled_afters.append(after_id)
    
    # Create the first game
    root = None
    buttons = None
    root = start_new_game()
    
    # Start the game mainloop
    root.mainloop()

if __name__ == "__main__":
    # Launch the bot with its own game instance
    run_minesweeper_bot()