from PyQt5.QtWidgets import (QMainWindow, QWidget, QGridLayout, 
                            QLabel, QScrollArea, QInputDialog, QMessageBox, 
                            QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                            QShortcut, QComboBox, QDialog, QFrame, QMenu)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QSize, QRect, QPoint, QTimer
import os, subprocess, sys

from components.image_cell import ImageCell
from components.loading import LoadingOverlay
from components.image_popup import ImageDetailsPopup
from core.cache import CacheManager
from core.metadata import get_metadata_field
from config import APP_CONFIG, EXPORT_PATHS, EXPORT_CONFIG
from utils.helpers import natural_sort_key, parse_tags

class ImageGallery(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize cache manager
        self.cache_manager = CacheManager()
        
        # Configuration
        self.cell_size = 150  # Size of each cell in the grid
        self.grid_spacing = 10  # Spacing between cells
        self.drag_selecting = False
        self.selected_cells = set()
        self.last_cell_position = None
        self.image_cells = []
        self.processed_cells = set()  # Track cells processed in current drag
        self.current_folder = None  # Track current folder for cache purposes
        
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
        if hasattr(APP_CONFIG, 'default_folder') and APP_CONFIG['default_folder']:
            # Show window first
            self.show()
            self.activateWindow()
            self.raise_()
            QApplication.processEvents()  # Process pending events
            # Then load images
            self.load_images(APP_CONFIG['default_folder'])
        
        # Get reference to QApplication instance for aboutToQuit connection
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.save_cache_on_exit)
    
    def save_cache_on_exit(self):
        """Save cache data when application is closing"""
        print("[Cache] Saving cache before exit")
        self.cache_manager.save_cache()
    
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
        from core.metadata import SUPPORTED_EXTENSIONS
        
        self.current_folder = os.path.normpath(folder_path)
        print(f"[Cache] Loading images from: {self.current_folder}")
        
        # Clear existing grid
        self.clear_grid()
        
        # Get all supported image files in the folder
        image_files = []
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    image_files.append(filepath)
        
        if not image_files:
            QMessageBox.information(self, "No Images", 
                f"No supported images found in the selected folder.\nSupported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
            return

        # Get list of cached files in this directory
        cached_files = set(self.cache_manager.get_cached_files_in_dir(self.current_folder))
        print(f"[Cache] Found {len(cached_files)} cached files in this directory")
        
        # Sort files by name initially using natural sort
        image_files.sort(key=natural_sort_key)
        
        # Show loading overlay
        self.loading_overlay.show()
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Create cells with progress update
        total_files = len(image_files)
        for i, image_path in enumerate(image_files, 1):
            norm_path = os.path.normpath(image_path)
            
            # Create cell with cache manager
            cell = ImageCell(image_path, self.cell_size, self.cache_manager)
            self.image_cells.append(cell)
            
            if i % 5 == 0:
                self.loading_overlay.update_progress(i, total_files)
                QApplication.processEvents()
        
        # Apply current sort and update grid
        self.sort_images()
        
        # Hide loading overlay
        self.loading_overlay.hide()
        
        # Clean cache of files that no longer exist
        self.cache_manager.clean_missing_files()
        
        # Save updated cache
        self.cache_manager.save_cache()
        
        # Activate window to gain focus
        self.activateWindow()
        self.raise_()
    
    def refresh_metadata(self):
        """Re-read metadata for all images in the grid"""
        # Show loading overlay
        self.loading_overlay.show()
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        total = len(self.image_cells)
        for i, cell in enumerate(self.image_cells, 1):
            cell.tag_text = cell.read_tag_metadata()
            # Update cache with the new tag data
            self.cache_manager.update_cache(cell.image_path, cell.tag_text)
            cell.update_background()
            cell.update()
            
            if i % 5 == 0:
                self.loading_overlay.update_progress(i, total)
                QApplication.processEvents()
        
        # Save updated cache after full refresh
        self.cache_manager.save_cache()
        print("[Cache] Cache updated after full metadata refresh")
        
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

    def export_lists(self, skip_refresh=True):
        """Export lists based on EXPORT_PATHS configuration"""
        if not self.image_cells:
            QMessageBox.information(self, "No Images", "No images loaded to export.")
            return

        # Refresh metadata if needed
        if not skip_refresh:
            self.loading_overlay.show()
            from PyQt5.QtWidgets import QApplication
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
