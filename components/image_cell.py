from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap, QImage
from PyQt5.QtCore import Qt, QRect
import os

from core.metadata import get_metadata_field, read_tag_metadata, write_tag_metadata, get_short_path_name

class ImageCell(QWidget):
    def __init__(self, image_path, cell_size, cache_manager=None, parent=None):
        super().__init__(parent)
        self.image_path = os.path.normpath(image_path)  # Normalize path for multiplatform support
        self.short_path = None  # Will be set when needed
        self.cell_size = cell_size
        self.cache_manager = cache_manager
        self.selected = False
        
        # Try to get tag from cache first
        cached_tags = None
        if self.cache_manager:
            cached_tags = self.cache_manager.get_cached_metadata(self.image_path)
        
        if cached_tags is not None:
            self.tag_text = cached_tags
            print(f"[Cache] Using cached tags for {os.path.basename(self.image_path)}")
        else:
            self.tag_text = self.read_tag_metadata()
            # Update cache with the new tag data
            if self.cache_manager:
                self.cache_manager.update_cache(self.image_path, self.tag_text)
                
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
        if not self.short_path:
            import sys
            if sys.platform == "win32" and any(ord(c) > 127 for c in self.image_path):
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
        """Read tag metadata from the image file"""
        return read_tag_metadata(self.image_path, self.get_exiftool_path())

    def write_tag_metadata(self, tag_text):
        """Write tag metadata to the image file"""
        success = write_tag_metadata(self.image_path, tag_text, self.get_exiftool_path())
        if success:
            self.tag_text = tag_text
            # Update cache with the new tag data
            if hasattr(self, 'cache_manager') and self.cache_manager:
                self.cache_manager.update_cache(self.image_path, tag_text)
                print(f"[Cache] Updated cache for {os.path.basename(self.image_path)}")
            self.update_background()
            self.update()
        return success
    
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
        from PyQt5.QtWidgets import QMenu, QMessageBox
        
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
                        # Update cache with the new tag data
                        if hasattr(cell, 'cache_manager') and cell.cache_manager:
                            cell.cache_manager.update_cache(cell.image_path, new_tags)
                            print(f"[Cache] Updated cache for {os.path.basename(cell.image_path)}")
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
                # Update cache with the new tag data
                if hasattr(self, 'cache_manager') and self.cache_manager:
                    self.cache_manager.update_cache(self.image_path, new_tags)
                    print(f"[Cache] Updated cache for {os.path.basename(self.image_path)}")
                self.update_background()
                self.update()
        except Exception as e:
            print(f"Error refreshing tags for {self.image_path}: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Refresh Error",
                f"Error refreshing tags for {os.path.basename(self.image_path)}:\n{str(e)}"
            )
