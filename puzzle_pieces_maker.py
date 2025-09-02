import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QPushButton, QFileDialog, QLabel, QSpinBox,
                            QDialog, QDialogButtonBox, QFormLayout, QMessageBox,
                            QScrollArea, QSlider, QFrame)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint, QSize


class GridDimensionsDialog(QDialog):
    def __init__(self, parent=None, current_x=10, current_y=10):
        super().__init__(parent)
        self.setWindowTitle("Grid Dimensions")
        self.setModal(True)
        self.resize(300, 150)

        layout = QFormLayout()

        self.x_spinbox = QSpinBox()
        self.x_spinbox.setMinimum(1)
        self.x_spinbox.setMaximum(100)
        self.x_spinbox.setValue(current_x)

        self.y_spinbox = QSpinBox()
        self.y_spinbox.setMinimum(1)
        self.y_spinbox.setMaximum(100)
        self.y_spinbox.setValue(current_y)

        layout.addRow("X Squares (Width):", self.x_spinbox)
        layout.addRow("Y Squares (Height):", self.y_spinbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def get_dimensions(self):
        return self.x_spinbox.value(), self.y_spinbox.value()


class ImageGridWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.original_pixmap = None
        self.grid_x_max = 0
        self.grid_y_max = 0
        self.zoom_factor = 1.0
        self.crop_mode = False
        self.drag_handles = []
        self.padding = 10  # Add 10 pixel padding around the image
        self.grid_points = []  # 2D array to store grid point locations
        self.drag_grid_points = []  # Copy of grid points when dragging begins
        self.is_dragging = False  # Flag to track if we're currently dragging
        self.dragging_handle = None  # Reference to the handle being dragged
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid gray;")
        self.setMinimumSize(400, 300)
        # Enable focus so we can receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

    def set_image_and_grid(self, pixmap, grid_x_max, grid_y_max):
        self.original_pixmap = pixmap
        self.grid_x_max = grid_x_max
        self.grid_y_max = grid_y_max
        self.zoom_factor = 1.0  # Reset zoom when new image is loaded
        self.calculate_grid_points()  # Calculate grid points BEFORE update_display
        self.update_display()

    def set_zoom(self, zoom_factor):
        self.zoom_factor = zoom_factor
        self.update_display()  # Grid points don't need recalculating for zoom changes

    def update_display(self):
        if not self.original_pixmap:
            return

        # Calculate the size based on zoom factor
        original_size = self.original_pixmap.size()
        zoomed_size = original_size * self.zoom_factor
        
        # Scale pixmap with zoom factor
        scaled_pixmap = self.original_pixmap.scaled(
            zoomed_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # Draw grid on the scaled pixmap
        gridded_pixmap = self.draw_grid(scaled_pixmap)

        # Create a larger pixmap with padding
        padded_size = QSize(gridded_pixmap.width() + 2 * self.padding,
                           gridded_pixmap.height() + 2 * self.padding)
        padded_pixmap = QPixmap(padded_size)
        padded_pixmap.fill(Qt.lightGray)  # Fill padding area with light gray

        # Draw the image centered in the padded pixmap
        painter = QPainter(padded_pixmap)
        painter.drawPixmap(self.padding, self.padding, gridded_pixmap)
        painter.end()

        self.setPixmap(padded_pixmap)

        # Adjust widget size to match the padded pixmap
        self.resize(padded_pixmap.size())

    def get_image_rect(self):
        """Get the rectangle where the actual image is drawn (excluding padding)"""
        if not self.original_pixmap:
            return QRect()

        # Calculate the scaled image size
        original_size = self.original_pixmap.size()
        zoomed_size = original_size * self.zoom_factor

        # Return the rectangle where the image is positioned (with padding offset)
        return QRect(self.padding, self.padding, zoomed_size.width(), zoomed_size.height())

    def draw_grid_lines(self, painter, grid_points_to_use, scale_x, scale_y, pen=None):
        """Shared function to draw grid lines using specified grid points and scaling"""
        if pen:
            painter.setPen(pen)

        # Draw vertical line segments using grid points
        for col in range(self.grid_x_max + 1):
            # Draw segments between consecutive points in this column
            for row in range(self.grid_y_max):
                # Get start point (current row)
                start_x = int(grid_points_to_use[row][col][0] * scale_x)
                start_y = int(grid_points_to_use[row][col][1] * scale_y)

                # Get end point (next row)
                end_x = int(grid_points_to_use[row + 1][col][0] * scale_x)
                end_y = int(grid_points_to_use[row + 1][col][1] * scale_y)

                # Draw line segment between these two points
                painter.drawLine(start_x, start_y, end_x, end_y)

        # Draw horizontal line segments using grid points
        for row in range(self.grid_y_max + 1):
            # Draw segments between consecutive points in this row
            for col in range(self.grid_x_max):
                # Get start point (current column)
                start_x = int(grid_points_to_use[row][col][0] * scale_x)
                start_y = int(grid_points_to_use[row][col][1] * scale_y)

                # Get end point (next column)
                end_x = int(grid_points_to_use[row][col + 1][0] * scale_x)
                end_y = int(grid_points_to_use[row][col + 1][1] * scale_y)

                # Draw line segment between these two points
                painter.drawLine(start_x, start_y, end_x, end_y)

    def draw_grid(self, pixmap):
        # Create a copy to draw on
        result_pixmap = pixmap.copy()
        painter = QPainter(result_pixmap)

        # Set up pen for grid lines
        pen = QPen(Qt.red, 2)
        painter.setPen(pen)

        width = result_pixmap.width()
        height = result_pixmap.height()

        # Only draw grid if we have grid points
        if not self.grid_points or self.grid_x_max == 0 or self.grid_y_max == 0:
            painter.end()
            return result_pixmap

        # Calculate scaling factor from original image to current pixmap
        original_size = self.original_pixmap.size()
        scale_x = width / original_size.width()
        scale_y = height / original_size.height()

        # Use shared drawing function
        self.draw_grid_lines(painter, self.grid_points, scale_x, scale_y, pen)

        painter.end()
        return result_pixmap

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update_display()

    def set_crop_mode(self, enabled):
        """Enable or disable crop mode"""
        self.crop_mode = enabled
        if enabled:
            self.create_drag_handles()
        else:
            self.drag_handles = []
        self.update_display()

    def set_drag_endpoints_mode(self, enabled):
        """Enable or disable drag endpoints mode"""
        # For now, this is a placeholder implementation
        # In the future, this could enable dragging of all grid intersection points
        # rather than just the perimeter points like crop mode does
        if enabled:
            # TODO: Implement drag endpoints functionality
            # This would create drag handles for ALL grid intersection points,
            # not just the perimeter ones
            print("Drag endpoints mode enabled - functionality to be implemented")
        else:
            print("Drag endpoints mode disabled")

        # For now, just update the display
        self.update_display()

    def create_drag_handles(self):
        """Create drag handles at all grid perimeter points"""
        self.drag_handles = []
        if not self.original_pixmap or self.grid_x_max == 0 or self.grid_y_max == 0 or not self.grid_points:
            return

        # Create handles for all perimeter points of the grid
        # Store (scaled_point, row, col) tuples to avoid duplicate lookups
        perimeter_points = set()  # Use set to avoid duplicate points at corners

        # Top edge: all points in row 0
        for col in range(self.grid_x_max + 1):
            scaled_point = self.get_scaled_grid_point(0, col)
            if scaled_point:
                perimeter_points.add((scaled_point, 0, col))

        # Bottom edge: all points in last row
        for col in range(self.grid_x_max + 1):
            scaled_point = self.get_scaled_grid_point(self.grid_y_max, col)
            if scaled_point:
                perimeter_points.add((scaled_point, self.grid_y_max, col))

        # Left edge: all points in column 0 (excluding corners already added)
        for row in range(1, self.grid_y_max):
            scaled_point = self.get_scaled_grid_point(row, 0)
            if scaled_point:
                perimeter_points.add((scaled_point, row, 0))

        # Right edge: all points in last column (excluding corners already added)
        for row in range(1, self.grid_y_max):
            scaled_point = self.get_scaled_grid_point(row, self.grid_x_max)
            if scaled_point:
                perimeter_points.add((scaled_point, row, self.grid_x_max))

        # Convert set to list of drag handles with edge flags
        for scaled_point, point_row, point_col in perimeter_points:
            x, y = scaled_point

            # Set edge flags based on stored indices
            is_left = point_col == 0
            is_right = point_col == self.grid_x_max
            is_top = point_row == 0
            is_bottom = point_row == self.grid_y_max

            self.drag_handles.append({
                'pos': QPoint(int(x), int(y)),
                'left': is_left,
                'right': is_right,
                'top': is_top,
                'bottom': is_bottom,
                'row': point_row,
                'col': point_col
            })

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap() or not self.crop_mode or not self.drag_handles:
            return

        # Check grid validity before creating painter
        if not self.grid_points or self.grid_x_max == 0 or self.grid_y_max == 0:
            return

        painter = QPainter(self)

        # Check if we're currently dragging and have a copy of the original grid
        is_dragging = any(handle.get('dragging', False) for handle in self.drag_handles)

        if is_dragging and self.drag_grid_points:
            # Draw the full grid using the original grid points copy
            pen = QPen(Qt.green, 1, Qt.SolidLine)  # Use green solid line for original grid
            painter.setPen(pen)

            # Calculate scaling factor from original image to current display
            original_size = self.original_pixmap.size()
            scale_x = self.zoom_factor
            scale_y = self.zoom_factor

            # Use shared drawing function with the copied grid points
            # Offset the drawing by padding amount
            painter.translate(self.padding, self.padding)
            self.draw_grid_lines(painter, self.drag_grid_points, scale_x, scale_y, pen)
            painter.translate(-self.padding, -self.padding)  # Reset translation

        # Draw the current perimeter (crop boundary) with blue dashed lines
        pen = QPen(Qt.blue, 2, Qt.DashLine)
        painter.setPen(pen)

        # Draw line segments between adjacent perimeter points
        # Draw top edge: connect all points in row 0
        for col in range(self.grid_x_max):
            start_point = self.get_scaled_grid_point(0, col)
            end_point = self.get_scaled_grid_point(0, col + 1)
            if start_point and end_point:
                painter.drawLine(start_point[0], start_point[1], end_point[0], end_point[1])

        # Draw bottom edge: connect all points in last row
        for col in range(self.grid_x_max):
            start_point = self.get_scaled_grid_point(self.grid_y_max, col)
            end_point = self.get_scaled_grid_point(self.grid_y_max, col + 1)
            if start_point and end_point:
                painter.drawLine(start_point[0], start_point[1], end_point[0], end_point[1])

        # Draw left edge: connect all points in column 0
        for row in range(self.grid_y_max):
            start_point = self.get_scaled_grid_point(row, 0)
            end_point = self.get_scaled_grid_point(row + 1, 0)
            if start_point and end_point:
                painter.drawLine(start_point[0], start_point[1], end_point[0], end_point[1])

        # Draw right edge: connect all points in last column
        for row in range(self.grid_y_max):
            start_point = self.get_scaled_grid_point(row, self.grid_x_max)
            end_point = self.get_scaled_grid_point(row + 1, self.grid_x_max)
            if start_point and end_point:
                painter.drawLine(start_point[0], start_point[1], end_point[0], end_point[1])

        # Draw drag handles
        """
        if self.drag_handles:
            print("Drawing drag handles, top-left handle at:", self.drag_handles[0]['pos'])  # Debug output
        """
        for handle in self.drag_handles:
            self.draw_drag_handle(painter, handle)

    def draw_drag_handle(self, painter, handle):
        """Draw a single drag handle"""
        size = 8
        rect = QRect(handle['pos'] - QPoint(size // 2, size // 2), QSize(size, size))
        painter.drawRect(rect)

    def update_drag_handle_positions(self):
        for handle in self.drag_handles:
            if not handle.get('updated', True):
                x, y = self.get_scaled_grid_point(handle['row'], handle['col'], self.drag_grid_points)
                old_y = handle['pos'].y()
                handle['pos'] = QPoint(int(x), int(y))
                new_y = handle['pos'].y()
            handle['updated'] = False  # Reset for next update
        """
        print("update drag handles, top-left handle at:", self.drag_handles[0]['pos'])  # Debug output\
        print("Top-left grid point:", self.get_grid_point(0, 0, self.drag_grid_points))  # Debug output
        print("Top-left rgrid point:", self.drag_grid_points[0][0])  # Debug output
        """

    def get_old_x_values_to_the_right(self, handle_row, drag_col, end_col):
        left_old, _col = self.drag_grid_points[handle_row][drag_col]
        right_old, _col = self.drag_grid_points[handle_row][end_col]
        width_old = right_old - left_old
        preserve_values = []
        for col in range(drag_col + 1, end_col):
            old_x, old_y = self.drag_grid_points[handle_row][col]
            relative_pos = (old_x - left_old) / width_old
            preserve_values.append(relative_pos)

        return (handle_row, drag_col, end_col, left_old, right_old, width_old, preserve_values)

    def get_old_x_values_to_the_left(self, handle_row, start_col, drag_col):
        left_old, _col = self.drag_grid_points[handle_row][start_col]
        right_old, _col = self.drag_grid_points[handle_row][drag_col]
        width_old = right_old - left_old
        preserve_values = []
        for col in range(start_col + 1, drag_col):
            old_x, old_y = self.drag_grid_points[handle_row][col]
            relative_pos = (old_x - right_old) / width_old
            preserve_values.append(relative_pos)
        return (handle_row, start_col, drag_col, left_old, right_old, width_old, preserve_values)

    def get_old_y_values_to_the_bottom(self, handle_col, drag_row, end_row):
        _row, top_old = self.drag_grid_points[drag_row][handle_col]
        _row, bottom_old = self.drag_grid_points[end_row][handle_col]
        height_old = bottom_old - top_old
        preserve_values = []
        for row in range(drag_row + 1, end_row):
            old_x, old_y = self.drag_grid_points[row][handle_col]
            relative_pos = (old_y - top_old) / height_old
            preserve_values.append(relative_pos)
        return (handle_col, drag_row, end_row, top_old, bottom_old, height_old, preserve_values)

    def get_old_y_values_to_the_top(self, handle_col, start_row, drag_row):
        _row, top_old = self.drag_grid_points[start_row][handle_col]
        _row, bottom_old = self.drag_grid_points[drag_row][handle_col]
        height_old = bottom_old - top_old
        preserve_values = []
        for row in range(start_row + 1, drag_row):
            old_x, old_y = self.drag_grid_points[row][handle_col]
            relative_pos = (old_y - bottom_old) / height_old
            preserve_values.append(relative_pos)
        return (handle_col, start_row, drag_row, top_old, bottom_old, height_old, preserve_values)

    def preserve_x_spacing_to_the_right(self, handle_row, drag_col, end_col, left_old, right_old, width_old, preserve_values):
        left_new, _col = self.drag_grid_points[handle_row][drag_col]
        width_new = right_old - left_new
        """Adjust points in the same row to preserve relative X spacing"""
        preserve_index = 0
        for col in range(drag_col + 1, end_col):
            old_x, old_y = self.drag_grid_points[handle_row][col]
            relative_pos = preserve_values[preserve_index]
            preserve_index += 1
            new_x = int(left_new + relative_pos * width_new)
            if handle_row == 0:
                print(
                    f"Preserve right: col {col}, row {handle_row}, old_x {old_x}, relative_pos {relative_pos}, new_x {new_x}")
            self.drag_grid_points[handle_row][col] = (new_x, old_y)
            # grid_point_counts[handle_row][col] += 1

    def preserve_x_spacing_to_the_left(self, handle_row, start_col, drag_col, left_old, right_old, width_old,
                                       preserve_values):
        right_new, _col = self.drag_grid_points[handle_row][drag_col]
        width_new = right_new - left_old
        """Adjust points in the same row to preserve relative Y spacing"""
        preserve_index = 0
        for col in range(start_col + 1, drag_col):
            old_x, old_y = self.drag_grid_points[handle_row][col]
            relative_pos = preserve_values[preserve_index]
            preserve_index += 1
            new_x = int(right_new + relative_pos * width_new)
            self.drag_grid_points[handle_row][col] = (new_x, old_y)
            # grid_point_counts[handle_row][col] += 1

    def preserve_y_spacing_to_the_bottom(self, handle_col, drag_row, end_row, top_old, bottom_old, height_old,
                                         preserve_values):
        _row, top_new = self.drag_grid_points[drag_row][handle_col]
        height_new = bottom_old - top_new
        """Adjust points in the same column to preserve relative Y spacing"""
        preserve_index = 0
        for row in range(drag_row + 1, end_row):
            old_x, old_y = self.drag_grid_points[row][handle_col]
            relative_pos = preserve_values[preserve_index]
            preserve_index += 1
            new_y = int(top_new + relative_pos * height_new)
            self.drag_grid_points[row][handle_col] = (old_x, new_y)
            # grid_point_counts[row][handle_col] += 1

    def preserve_y_spacing_to_the_top(self, handle_col, start_row, drag_row, top_old, bottom_old, height_old,
                                      preserve_values):
        _row, bottom_new = self.drag_grid_points[drag_row][handle_col]
        height_new = bottom_new - top_old
        """Adjust points in the same column to preserve relative Y spacing"""
        preserve_index = 0
        for row in range(start_row + 1, drag_row):
            old_x, old_y = self.drag_grid_points[row][handle_col]
            relative_pos = preserve_values[preserve_index]
            preserve_index += 1
            new_y = int(bottom_new + relative_pos * height_new)
            self.drag_grid_points[row][handle_col] = (old_x, new_y)
            # grid_point_counts[row][handle_col] += 1

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self.crop_mode:
            # Set focus so we can receive keyboard events
            self.setFocus()

            # Check if a drag handle was clicked
            for handle in self.drag_handles:
                if QRect(handle['pos'] - QPoint(4, 4), QSize(8, 8)).contains(event.pos()):
                    # Set dragging state
                    self.is_dragging = True
                    self.dragging_handle = handle
                    handle['dragging'] = True
                    # Copy current grid points to drag_grid_points
                    self.drag_grid_points = [row.copy() for row in self.grid_points]
                    self.last_drag_pos = event.pos()
                    self.update()
                    self.drag_preserve_values = None
                    return

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton and self.crop_mode and self.is_dragging and self.dragging_handle and self.drag_grid_points:
            handle = self.dragging_handle

            grid_point_counts = []
            for row in range(self.grid_y_max + 1):  # +1 because we need lines at both edges
                grid_row = [0 for col in range(self.grid_x_max + 1)]
                grid_point_counts.append(grid_row)

            print("\nStart drag")
            # Calculate the movement delta in original image coordinates
            old_pos = self.last_drag_pos
            self.last_drag_pos = event.pos()
            display_delta_x = self.last_drag_pos.x() - old_pos.x()
            display_delta_y = self.last_drag_pos.y() - old_pos.y()

            # Convert display delta to original image coordinate delta
            delta_x = display_delta_x / self.zoom_factor
            delta_y = display_delta_y / self.zoom_factor

            print("display delta:", display_delta_x, display_delta_y, "-> grid delta:", delta_x, delta_y)

            doing_left = handle['left']
            doing_right = handle['right']
            doing_top = handle['top']
            doing_bottom = handle['bottom']

            # Determine which axes this handle can move along
            can_move_x = doing_left or doing_right
            can_move_y = doing_top or doing_bottom

            # Set delta to 0 if movement is not allowed
            if not can_move_x:
                delta_x = 0
            if not can_move_y:
                delta_y = 0

            # Update grid points directly in original image coordinates
            # Get old values for spacing preservation before making changes
            if self.drag_preserve_values is None:
                self.drag_preserve_values = {
                    "left": {},
                    "right": {},
                    "top": {},
                    "bottom": {},
                }

                old_values = {}
                for other_handle in self.drag_handles:
                    other_handle_row = other_handle['row']
                    other_handle_col = other_handle['col']

                    if doing_left and other_handle['left'] and can_move_x:
                        #key = f"left_{other_handle_row}"
                        key = (other_handle_row, other_handle_col, self.grid_x_max)
                        if key not in self.drag_preserve_values['left']:
                            self.drag_preserve_values['left'][key] = self.get_old_x_values_to_the_right(*key)
                        else:
                            print("Already have old values for", key)

                    if doing_right and other_handle['right'] and can_move_x:
                        #key = f"right_{other_handle_row}"
                        key = (other_handle_row, 0, other_handle_col)
                        if key not in self.drag_preserve_values['right']:
                            self.drag_preserve_values['right'][key] = self.get_old_x_values_to_the_left(*key)
                        else:
                            print("Already have old values for", key)

                    if doing_top and other_handle['top'] and can_move_y:
                        #key = f"top_{other_handle_col}"
                        key = (other_handle_col, other_handle_row, self.grid_y_max)
                        if key not in self.drag_preserve_values['top']:
                            self.drag_preserve_values['top'][key] = self.get_old_y_values_to_the_bottom(*key)
                        else:
                            print("Already have old values for", key)

                    if doing_bottom and other_handle['bottom'] and can_move_y:
                        #key = f"bottom_{other_handle_col}"
                        key = (other_handle_col, 0, other_handle_row)
                        if key not in self.drag_preserve_values['bottom']:
                            self.drag_preserve_values['bottom'][key] = self.get_old_y_values_to_the_top(*key)
                        else:
                            print("Already have old values for", key)
            else:
                print("Not updating old values during drag")

            # Apply movement to grid points and update handle positions
            for other_handle in self.drag_handles:
                other_handle_row = other_handle['row']
                other_handle_col = other_handle['col']

                # Check if this handle should be moved
                should_move_x = (doing_left and other_handle['left']) or (doing_right and other_handle['right'])
                should_move_y = (doing_top and other_handle['top']) or (doing_bottom and other_handle['bottom'])

                if should_move_x or should_move_y:
                    # Get current grid point
                    old_x, old_y = self.drag_grid_points[other_handle_row][other_handle_col]

                    # Apply delta in original coordinates
                    new_x = old_x + (delta_x if should_move_x else 0)
                    new_y = old_y + (delta_y if should_move_y else 0)

                    # Update grid point
                    self.drag_grid_points[other_handle_row][other_handle_col] = (int(new_x), int(new_y))
                    grid_point_counts[other_handle_row][other_handle_col] += 1

                    # Update handle display position from grid point
                    scaled_point = self.get_scaled_grid_point(other_handle_row, other_handle_col, self.drag_grid_points)
                    if scaled_point:
                        other_handle['pos'] = QPoint(int(scaled_point[0]), int(scaled_point[1]))
                        other_handle['updated'] = True

            # Preserve spacing after all handles have been moved
            for key, values in self.drag_preserve_values['left'].items():
                self.preserve_x_spacing_to_the_right(*values)
            for key, values in self.drag_preserve_values['right'].items():
                self.preserve_x_spacing_to_the_left(*values)
            for key, values in self.drag_preserve_values['top'].items():
                self.preserve_y_spacing_to_the_bottom(*values)
            for key, values in self.drag_preserve_values['bottom'].items():
                self.preserve_y_spacing_to_the_top(*values)

            for row in range(self.grid_y_max + 1):  # +1 because we need lines at both edges
                for col in range(self.grid_x_max + 1):
                    if grid_point_counts[row][col] > 1:
                        print(f"Point ({row},{col}) modified {grid_point_counts[row][col]} times during this drag")
                print("for row %d: %s" % (row, grid_point_counts[row]))  # Debug output for each row

            self.update_drag_handle_positions()
            self.update()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self.crop_mode:
            # Copy modified grid points back to the main grid_points if we were dragging
            if self.is_dragging and self.drag_grid_points:
                # Deep copy the modified grid points back to the main grid
                self.grid_points = [row.copy() for row in self.drag_grid_points]
                print(f"Grid points updated from drag copy after dragging")  # Debug output
                # Clear the copy to free memory and ensure clean state
                self.drag_grid_points = []
                self.drag_preserve_values = None
                # Redraw the grid with the updated points
                self.update_display()

            # Clear dragging state
            self.is_dragging = False
            self.dragging_handle = None

            for handle in self.drag_handles:
                handle['dragging'] = False

            # Handle dragging is complete, but keep crop mode active
            # User can exit crop mode manually using the crop button

    def keyPressEvent(self, event):
        """Handle key press events - particularly Escape to cancel drag operations"""
        super().keyPressEvent(event)

        # Check if Escape key is pressed while dragging
        if event.key() == Qt.Key_Escape and self.is_dragging:
            self.cancel_drag_operation()
        else:
            # Pass other key events to parent
            super().keyPressEvent(event)

    def cancel_drag_operation(self):
        """Cancel the current drag operation and restore original handle positions"""
        if not self.is_dragging:
            return

        print("Drag operation cancelled - restoring original positions")

        # Restore handle positions from the original grid points
        if self.drag_grid_points:
            # Recreate handles at their original positions
            self.create_drag_handles()

        # Clear the drag grid points copy without applying changes
        self.drag_grid_points = []
        self.drag_preserve_values = None

        # Clear dragging state
        self.is_dragging = False
        self.dragging_handle = None

        # Clear dragging flags from all handles
        for handle in self.drag_handles:
            handle['dragging'] = False

        # Redraw to show the restored state
        self.update()

    def calculate_grid_points(self):
        """Calculate the 2D array of grid point locations in original image dimensions"""
        self.grid_points = []

        if not self.original_pixmap or self.grid_x_max == 0 or self.grid_y_max == 0:
            return

        # Use original image dimensions (unscaled)
        original_size = self.original_pixmap.size()
        width = original_size.width()
        height = original_size.height()

        # Calculate grid spacing in original image coordinates
        x_spacing = width / self.grid_x_max
        y_spacing = height / self.grid_y_max

        # Create 2D array with grid point coordinates in original image dimensions
        # Array structure: grid_points[row][col] = (x, y) in original image pixels
        for row in range(self.grid_y_max + 1):  # +1 because we need lines at both edges
            grid_row = []
            y = int(row * y_spacing)

            for col in range(self.grid_x_max + 1):  # +1 because we need lines at both edges
                x = int(col * x_spacing)
                grid_row.append((x, y))

            self.grid_points.append(grid_row)
            print("Row %d: %s" % (row, grid_row))  # Debug output for each row

        # Print debug information about grid points (can be removed later)
        print(f"Grid points calculated: {len(self.grid_points)} rows x {len(self.grid_points[0]) if self.grid_points else 0} cols")
        print(f"Original image size: {width}x{height}")
        if self.grid_points:
            print(f"Top-left corner: {self.grid_points[0][0]}")
            print(f"Bottom-right corner: {self.grid_points[-1][-1]}")

    def set_grid_points(self, grid_points):
        """Set the grid points directly from loaded data"""
        self.grid_points = grid_points if grid_points else []
        print(f"Grid points loaded: {len(self.grid_points)} rows x {len(self.grid_points[0]) if self.grid_points else 0} cols")
        if self.grid_points:
            print(f"Loaded top-left corner: {self.grid_points[0][0]}")
            print(f"Loaded bottom-right corner: {self.grid_points[-1][-1]}")

    def get_grid_point(self, row, col, grid_points=None):
        """Get the coordinates of a specific grid point in original image dimensions"""
        if grid_points is None:
            grid_points = self.grid_points
        if (grid_points and 0 <= row < len(grid_points) and 0 <= col < len(grid_points[0])):
            return grid_points[row][col]
        return None

    def get_scaled_grid_point(self, row, col, grid_points=None):
        """Get the coordinates of a specific grid point scaled to current zoom and with padding offset"""
        original_point = self.get_grid_point(row, col, grid_points)
        if original_point is None:
            return None

        # Scale the original coordinates to current zoom level
        scaled_x = int(original_point[0] * self.zoom_factor) + self.padding
        scaled_y = int(original_point[1] * self.zoom_factor) + self.padding

        return (scaled_x, scaled_y)

class PuzzleGridViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Puzzle Pieces Maker")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Control buttons
        button_layout = QHBoxLayout()

        self.load_button = QPushButton("Load Document")
        self.load_button.clicked.connect(self.load_document)
        button_layout.addWidget(self.load_button)

        # In PuzzleGridViewer.__init__ (button layout section)
        self.reload_button = QPushButton("Reload Existing Document")
        self.reload_button.clicked.connect(self.reload_document)
        self.reload_button.setEnabled(False)
        button_layout.addWidget(self.reload_button)

        self.open_button = QPushButton("Open Image")
        self.open_button.clicked.connect(self.open_image)
        button_layout.addWidget(self.open_button)

        self.grid_button = QPushButton("Set Grid Dimensions")
        self.grid_button.clicked.connect(self.set_grid_dimensions)
        self.grid_button.setEnabled(False)
        button_layout.addWidget(self.grid_button)

        self.save_button = QPushButton("Save Document")
        self.save_button.clicked.connect(self.save_document)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        self.save_as_button = QPushButton("Save Document As...")
        self.save_as_button.clicked.connect(self.save_document_as)
        self.save_as_button.setEnabled(False)
        button_layout.addWidget(self.save_as_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        zoom_layout.addWidget(QLabel("Zoom:"))
        
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_out_button.setEnabled(False)
        zoom_layout.addWidget(self.zoom_out_button)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)  # 10% zoom
        self.zoom_slider.setMaximum(500)  # 500% zoom
        self.zoom_slider.setValue(100)  # 100% zoom
        self.zoom_slider.setEnabled(False)
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_in_button.setEnabled(False)
        zoom_layout.addWidget(self.zoom_in_button)
        
        self.zoom_fit_button = QPushButton("Fit to Window")
        self.zoom_fit_button.clicked.connect(self.zoom_fit)
        self.zoom_fit_button.setEnabled(False)
        zoom_layout.addWidget(self.zoom_fit_button)
        
        self.zoom_actual_button = QPushButton("Actual Size")
        self.zoom_actual_button.clicked.connect(self.zoom_actual)
        self.zoom_actual_button.setEnabled(False)
        zoom_layout.addWidget(self.zoom_actual_button)
        
        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_label)
        
        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)

        # Toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.StyledPanel)
        toolbar_frame.setMaximumHeight(50)
        toolbar_layout = QHBoxLayout(toolbar_frame)

        self.crop_mode = False
        self.crop_button = QPushButton("Crop")
        self.crop_button.clicked.connect(self.toggle_crop_mode)
        self.crop_button.setEnabled(False)
        self.crop_button.setCheckable(True)
        toolbar_layout.addWidget(self.crop_button)

        # Add Drag Endpoints button
        self.drag_endpoints_mode = False
        self.drag_endpoints_button = QPushButton("Drag Endpoints")
        self.drag_endpoints_button.clicked.connect(self.toggle_drag_endpoints_mode)
        self.drag_endpoints_button.setEnabled(False)
        self.drag_endpoints_button.setCheckable(True)
        toolbar_layout.addWidget(self.drag_endpoints_button)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        # Scroll area for image display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.image_widget = ImageGridWidget()
        self.scroll_area.setWidget(self.image_widget)
        layout.addWidget(self.scroll_area)

        # Status
        self.status_label = QLabel("Click 'Open Image' to start")
        layout.addWidget(self.status_label)

        self.current_image_path = None
        self.current_document_path = None

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )

        if file_path:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Error", "Could not load the selected image file.")
                return

            self.current_image_path = file_path
            # Clear current document path since this is a new image
            self.current_document_path = None

            # clear away existing grid and crop mode
            self.clear_crop_mode()

            # Get grid dimensions
            dialog = GridDimensionsDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                grid_x, grid_y = dialog.get_dimensions()

                # Display image with grid
                self.image_widget.set_image_and_grid(pixmap, grid_x, grid_y)
                self.grid_button.setEnabled(True)
                self.save_button.setEnabled(True)
                self.save_as_button.setEnabled(True)
                self.crop_button.setEnabled(True)
                self.enable_zoom_controls(True)

                filename = os.path.basename(file_path)
                self.status_label.setText(f"Image: {filename} | Grid: {grid_x}x{grid_y}")
            else:
                # User cancelled, just show image without grid
                self.image_widget.set_image_and_grid(pixmap, 0, 0)
                self.grid_button.setEnabled(True)
                self.save_button.setEnabled(True)
                self.save_as_button.setEnabled(True)
                self.crop_button.setEnabled(True)
                self.enable_zoom_controls(True)
                filename = os.path.basename(file_path)
                self.status_label.setText(f"Image: {filename} | No grid")

    def enable_zoom_controls(self, enabled):
        """Enable or disable all zoom controls"""
        self.zoom_out_button.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)
        self.zoom_in_button.setEnabled(enabled)
        self.zoom_fit_button.setEnabled(enabled)
        self.zoom_actual_button.setEnabled(enabled)

    def set_grid_dimensions(self):
        if not self.current_image_path:
            return

        dialog = GridDimensionsDialog(self, self.image_widget.grid_x_max, self.image_widget.grid_y_max)
        if dialog.exec_() == QDialog.Accepted:
            # clear away existing grid and crop mode
            self.clear_crop_mode()

            grid_x, grid_y = dialog.get_dimensions()

            # Reload the original image and apply new grid
            pixmap = QPixmap(self.current_image_path)
            self.image_widget.set_image_and_grid(pixmap, grid_x, grid_y)

            filename = os.path.basename(self.current_image_path)
            self.status_label.setText(f"Image: {filename} | Grid: {grid_x}x{grid_y}")

    def zoom_in(self):
        current_zoom = self.image_widget.zoom_factor
        new_zoom = min(current_zoom * 1.1, 5.0)  # Max zoom 500%
        self.image_widget.set_zoom(new_zoom)
        self.zoom_slider.setValue(int(new_zoom * 100))
        self.zoom_label.setText(f"{int(new_zoom * 100)}%")

    def zoom_out(self):
        current_zoom = self.image_widget.zoom_factor
        new_zoom = max(current_zoom / 1.1, 0.1)  # Min zoom 10%
        self.image_widget.set_zoom(new_zoom)
        self.zoom_slider.setValue(int(new_zoom * 100))
        self.zoom_label.setText(f"{int(new_zoom * 100)}%")

    def zoom_changed(self, value):
        zoom_factor = value / 100.0
        self.image_widget.set_zoom(zoom_factor)
        self.zoom_label.setText(f"{value}%")

    def zoom_fit(self):
        if self.image_widget.original_pixmap:
            # Get the scroll area's viewport size (available space for the image)
            viewport_size = self.scroll_area.viewport().size()

            # Get original image size
            image_size = self.image_widget.original_pixmap.size()

            # Calculate zoom factors needed to fit width and height
            width_zoom = viewport_size.width() / image_size.width()
            height_zoom = viewport_size.height() / image_size.height()

            # Use the smaller zoom factor to ensure the entire image fits
            fit_zoom = min(width_zoom, height_zoom)

            # Clamp zoom to our valid range (0.1 to 5.0)
            fit_zoom = max(0.1, min(fit_zoom, 5.0))

            # Apply the calculated zoom
            self.image_widget.set_zoom(fit_zoom)
            self.zoom_slider.setValue(int(fit_zoom * 100))
            self.zoom_label.setText(f"{int(fit_zoom * 100)}%")

    def zoom_actual(self):
        if self.image_widget.original_pixmap:
            self.image_widget.set_zoom(1.0)
            self.zoom_slider.setValue(100)
            self.zoom_label.setText("100%")

    def _save_document_to_file(self, file_path):
        """Helper function to save document data to a specified file path"""
        if not self.current_image_path:
            return False

        # Create the document data with all required information
        # Convert backslashes to forward slashes for cross-platform compatibility
        normalized_image_path = self.current_image_path.replace('\\', '/')

        # Get current window geometry
        geometry = self.geometry()

        document_data = {
            "grid_x": self.image_widget.grid_x_max,
            "grid_y": self.image_widget.grid_y_max,
            "image_path": normalized_image_path,
            "zoom_value": self.image_widget.zoom_factor,
            "grid_points": self.image_widget.grid_points,  # Save grid points array
            "window_width": geometry.width(),
            "window_height": geometry.height(),
            "window_x": geometry.x(),
            "window_y": geometry.y()
        }

        try:
            with open(file_path, "w") as json_file:
                json.dump(document_data, json_file, indent=2)

            QMessageBox.information(
                self,
                "Document Saved",
                f"Document saved successfully to:\n{file_path}\n\n"
                f"Grid: {document_data['grid_x']}x{document_data['grid_y']}\n"
                f"Zoom: {int(document_data['zoom_value'] * 100)}%"
            )
            # Enable reload button since we have a loaded document
            self.reload_button.setEnabled(True)

            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save document:\n{str(e)}"
            )
            return False

    def save_document(self):
        if not self.current_image_path:
            return

        # If we have a current document path, save to it directly
        if self.current_document_path:
            self._save_document_to_file(self.current_document_path)
        else:
            # No current document path, so act like "Save As..."
            self.save_document_as()

    def save_document_as(self):
        if not self.current_image_path:
            return

        # Get the directory of the current image
        directory = os.path.dirname(self.current_image_path)

        # Create a default file name based on the image name
        image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        default_file_name = os.path.join(directory, f"{image_name}_modified.puz.json")

        # Show a file dialog to save the document
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document As",
            default_file_name,
            "Puzzle JSON Files (*.puz.json);;JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            # Use the shared save function
            if self._save_document_to_file(file_path):
                # Update current document path only if save was successful
                self.current_document_path = file_path

    def clear_crop_mode(self):
        if self.crop_mode:
            # clear drag movde
            self.image_widget.cancel_drag_operation()
            # restore button state
            # Uncheck the crop button
            self.crop_button.setChecked(False)
            self.toggle_crop_mode()

    def load_document_from_path(self, file_path):
        self.clear_crop_mode()

        """Load a document from a given file path"""
        try:
            with open(file_path, "r") as json_file:
                document_data = json.load(json_file)

            # Validate document data
            grid_x = document_data.get("grid_x")
            grid_y = document_data.get("grid_y")
            image_path = document_data.get("image_path")
            zoom_value = document_data.get("zoom_value", 1.0)
            saved_grid_points = document_data.get("grid_points")  # Load saved grid points

            # Get window dimensions (with fallbacks for older documents)
            window_width = document_data.get("window_width")
            window_height = document_data.get("window_height")
            window_x = document_data.get("window_x")
            window_y = document_data.get("window_y")

            if grid_x is None or grid_y is None or image_path is None:
                raise ValueError("Invalid document structure.")

            # Convert forward slashes back to native path format if needed
            if '/' in image_path and os.sep == '\\':
                image_path = image_path.replace('/', '\\')

            # Update viewer state
            self.current_image_path = image_path
            self.current_document_path = file_path  # Set the current document path

            # Restore window dimensions if available, ensuring it's on screen
            if all(v is not None for v in [window_width, window_height, window_x, window_y]):
                # Use the ensure_window_on_screen method to validate and adjust the position
                adjusted_x, adjusted_y, adjusted_width, adjusted_height = self.ensure_window_on_screen(
                    window_x, window_y, window_width, window_height
                )
                self.setGeometry(adjusted_x, adjusted_y, adjusted_width, adjusted_height)

            # Load and display the image
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Error", f"Could not load the image from the document:\n{image_path}")
                return False

            # Set up the image widget
            self.image_widget.original_pixmap = pixmap
            self.image_widget.grid_x_max = grid_x
            self.image_widget.grid_y_max = grid_y

            # Load saved grid points if available, otherwise calculate them
            if saved_grid_points:
                self.image_widget.set_grid_points(saved_grid_points)
                print("Using saved grid points from document")
            else:
                self.image_widget.calculate_grid_points()
                print("No saved grid points found, calculated new ones")

            # Set zoom and update display
            self.image_widget.zoom_factor = 1.0  # Reset to default first
            self.image_widget.update_display()
            self.image_widget.set_zoom(zoom_value)

            # Update zoom controls to match loaded zoom
            self.zoom_slider.setValue(int(zoom_value * 100))
            self.zoom_label.setText(f"{int(zoom_value * 100)}%")

            # Update status
            filename = os.path.basename(image_path)
            self.status_label.setText(f"Image: {filename} | Grid: {grid_x}x{grid_y} | Zoom: {int(zoom_value * 100)}%")

            # Update window title to include document name
            document_name = os.path.basename(file_path)
            self.setWindowTitle(f"Puzzle Pieces Maker - {document_name}")

            # Enable controls
            self.grid_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.save_as_button.setEnabled(True)
            self.crop_button.setEnabled(True)
            self.enable_zoom_controls(True)
            self.drag_endpoints_button.setEnabled(True)

            # Enable reload button since we have a loaded document
            self.reload_button.setEnabled(True)

            return True

        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load document:\n{str(e)}"
            )
            return False

    def load_document(self):
        """Load document using file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Document",
            "",
            "Puzzle JSON Files (*.puz.json);;JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            self.load_document_from_path(file_path)

    def reload_document(self):
        """Reload the current document from disk"""
        if self.current_document_path and os.path.exists(self.current_document_path):
            reply = QMessageBox.question(
                self,
                "Reload Document",
                "Any unsaved changes will be lost. Do you want to reload?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.load_document_from_path(self.current_document_path)
        else:
            QMessageBox.warning(self, "Reload Error", "No document to reload or file not found.")

    def toggle_crop_mode(self):
        """Toggle crop mode on/off"""
        if self.crop_button.isChecked():
            # Enable crop mode
            self.crop_mode = True
            self.image_widget.set_crop_mode(True)
            self.crop_button.setText("Exit Crop")
        else:
            # Disable crop mode
            self.crop_mode = False
            self.image_widget.set_crop_mode(False)
            self.crop_button.setText("Crop")

    def toggle_drag_endpoints_mode(self):
        """Toggle drag endpoints mode on/off"""
        if self.drag_endpoints_button.isChecked():
            # Enable drag endpoints mode
            self.drag_endpoints_mode = True
            self.image_widget.set_drag_endpoints_mode(True)
            self.drag_endpoints_button.setText("Exit Drag Endpoints")
        else:
            # Disable drag endpoints mode
            self.drag_endpoints_mode = False
            self.image_widget.set_drag_endpoints_mode(False)
            self.drag_endpoints_button.setText("Drag Endpoints")

    def ensure_window_on_screen(self, x, y, width, height):
        """Ensure the window position is visible on screen, adjusting if necessary"""
        # Get the desktop widget to access screen geometry
        desktop = QApplication.desktop()

        # Get all available screens
        num_screens = desktop.screenCount()
        all_screens_geometry = QRect()

        # Calculate the combined geometry of all screens
        for i in range(num_screens):
            screen_geometry = desktop.availableGeometry(i)
            if i == 0:
                all_screens_geometry = screen_geometry
            else:
                all_screens_geometry = all_screens_geometry.united(screen_geometry)

        # Ensure the window isn't too large for any screen
        max_width = all_screens_geometry.width()
        max_height = all_screens_geometry.height()
        width = min(width, max_width)
        height = min(height, max_height)

        # Check if the window would be visible on any screen
        window_rect = QRect(x, y, width, height)
        is_visible_on_any_screen = False

        for i in range(num_screens):
            screen_geometry = desktop.availableGeometry(i)
            # Check if the window intersects with this screen (at least partially visible)
            if window_rect.intersects(screen_geometry):
                # Check if at least 25% of the window is visible on this screen
                intersection = window_rect.intersected(screen_geometry)
                visible_area = intersection.width() * intersection.height()
                total_area = width * height
                if visible_area >= total_area * 0.25:  # At least 25% visible
                    is_visible_on_any_screen = True
                    break

        # If not sufficiently visible on any screen, move to primary screen
        if not is_visible_on_any_screen:
            primary_screen = desktop.availableGeometry(desktop.primaryScreen())
            # Center the window on the primary screen
            x = primary_screen.x() + (primary_screen.width() - width) // 2
            y = primary_screen.y() + (primary_screen.height() - height) // 2

            # Ensure it fits within the primary screen bounds
            x = max(primary_screen.left(), min(x, primary_screen.right() - width))
            y = max(primary_screen.top(), min(y, primary_screen.bottom() - height))

        return x, y, width, height

def main():
    app = QApplication(sys.argv)
    viewer = PuzzleGridViewer()

    # Check for command line arguments
    if len(sys.argv) > 1:
        document_path = sys.argv[1]
        # Check if the file exists and has the right extension
        if os.path.exists(document_path) and document_path.lower().endswith(('.puz.json', '.json')):
            # Load the document after the viewer is shown
            viewer.show()
            viewer.load_document_from_path(document_path)
        else:
            viewer.show()
            if not os.path.exists(document_path):
                QMessageBox.warning(viewer, "File Not Found", f"The specified file does not exist:\n{document_path}")
            else:
                QMessageBox.warning(viewer, "Invalid File", f"The specified file is not a valid puzzle document:\n{document_path}")
    else:
        viewer.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
