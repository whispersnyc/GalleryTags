import sys
import os
import re
import shutil
import ctypes
from ctypes import wintypes, windll
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                            QLabel, QScrollArea, QInputDialog, QMessageBox, 
                            QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                            QShortcut, QComboBox, QDialog, QFrame, QMenu)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QSize, QRect, QPoint, QTimer
from PIL import Image
import piexif
from io import BytesIO
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import subprocess
from config import APP_CONFIG, EXPORT_PATHS, EXPORT_CONFIG, FORMAT_CONFIG
# config.APP_CONFIG = {"default_folder":path_str}
# config.EXPORT_PATHS = {file_path_str: tags_str ("& tag1, tag2" means AND while '|' prefix means OR, default AND)}
# config.EXPORT_CONFIG = {'heading': heading_str, 'item_format': "![$fn]($fp/$fn.$fe)\n", "group_by": 5}
# config.FORMAT_CONFIG = {'.ext': '-(Exif/XMP):(Property)', 'extensions': ['.ext', '.extension'], ...}

# Helper to get all supported extensions
SUPPORTED_EXTENSIONS = [ext for format_info in FORMAT_CONFIG.values() 
                       for ext in format_info['extensions']]

def natural_sort_key(s):
    parts = re.split('([0-9]+)', os.path.basename(s))
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def check_exiftool():
    """Check if exiftool is available in the system"""
    exiftool_cmd = 'exiftool.exe' if sys.platform == "win32" else 'exiftool'
    if not shutil.which(exiftool_cmd):
        msg = """ExifTool is not found in your system PATH. 
Please install ExifTool and make sure it's accessible from the command line.
Download from: https://exiftool.org/"""
        QMessageBox.critical(None, "ExifTool Not Found", msg)
        sys.exit(1)

def get_short_path_name(long_name):
    """Get short path name, with cross-platform fallback"""
    if sys.platform == "win32":
        try:
            buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if windll.kernel32.GetShortPathNameW(long_name, buffer, wintypes.MAX_PATH) > 0:
                return buffer.value
        except Exception as e:
            print(f"Error getting short path: {e}")
    return long_name

# Helper to get metadata field for a file
def get_metadata_field(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    for format_info in FORMAT_CONFIG.values():
        if ext in format_info['extensions']:
            return format_info['field']
    return None

def parse_tags(tag_string):
    """Helper function to parse tag string into a set of cleaned tags"""
    if not tag_string:
        return set()
    return {tag.strip().lower() for tag in tag_string.split(',') if tag.strip()}

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Progress label
        self.progress_label = QLabel("Loading...")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background-color: rgba(0, 0, 0, 140);
                padding: 10px 20px;
                border-radius: 5px;
            }
        """)
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label, alignment=Qt.AlignCenter)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        self.hide()
    
    def update_progress(self, current, total):
        self.progress_label.setText(f"Loading... {current}/{total}")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setFixedSize(self.parent().size())

class ImageCell(QWidget):
    def __init__(self, image_path, cell_size, parent=None):
        super().__init__(parent)
        self.image_path = os.path.normpath(image_path)  # Normalize path for multiplatform support
        self.short_path = None  # Will be set when needed
        self.cell_size = cell_size
        self.selected = False
        self.tag_text = self.read_tag_metadata()
        self.setFixedSize(cell_size, cell_size)
        self.setMouseTracking(True)
        
        # Load image and create pixmap
        self.load_image()
        
        # Setup visual properties
        self.setStyleSheet("border: 1px solid #999999;")
        
        # Set different background color based on tag status
        self.update_background()

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def get_exiftool_path(self):
        """Get the appropriate path for ExifTool operations"""
        if sys.platform == "win32" and not self.short_path:
            if any(ord(c) > 127 for c in self.image_path):
                self.short_path = get_short_path_name(self.image_path)
        return self.short_path if self.short_path else self.image_path

    def update_background(self):
        if self.tag_text:
            # Darker background for tagged images
            self.setStyleSheet("border: 1px solid #999999; background-color: #EBEBEB;")
        else:
            # Default background for untagged images
            self.setStyleSheet("border: 1px solid #999999; background-color: white;")
        
    def load_image(self):
        image = QImage(self.image_path)
        if not image.isNull():
            # Scale image to fit cell while preserving aspect ratio
            self.pixmap = QPixmap.fromImage(image)
            self.pixmap = self.pixmap.scaled(
                self.cell_size, self.cell_size, 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        else:
            # Create an empty pixmap if image can't be loaded
            self.pixmap = QPixmap(self.cell_size, self.cell_size)
            self.pixmap.fill(Qt.lightGray)
    
    def read_tag_metadata(self):
        """Read tag metadata using exiftool"""
        try:
            field = get_metadata_field(self.image_path)
            if not field:
                print(f"Unsupported file format: {self.image_path}")
                return ""
                
            result = subprocess.run(
                ['exiftool', field, '-b', self.get_exiftool_path()], 
                capture_output=True, text=True, check=True,
                encoding='utf-8'
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"ExifTool error for {self.image_path}: {e.stderr}")
            return ""
        except Exception as e:
            print(f"Error reading metadata from {self.image_path}: {e}")
            return ""

    def write_tag_metadata(self, tag_text):
        """Write tag metadata using exiftool"""
        try:
            field = get_metadata_field(self.image_path)
            if not field:
                print(f"Unsupported file format: {self.image_path}")
                return False
                
            # ExifTool command to write metadata
            result = subprocess.run(
                ['exiftool', f'{field}={tag_text}', '-overwrite_original', self.get_exiftool_path()],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode == 0:
                self.tag_text = tag_text
                self.update_background()
                self.update()
                return True
            else:
                print(f"ExifTool error: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error writing metadata to {self.image_path}: {e}")
            return False
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw background based on tag status
        if self.tag_text:
            # Darker background for tagged images
            painter.fillRect(self.rect(), QColor(235, 235, 235))
        else:
            # Default white background for untagged images
            painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # Calculate the centering position for the image
        x = (self.width() - self.pixmap.width()) // 2
        y = (self.height() - self.pixmap.height()) // 2
        
        # Draw the image
        painter.drawPixmap(x, y, self.pixmap)
        
        # Draw selection overlay if selected
        if self.selected:
            painter.setPen(QPen(QColor(0, 120, 215), 3))
            painter.drawRect(2, 2, self.width()-4, self.height()-4)
        
        # Draw tag metadata if it exists
        if self.tag_text:
            # Create a semi-transparent rectangle at the bottom
            tag_rect_height = 24
            painter.fillRect(
                QRect(0, self.height() - tag_rect_height, self.width(), tag_rect_height),
                QColor(0, 0, 0, 150)
            )
            
            # Draw the tag text
            painter.setPen(Qt.white)
            # Truncate text if it's too long
            displayed_text = self.tag_text
            if len(displayed_text) > 20:
                displayed_text = displayed_text[:17] + "..."
            painter.drawText(
                QRect(5, self.height() - tag_rect_height, self.width() - 10, tag_rect_height),
                Qt.AlignVCenter, displayed_text
            )
    
    def toggle_selection(self):
        self.selected = not self.selected
        self.update()
    
    def set_selected(self, selected):
        if self.selected != selected:
            self.selected = selected
            self.update()

    def show_context_menu(self, position):
        """Show context menu for cell"""
        # Get parent ImageGallery window
        gallery = self.window()
        
        # If no cells are selected, select this one
        if not gallery.selected_cells:
            gallery.selected_cells.clear()
            for cell in gallery.image_cells:
                cell.set_selected(False)
            self.set_selected(True)
            gallery.selected_cells.add(self)
        
        menu = QMenu(self)
        refresh_action = menu.addAction(f"Refresh Tags ({len(gallery.selected_cells)} selected)")
        action = menu.exec_(self.mapToGlobal(position))
        
        if action == refresh_action:
            # Refresh all selected cells
            for cell in gallery.selected_cells:
                try:
                    new_tags = cell.read_tag_metadata()
                    if new_tags != cell.tag_text:
                        cell.tag_text = new_tags
                        cell.update_background()
                        cell.update()
                except Exception as e:
                    print(f"Error refreshing tags for {cell.image_path}: {e}")
                    QMessageBox.warning(
                        self, 
                        "Refresh Error",
                        f"Error refreshing tags for {os.path.basename(cell.image_path)}:\n{str(e)}"
                    )

    def refresh_single(self):
        """Refresh tags for this cell only"""
        try:
            new_tags = self.read_tag_metadata()
            if new_tags != self.tag_text:
                self.tag_text = new_tags
                self.update_background()
                self.update()
        except Exception as e:
            print(f"Error refreshing tags for {self.image_path}: {e}")
            QMessageBox.warning(
                self, 
                "Refresh Error",
                f"Error refreshing tags for {os.path.basename(self.image_path)}:\n{str(e)}"
            )

class ImageDetailsPopup(QWidget):
    def __init__(self, parent=None, image_path="", tag_text="", position=None, on_tags_updated=None):
        super().__init__(parent, Qt.Window)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.image_path = image_path
        self.on_tags_updated = on_tags_updated
        self.dragging = False
        self.drag_position = None
        
        # Setup layout
        layout = QVBoxLayout()
        
        # Add title bar
        title_bar = QFrame()
        title_bar.setStyleSheet("background-color: #f0f0f0; border-bottom: 1px solid #ddd;")
        title_bar_layout = QHBoxLayout(title_bar)
        
        # Add title label with filename
        title_label = QLabel(os.path.basename(image_path))
        title_label.setStyleSheet("font-weight: bold; padding: 5px;")
        title_bar_layout.addWidget(title_label)
        
        layout.addWidget(title_bar)
        
        # Add image preview
        image_label = QLabel()
        pixmap = QPixmap(image_path)
        max_preview_size = QSize(500, 400)
        scaled_pixmap = pixmap.scaled(
            max_preview_size, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # Add tag text input
        self.tag_input = QLineEdit()
        self.tag_input.setText(tag_text if tag_text else "")
        self.tag_input.setStyleSheet("background-color: white; padding: 10px;")
        self.tag_input.returnPressed.connect(self.confirm_changes)
        layout.addWidget(self.tag_input)
        
        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.confirm_changes)
        self.confirm_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.confirm_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Position the popup within screen bounds
        if position:
            screen = QApplication.screenAt(position)
            if not screen:
                screen = QApplication.primaryScreen()
            
            screen_geom = screen.availableGeometry()
            popup_size = self.sizeHint()
            
            # Adjust position to keep popup within screen bounds
            x = min(max(position.x(), screen_geom.left()), 
                   screen_geom.right() - popup_size.width())
            y = min(max(position.y(), screen_geom.top()), 
                   screen_geom.bottom() - popup_size.height())
            
            self.move(x, y)
    
    def confirm_changes(self):
        if self.on_tags_updated:
            self.on_tags_updated(self.tag_input.text())
        self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            new_pos = event.globalPos() - self.drag_position
            
            # Keep popup within screen bounds
            screen = QApplication.screenAt(event.globalPos())
            if not screen:
                screen = QApplication.primaryScreen()
            
            screen_geom = screen.availableGeometry()
            popup_geom = self.frameGeometry()
            
            x = min(max(new_pos.x(), screen_geom.left()),
                   screen_geom.right() - popup_geom.width())
            y = min(max(new_pos.y(), screen_geom.top()),
                   screen_geom.bottom() - popup_geom.height())
            
            self.move(x, y)

class ImageGallery(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.cell_size = 150  # Size of each cell in the grid
        self.grid_spacing = 10  # Spacing between cells
        self.drag_selecting = False
        self.selected_cells = set()
        self.last_cell_position = None
        self.image_cells = []
        self.processed_cells = set()  # Track cells processed in current drag
        
        # Double click tracking
        self.last_click_pos = None
        self.last_click_time = 0
        self.double_click_interval = 300  # milliseconds
        self.click_distance_threshold = 10  # pixels
        
        # Sort options
        self.sort_options = [
            "Name (ascending)", "Name (descending)",
            "Modified Date (ascending)", "Modified Date (descending)",
            "Tags (ascending)", "Tags (descending)"
        ]
        self.current_sort = "Name (ascending)"
        
        # UI setup
        self.setWindowTitle("GalleryTags - Image Gallery with Tag Editor")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(self.central_widget)
        
        # Add buttons for folder selection and tag application
        button_layout = QHBoxLayout()
        
        # Add buttons first
        self.open_folder_button = QPushButton("Open Folder (Ctrl+O)")
        self.open_folder_button.clicked.connect(self.open_folder)
        button_layout.addWidget(self.open_folder_button)
        
        self.select_all_button = QPushButton("Select All (Ctrl+A)")
        self.select_all_button.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_button)
        
        self.refresh_button = QPushButton("Refresh Metadata (Ctrl+R)")
        self.refresh_button.clicked.connect(self.refresh_metadata)
        button_layout.addWidget(self.refresh_button)
        
        self.apply_tag_button = QPushButton("Add Tag (Enter)")
        self.apply_tag_button.clicked.connect(self.apply_tag_to_selected)
        button_layout.addWidget(self.apply_tag_button)
        
        # Add export button
        self.export_button = QPushButton("Export (Ctrl+E)")
        self.export_button.clicked.connect(lambda: self.export_lists(True))
        button_layout.addWidget(self.export_button)
        
        # Add sort dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(self.sort_options)
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        button_layout.addWidget(self.sort_combo)
        
        # Add search controls
        self.search_mode = QComboBox()
        self.search_mode.addItems(["AND", "OR"])
        self.search_mode.setFixedWidth(70)
        self.search_mode.currentTextChanged.connect(self.perform_search)
        button_layout.addWidget(self.search_mode)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tags (comma separated)")
        self.search_input.returnPressed.connect(self.perform_search)
        button_layout.addWidget(self.search_input)
        
        # Add keyboard shortcuts
        QShortcut(Qt.CTRL + Qt.Key_O, self, self.open_folder)
        QShortcut(Qt.CTRL + Qt.Key_A, self, self.select_all)
        QShortcut(Qt.CTRL + Qt.Key_R, self, self.refresh_metadata)
        QShortcut(Qt.CTRL + Qt.Key_F, self, self.focus_search)
        QShortcut(Qt.CTRL + Qt.Key_E, self, lambda: self.export_lists(True))
        QShortcut(Qt.CTRL + Qt.SHIFT + Qt.Key_E, self, lambda: self.export_lists(False))
        
        main_layout.addLayout(button_layout)
        
        # Create scroll area for the grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)
        
        # Create a widget to hold the grid
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(self.grid_spacing)
        self.scroll_area.setWidget(self.grid_widget)
        
        # Connect resize event to update grid
        self.resizeTimer = None
        
        # Add loading overlay
        self.loading_overlay = LoadingOverlay(self)
        
        # Initialize with default folder if set
        if APP_CONFIG['default_folder']:
            # Show window first
            self.show()
            self.activateWindow()
            self.raise_()
            QApplication.processEvents()  # Process pending events
            # Then load images
            self.load_images(APP_CONFIG['default_folder'])
    
    def clear_selections(self):
        """Clear all selected cells"""
        self.selected_cells.clear()
        for cell in self.image_cells:
            cell.set_selected(False)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # Use a timer to avoid excessive grid updates during resize
        if self.resizeTimer:
            self.resizeTimer.stop()
        
        self.resizeTimer = QTimer()
        self.resizeTimer.setSingleShot(True)
        self.resizeTimer.timeout.connect(self.delayed_resize_update)
        self.resizeTimer.start(150)
        
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())
    
    def delayed_resize_update(self):
        self.update_grid_layout()
    
    def update_grid_layout(self):
        if not self.image_cells:
            return
            
        # Calculate grid dimensions based on available width
        available_width = self.scroll_area.viewport().width() - 20
        grid_columns = max(1, available_width // (self.cell_size + self.grid_spacing))
        
        # Clear the existing grid
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        
        # Only arrange visible cells
        row, col = 0, 0
        for cell in self.image_cells:
            if cell.isVisible():
                self.grid_layout.addWidget(cell, row, col)
                col += 1
                if col >= grid_columns:
                    col = 0
                    row += 1
    
    def perform_search(self):
        """Filter images based on search tags"""
        search_text = self.search_input.text().strip()
        
        # Hide all cells first
        for cell in self.image_cells:
            cell.hide()
        
        # If search is empty, show all cells
        if not search_text:
            for cell in self.image_cells:
                cell.show()
            self.update_grid_layout()
            return
        
        # Parse search terms and determine search mode
        search_tags = parse_tags(search_text)
        is_and_mode = self.search_mode.currentText() == "AND"
        
        # Filter and show matching cells
        for cell in self.image_cells:
            cell_tags = parse_tags(cell.tag_text)
            
            if is_and_mode:
                # AND mode: all search tags must be present
                visible = all(search_tag in cell_tags for search_tag in search_tags)
            else:
                # OR mode: any search tag must be present
                visible = any(search_tag in cell_tags for search_tag in search_tags)
            
            if visible:
                cell.show()
            else:
                cell.hide()
        
        # Update grid layout after changing visibility
        self.update_grid_layout()
        
        # Keep focus on search input
        self.search_input.setFocus()
    
    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.load_images(folder_path)
    
    def load_images(self, folder_path):
        # Clear existing grid
        self.clear_grid()
        
        # Get all supported image files in the folder
        image_files = []
        for filename in os.listdir(folder_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                image_files.append(os.path.join(folder_path, filename))
        
        if not image_files:
            QMessageBox.information(self, "No Images", 
                f"No supported images found in the selected folder.\nSupported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
            return

        # Sort files by name initially using natural sort
        image_files.sort(key=natural_sort_key)
        
        # Show loading overlay
        self.loading_overlay.show()
        QApplication.processEvents()
        
        # Create cells with progress update
        total_files = len(image_files)
        for i, image_path in enumerate(image_files, 1):
            cell = ImageCell(image_path, self.cell_size)
            self.image_cells.append(cell)
            
            if i % 5 == 0:
                self.loading_overlay.update_progress(i, total_files)
                QApplication.processEvents()
        
        # Apply current sort and update grid
        self.sort_images()
        
        # Hide loading overlay
        self.loading_overlay.hide()
        
        # Activate window to gain focus
        self.activateWindow()
        self.raise_()
    
    def refresh_metadata(self):
        """Re-read metadata for all images in the grid"""
        # Show loading overlay
        self.loading_overlay.show()
        QApplication.processEvents()
        
        total = len(self.image_cells)
        for i, cell in enumerate(self.image_cells, 1):
            cell.tag_text = cell.read_tag_metadata()
            cell.update_background()
            cell.update()
            
            if i % 5 == 0:
                self.loading_overlay.update_progress(i, total)
                QApplication.processEvents()
        
        self.loading_overlay.hide()
    
    def clear_grid(self):
        # Clear selected cells
        self.selected_cells.clear()
        
        # Remove all widgets from the grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear image cells list
        self.image_cells.clear()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_time = event.timestamp()
            current_pos = event.pos()
            
            # Check if this is a double click
            if (self.last_click_pos and self.last_click_time and
                current_time - self.last_click_time <= self.double_click_interval and
                (current_pos - self.last_click_pos).manhattanLength() <= self.click_distance_threshold):
                # Handle as double click
                cell = self.get_cell_at_position(current_pos)
                if cell:
                    # Clear all selections first
                    self.selected_cells.clear()
                    for other_cell in self.image_cells:
                        other_cell.set_selected(False)
                    
                    # Select only the double-clicked cell
                    cell.set_selected(True)
                    self.selected_cells.add(cell)
                    
                    def on_tags_updated(new_tags):
                        if cell.write_tag_metadata(new_tags):
                            cell.tag_text = new_tags
                            cell.update_background()
                            cell.update()
                            # Clear selections after successful update
                            self.clear_selections()
                    
                    popup = ImageDetailsPopup(
                        parent=self,
                        image_path=cell.image_path,
                        tag_text=cell.tag_text,
                        position=self.mapToGlobal(current_pos),
                        on_tags_updated=on_tags_updated
                    )
                    popup.show()
                
                # Reset click tracking
                self.last_click_pos = None
                self.last_click_time = 0
                
            else:
                # Handle as single click - start drag select
                self.drag_selecting = True
                self.processed_cells.clear()
                self.process_mouse_at_position(current_pos)
                
                # Update click tracking
                self.last_click_pos = current_pos
                self.last_click_time = current_time
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_selecting = False
            self.last_cell_position = None
            self.processed_cells.clear()  # Clear processed cells when done
    
    def mouseMoveEvent(self, event):
        if self.drag_selecting:
            self.process_mouse_at_position(event.pos())
    
    def process_mouse_at_position(self, pos):
        cell = self.get_cell_at_position(pos)
        if cell and cell not in self.processed_cells:  # Only process unprocessed cells
            # Don't repeat actions on the same cell position
            cell_pos = (cell.pos().x(), cell.pos().y())
            if cell_pos == self.last_cell_position:
                return
            
            self.last_cell_position = cell_pos
            self.processed_cells.add(cell)  # Mark cell as processed
            
            # Toggle selection
            cell.toggle_selection()
            
            # Update selected cells set
            if cell.selected:
                self.selected_cells.add(cell)
            else:
                self.selected_cells.discard(cell)
    
    def get_cell_at_position(self, pos):
        # Convert the position to the grid widget's coordinate system
        scroll_pos = self.scroll_area.mapFromParent(pos)
        grid_pos = self.grid_widget.mapFrom(self.scroll_area, scroll_pos)
        
        # Check each cell to see if it contains the point
        for cell in self.image_cells:
            cell_rect = QRect(cell.pos(), cell.size())
            if cell_rect.contains(grid_pos):
                return cell
        
        return None
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear_selections()
        # Handle Enter as before
        elif (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter) and \
           not self.search_input.hasFocus():
            self.apply_tag_to_selected()
        else:
            super().keyPressEvent(event)
    
    def apply_tag_to_selected(self):
        if not self.selected_cells:
            QMessageBox.information(self, "No Selection", "Please select at least one image first.")
            return
        
        # Create custom input dialog with styled input
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Tag")
        
        layout = QVBoxLayout()
        
        # Create styled input
        input_field = QLineEdit()
        input_field.setStyleSheet("background-color: white; padding: 10px;")
        layout.addWidget(input_field)
        
        # Add buttons
        button_box = QHBoxLayout()
        ok_button = QPushButton("Confirm")
        cancel_button = QPushButton("Cancel")
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        layout.addLayout(button_box)
        
        dialog.setLayout(layout)
        
        # Connect buttons
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        input_field.returnPressed.connect(dialog.accept)
        
        # Show dialog and handle result
        if dialog.exec_() == QDialog.Accepted:
            tag_text = input_field.text()
            if tag_text:
                success_count = 0
                
                for cell in self.selected_cells:
                    current_tags = cell.tag_text
                    new_tags = f"{current_tags}, {tag_text}" if current_tags else tag_text
                    
                    if cell.write_tag_metadata(new_tags):
                        success_count += 1
                
                # Clear selections after successful operation
                self.clear_selections()
                
                QMessageBox.information(
                    self, 
                    "Tags Applied", 
                    f"Successfully applied tags to {success_count} of {len(self.selected_cells)} images."
                )
    
    def select_all(self):
        """Toggle selection of all images"""
        # Check if all cells are currently selected
        all_selected = len(self.selected_cells) == len(self.image_cells)
        
        # If all selected, deselect all. Otherwise, select all.
        for cell in self.image_cells:
            cell.set_selected(not all_selected)
            if not all_selected:
                self.selected_cells.add(cell)
            
        if all_selected:
            self.selected_cells.clear()
    
    def on_sort_changed(self, option):
        self.current_sort = option
        self.sort_images()
    
    def sort_images(self):
        """Sort images based on current sort option"""
        if not self.image_cells:
            return
            
        # Remember selected paths before sorting
        selected_paths = {cell.image_path for cell in self.selected_cells}
        
        # Sort cells based on current option
        if self.current_sort.startswith("Name"):
            self.image_cells.sort(
                key=lambda x: natural_sort_key(x.image_path),
                reverse=self.current_sort.endswith("(descending)")
            )
        elif self.current_sort.startswith("Modified Date"):
            self.image_cells.sort(
                key=lambda x: os.path.getmtime(x.image_path),
                reverse=self.current_sort.endswith("(descending)")
            )
        elif self.current_sort.startswith("Tags"):
            # Split into tagged and untagged groups
            tagged = [x for x in self.image_cells if x.tag_text]
            untagged = [x for x in self.image_cells if not x.tag_text]
            
            # Sort tagged cells by tag text, maintaining ascending/descending order
            reverse_order = self.current_sort.endswith("(descending)")
            tagged.sort(key=lambda x: x.tag_text.lower(), reverse=reverse_order)
            
            # Combine with untagged cells always at end
            self.image_cells = tagged + untagged

        # Update grid layout
        row, col = 0, 0
        grid_columns = max(1, self.scroll_area.viewport().width() - 20) // (self.cell_size + self.grid_spacing)
        
        # Clear and rebuild grid
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        
        for cell in self.image_cells:
            self.grid_layout.addWidget(cell, row, col)
            cell.set_selected(cell.image_path in selected_paths)
            col += 1
            if col >= grid_columns:
                col = 0
                row += 1

    def export_lists(self, skip_refresh):
        """Export lists based on EXPORT_PATHS configuration"""
        if not self.image_cells:
            QMessageBox.information(self, "No Images", "No images loaded to export.")
            return

        # Refresh metadata if needed
        if not skip_refresh:
            self.loading_overlay.show()
            QApplication.processEvents()
            
            total = len(self.image_cells)
            for i, cell in enumerate(self.image_cells, 1):
                cell.tag_text = cell.read_tag_metadata()
                if i % 5 == 0:
                    self.loading_overlay.update_progress(i, total)
                    QApplication.processEvents()
            
            self.loading_overlay.hide()

        # Get group size from config
        group_size = EXPORT_CONFIG.get('group_by', 0)

        # Process each export path
        for file_path, tags_str in EXPORT_PATHS.items():
            try:
                # Determine search mode and clean tags string
                tags_str = tags_str.strip()
                is_or_mode = tags_str.startswith('|')
                # Remove prefix if exists
                if tags_str.startswith('|') or tags_str.startswith('&'):
                    tags_str = tags_str[1:].strip()
                
                # Parse the tags using helper function
                required_tags = parse_tags(tags_str)
        
                # Filter images based on tags
                matched_images = []
                for cell in self.image_cells:
                    cell_tags = parse_tags(cell.tag_text)
                    
                    if is_or_mode:
                        # OR mode: any required tag must be present
                        if any(tag in cell_tags for tag in required_tags):
                            matched_images.append(cell.image_path)
                    else:
                        # AND mode (default): all required tags must be present
                        if all(tag in cell_tags for tag in required_tags):
                            matched_images.append(cell.image_path)

                # Generate export content
                content = EXPORT_CONFIG['heading'] + '\n'
                
                # Get base directory of export file for path calculations
                export_dir = os.path.dirname(os.path.abspath(file_path))
                
                # Process images with grouping
                for i, img_path in enumerate(matched_images, 1):
                    # Extract components
                    filename = os.path.basename(img_path)
                    filename_no_ext = os.path.splitext(filename)[0]
                    file_ext = os.path.splitext(filename)[1][1:]  # Remove dot
                    full_filepath = os.path.dirname(img_path)
                    
                    # Calculate relative path
                    try:
                        rel_path = os.path.relpath(full_filepath, export_dir)
                        if rel_path == '.':
                            short_path = '.'
                        else:
                            short_path = './' + rel_path.replace(os.path.sep, '/')
                    except ValueError:
                        # If relpath fails (different drives etc), use full path
                        short_path = full_filepath
                    
                    # Format item string
                    item = EXPORT_CONFIG['item_format']
                    item = item.replace('$fn', filename_no_ext)
                    item = item.replace('$fe', file_ext)
                    item = item.replace('$fp', short_path)
                    item = item.replace('$ffp', full_filepath)
                    
                    content += item
                    
                    # Add extra newline after each group
                    if group_size > 0 and i % group_size == 0 and i < len(matched_images):
                        content += '\n'

                # Write to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            except Exception as e:
                print(f"Error exporting to {file_path}: {e}")
                QMessageBox.warning(self, "Export Error", 
                    f"Error exporting to {file_path}:\n{str(e)}")

        QMessageBox.information(self, "Export Complete", 
            f"Successfully exported lists to {len(EXPORT_PATHS)} file(s).")

    def focus_search(self):
        """Focus the search input box"""
        self.search_input.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_exiftool()
    
    window = ImageGallery()
    window.show()
    sys.exit(app.exec_())
