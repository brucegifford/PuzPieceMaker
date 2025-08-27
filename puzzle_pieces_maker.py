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
        self.grid_x = 0
        self.grid_y = 0
        self.zoom_factor = 1.0
        self.crop_mode = False
        self.drag_handles = []
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid gray;")
        self.setMinimumSize(400, 300)

    def set_image_and_grid(self, pixmap, grid_x, grid_y):
        self.original_pixmap = pixmap
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.zoom_factor = 1.0  # Reset zoom when new image is loaded
        self.update_display()

    def set_zoom(self, zoom_factor):
        self.zoom_factor = zoom_factor
        self.update_display()

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
        self.setPixmap(gridded_pixmap)
        
        # Adjust widget size to match the pixmap
        self.resize(gridded_pixmap.size())

    def draw_grid(self, pixmap):
        # Create a copy to draw on
        result_pixmap = pixmap.copy()
        painter = QPainter(result_pixmap)

        # Set up pen for grid lines
        pen = QPen(Qt.red, 2)
        painter.setPen(pen)

        width = result_pixmap.width()
        height = result_pixmap.height()

        # Calculate grid spacing
        x_spacing = width / self.grid_x
        y_spacing = height / self.grid_y

        # Draw vertical lines (including left and right borders)
        for i in range(self.grid_x + 1):
            x = int(i * x_spacing)
            painter.drawLine(x, 0, x, height)

        # Draw horizontal lines (including top and bottom borders)
        for i in range(self.grid_y + 1):
            y = int(i * y_spacing)
            painter.drawLine(0, y, width, y)

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

    def create_drag_handles(self):
        """Create drag handles at grid corners and midpoints"""
        self.drag_handles = []
        if not self.original_pixmap or self.grid_x == 0 or self.grid_y == 0:
            return

        # Get current image dimensions
        current_pixmap = self.pixmap()
        if not current_pixmap:
            return

        width = current_pixmap.width()
        height = current_pixmap.height()

        # Corner handles (4 corners of the grid)
        corners = [
            (0, 0),  # Top-left
            (width, 0),  # Top-right
            (0, height),  # Bottom-left
            (width, height)  # Bottom-right
        ]

        for x, y in corners:
            self.drag_handles.append({'pos': QPoint(int(x), int(y)), 'type': 'corner'})

        # Single midpoint handle on each outside edge
        # Top edge center
        self.drag_handles.append({'pos': QPoint(width // 2, 0), 'type': 'edge'})

        # Bottom edge center
        self.drag_handles.append({'pos': QPoint(width // 2, height), 'type': 'edge'})

        # Left edge center
        self.drag_handles.append({'pos': QPoint(0, height // 2), 'type': 'edge'})

        # Right edge center
        self.drag_handles.append({'pos': QPoint(width, height // 2), 'type': 'edge'})

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap() or not self.crop_mode:
            return

        painter = QPainter(self)
        pen = QPen(Qt.blue, 2, Qt.DashLine)
        painter.setPen(pen)

        # Draw the crop rectangle
        rect = QRect(self.drag_handles[0]['pos'], self.drag_handles[3]['pos'])
        painter.drawRect(rect.normalized())

        # Draw drag handles
        for handle in self.drag_handles:
            self.draw_drag_handle(painter, handle)

    def draw_drag_handle(self, painter, handle):
        """Draw a single drag handle"""
        size = 8
        rect = QRect(handle['pos'] - QPoint(size // 2, size // 2), QSize(size, size))
        painter.drawRect(rect)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self.crop_mode:
            # Check if a drag handle was clicked
            for handle in self.drag_handles:
                if QRect(handle['pos'] - QPoint(4, 4), QSize(8, 8)).contains(event.pos()):
                    handle['dragging'] = True
                    self.update()
                    return

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton and self.crop_mode:
            for handle in self.drag_handles:
                if handle.get('dragging'):
                    # Move the handle with the mouse
                    handle['pos'] = event.pos()
                    self.update()
                    return

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self.crop_mode:
            for handle in self.drag_handles:
                handle['dragging'] = False

            # Here you can add code to handle the cropping logic,
            # such as updating the original_pixmap to the new cropped area.
            # For now, we just disable crop mode.
            self.set_crop_mode(False)


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

        self.crop_button = QPushButton("Crop")
        self.crop_button.clicked.connect(self.toggle_crop_mode)
        self.crop_button.setEnabled(False)
        self.crop_button.setCheckable(True)
        toolbar_layout.addWidget(self.crop_button)

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

        dialog = GridDimensionsDialog(self, self.image_widget.grid_x, self.image_widget.grid_y)
        if dialog.exec_() == QDialog.Accepted:
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

    def save_document(self):
        if not self.current_image_path:
            return

        # If we have a current document path, save to it directly
        if self.current_document_path:
            file_path = self.current_document_path
        else:
            # No current document path, so act like "Save As..."
            self.save_document_as()
            return

        # Create the document data with all required information
        # Convert backslashes to forward slashes for cross-platform compatibility
        normalized_image_path = self.current_image_path.replace('\\', '/')

        # Get current window geometry
        geometry = self.geometry()

        document_data = {
            "grid_x": self.image_widget.grid_x,
            "grid_y": self.image_widget.grid_y,
            "image_path": normalized_image_path,
            "zoom_value": self.image_widget.zoom_factor,
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
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save document:\n{str(e)}"
            )

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
            # Create the document data with all required information
            # Convert backslashes to forward slashes for cross-platform compatibility
            normalized_image_path = self.current_image_path.replace('\\', '/')

            # Get current window geometry
            geometry = self.geometry()

            document_data = {
                "grid_x": self.image_widget.grid_x,
                "grid_y": self.image_widget.grid_y,
                "image_path": normalized_image_path,
                "zoom_value": self.image_widget.zoom_factor,
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

                # Update current document path
                self.current_document_path = file_path

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save document:\n{str(e)}"
                )

    def load_document_from_path(self, file_path):
        """Load a document from a given file path"""
        try:
            with open(file_path, "r") as json_file:
                document_data = json.load(json_file)

            # Validate document data
            grid_x = document_data.get("grid_x")
            grid_y = document_data.get("grid_y")
            image_path = document_data.get("image_path")
            zoom_value = document_data.get("zoom_value", 1.0)

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

            # Restore window dimensions if available
            if all(v is not None for v in [window_width, window_height, window_x, window_y]):
                self.setGeometry(window_x, window_y, window_width, window_height)

            # Load and display the image
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Error", f"Could not load the image from the document:\n{image_path}")
                return False

            self.image_widget.set_image_and_grid(pixmap, grid_x, grid_y)
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

    def toggle_crop_mode(self):
        """Toggle crop mode on/off"""
        if self.crop_button.isChecked():
            # Enable crop mode
            self.image_widget.set_crop_mode(True)
            self.crop_button.setText("Exit Crop")
        else:
            # Disable crop mode
            self.image_widget.set_crop_mode(False)
            self.crop_button.setText("Crop")


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
