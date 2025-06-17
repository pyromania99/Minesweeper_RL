import tkinter as tk
import pyautogui
import numpy as np
import cv2
from PIL import ImageGrab, Image
import time
import gui
import pytesseract
import sys

def capture_game_board():
    """Capture the game window"""
    window = pyautogui.getWindowsWithTitle("Sample Game")[0]
    window.activate()
    time.sleep(0.2)  # Wait for window to come to foreground
    
    x, y, width, height = window.left, window.top, window.width, window.height
    screenshot = ImageGrab.grab(bbox=(x, y, width+x, height+y))
    
    # Convert to numpy array for OpenCV
    screenshot_np = np.array(screenshot)
    screenshot_np = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    
    return screenshot_np, (x, y, width, height)

def detect_grid_cells(image):
    """Detect individual cells using contrast detection"""
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
    cv2.imwrite("threshold_debug.png", thresh)

    # Find contours of all cells
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours to find cells (looking for squares of similar size)
    cell_contours = []
    areas = []
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Check if it's roughly square
        aspect_ratio = float(w) / h
        if 0.8 <= aspect_ratio <= 1.2 and w > 20 and h > 20:
            areas.append(w * h)
            cell_contours.append((x, y, w, h))
    
    # If we found cells, calculate the median area to filter out non-cell contours
    if areas:
        median_area = np.median(areas)
        # Keep only contours with area close to the median (within 30%)
        cell_contours = [(x, y, w, h) for x, y, w, h in cell_contours 
                         if 0.7 * median_area <= w * h <= 1.3 * median_area]
    
    # Visualization for debugging
    debug_image = image.copy()
    for x, y, w, h in cell_contours:
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    print(f"Detected {len(cell_contours)} potential cells")
    
    return cell_contours

def organize_cells_into_grid(cell_contours):
    """Organize detected cells into a grid structure"""
    # Sort cells by y-coordinate (row) first
    cell_contours.sort(key=lambda c: c[1])
    
    # Identify rows by grouping cells with similar y-coordinates
    rows = []
    current_row = [cell_contours[0]]
    row_height = cell_contours[0][3]  # Height of first cell
    
    for cell in cell_contours[1:]:
        if abs(cell[1] - current_row[0][1]) <= row_height * 0.3:
            # This cell is in the same row
            current_row.append(cell)
        else:
            # This is a new row
            rows.append(current_row)
            current_row = [cell]
    
    # Add the last row
    if current_row:
        rows.append(current_row)
    
    # Sort each row by x-coordinate
    for i in range(len(rows)):
        rows[i].sort(key=lambda c: c[0])
    
    return rows

def analyze_cell_numbers(image, organized_cells):
    """Extract the number from each cell using color analysis instead of OCR"""
    board = []
    
    # Color ranges for different numbers (BGR format)
    color_ranges = {
        '1': {'lower': (220, 0, 0), 'upper': (255, 200, 200)},     # Blue
        '2': {'lower': (50, 150, 0), 'upper': (150, 255, 200)},     # Green
        '3': {'lower': (50, 100, 150), 'upper': (200, 200, 255)},     # Red
        '4': {'lower': (128, 0, 128), 'upper': (255, 100, 255)},   # Purple
        '5': {'lower': (0, 0, 128), 'upper': (100, 100, 180)},     # Dark Red
        '6': {'lower': (128, 128, 0), 'upper': (255, 255, 100)},   # Turquoise
        '7': {'lower': (0, 0, 0), 'upper': (50, 50, 50)},          # Black
        '8': {'lower': (100, 100, 100), 'upper': (150, 150, 150)}  # Gray
    }
    
    for row in organized_cells:
        board_row = []
        for x, y, w, h in row:
            # Extract the center region of the cell
            center_x, center_y = x + w//2, y + h//2
            cell_region = image[center_y-5:center_y+5, center_x-5:center_x+5]
            
            # Check if region is valid
            if cell_region.size == 0:
                board_row.append("?")
                continue
                
            # Calculate average color
            avg_color = np.mean(cell_region, axis=(0, 1))
            
            # Check if cell is revealed (gray background)
            if np.mean(avg_color) > 200:  # Light background = unrevealed
                board_row.append(" ")
                continue
                
            # Identify number by dominant color
            number = " "
            for digit, range_data in color_ranges.items():
                lower = np.array(range_data['lower'])
                upper = np.array(range_data['upper'])
                
                # Check if average color is in range
                if np.all(avg_color >= lower) and np.all(avg_color <= upper):
                    number = digit
                    break
                    
            board_row.append(number)
        board.append(board_row)
    
    return board

def print_board(board):
    """Print the RGB values for each cell"""
    for row in board:
        # Format each RGB tuple nicely
        formatted_row = [f"({num})" for num in row]
        print(" ".join(formatted_row))
    

def create_grid_visualization(image, organized_cells):
    """Create a detailed visualization of the detected grid with RGB values"""
    # Create a copy of the original image
    viz_image = image.copy()
    
    # Draw a more prominent grid
    for row_idx, row in enumerate(organized_cells):
        for col_idx, (x, y, w, h) in enumerate(row):
            # Draw cell boundary
            cv2.rectangle(viz_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Calculate average RGB value for this cell
            cell_region = image[y:y+h, x:x+w]
            if cell_region.size > 0:
                avg_color = np.mean(cell_region, axis=(0, 1))
                # Convert BGR to RGB for display
                avg_rgb = f"({int(avg_color[2])},{int(avg_color[1])},{int(avg_color[0])})"
            else:
                avg_rgb = "(?,?,?)"
            
            # Add row, column coordinates as text
            cv2.putText(viz_image, f"{row_idx},{col_idx}", 
                       (x + 3, y + h - 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       0.4, (255, 0, 255), 1)
            
            # Add RGB value (EASILY REMOVABLE - just delete or comment out these two lines)
            # Draw average RGB value in column format, using black for high contrast
            if avg_rgb != "(?,?,?)":
                r, g, b = avg_color[2], avg_color[1], avg_color[0]
                rgb_lines = [f"R:{int(r)}", f"G:{int(g)}", f"B:{int(b)}"]
                for i, line in enumerate(rgb_lines):
                    cv2.putText(
                        viz_image, line,
                        (x + 3, y + 15 + i * 13),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (0, 0, 0), 1, cv2.LINE_AA
                    )
            else:
                cv2.putText(
                    viz_image, avg_rgb,
                    (x + 3, y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, (0, 0, 0), 1, cv2.LINE_AA
                )
    
    # Add a title
    cv2.putText(viz_image, "Detected Minesweeper Grid", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
               1, (0, 0, 255), 2)
    
    # Save the visualization
    cv2.imwrite("grid_visualization.png", viz_image)
    return viz_image

if __name__ == "__main__":
    def wait_for_game_window():
        """Wait until the game window appears, then return it."""
        print("Waiting for 'Sample Game' window to appear...")
        while True:
            windows = pyautogui.getWindowsWithTitle("Sample Game")
            if windows:
                print("Game window detected.")
                return windows[0]
            time.sleep(1)

    prev_board_state = None
    organized_cells = None
    cell_contours = None

    print("Starting automatic board monitoring. The analysis will update after each click.")
    print("Press Ctrl+C to exit.")

    try:
        while True:
            # Wait for the game window to appear
            try:
                window = wait_for_game_window()
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                sys.exit(0)

            # Try to capture and analyze the board
            try:
                screenshot, window_info = capture_game_board()
                cell_contours = detect_grid_cells(screenshot)
                organized_cells = organize_cells_into_grid(cell_contours)
                grid_viz = create_grid_visualization(screenshot, organized_cells)
                cv2.imwrite("grid_visualization.png", grid_viz)
            except Exception as e:
                print(f"Error during initial capture: {e}")
                time.sleep(2)
                continue

            prev_board_state = None

            # Monitor the board until the window closes
            while True:
                # Check if the window still exists
                windows = pyautogui.getWindowsWithTitle("Sample Game")
                if not windows:
                    print("Game window closed. Waiting for next instance...")
                    break

                try:
                    screenshot, window_info = capture_game_board()
                    board = analyze_cell_numbers(screenshot, organized_cells)
                    board_str = '\n'.join([' '.join(row) for row in board])

                    if board_str != prev_board_state:
                        print("\nBoard updated:")
                        print_board(board)
                        prev_board_state = board_str
                except Exception as e:
                    print(f"Error during monitoring: {e}")
                    time.sleep(1)
                    continue

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
