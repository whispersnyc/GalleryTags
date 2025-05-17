from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFrame
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QSize
import os

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
            from PyQt5.QtWidgets import QApplication
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
            from PyQt5.QtWidgets import QApplication
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
