from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView)
import json
import os

class ExportConfigDialog(QDialog):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("Export Configuration")
        self.setModal(True)
        self.resize(600, 400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Export File Path", "Tag Query"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Button row
        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.del_row_btn = QPushButton("Delete Selected")
        self.cancel_btn = QPushButton("Cancel")
        self.export_btn = QPushButton("Export")
        
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.del_row_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)
        
        # Connect signals
        self.add_row_btn.clicked.connect(self.add_row)
        self.del_row_btn.clicked.connect(self.delete_selected)
        self.cancel_btn.clicked.connect(self.reject)
        self.export_btn.clicked.connect(self.validate_and_accept)
        
        # Load existing config
        self.load_config()
    
    def load_config(self):
        """Load existing config from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Populate table
                for filepath, query in config.items():
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(filepath))
                    self.table.setItem(row, 1, QTableWidgetItem(query))
            except Exception as e:
                QMessageBox.warning(self, "Load Error", f"Error loading config: {str(e)}")
    
    def add_row(self):
        """Add a new empty row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
    
    def delete_selected(self):
        """Delete selected rows"""
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
    
    def validate_and_accept(self):
        """Validate inputs and save config"""
        config = {}
        
        for row in range(self.table.rowCount()):
            filepath = self.table.item(row, 0).text().strip()
            query = self.table.item(row, 1).text().strip()
            
            if filepath and query:
                # Validate filepath
                if not filepath.endswith('.md'):
                    QMessageBox.warning(self, "Validation Error", 
                        f"Export file path must end with .md (row {row + 1})")
                    return
                
                # Check for duplicate filepaths
                if filepath in config:
                    QMessageBox.warning(self, "Validation Error", 
                        f"Duplicate export file path: {filepath}")
                    return
                
                config[filepath] = query
            elif filepath or query:
                # One field is empty but not both
                QMessageBox.warning(self, "Validation Error", 
                    f"Both filepath and query must be specified (row {row + 1})")
                return
        
        # Save config
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving config: {str(e)}")
            return
        
        self.accept()