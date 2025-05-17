from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

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
