#!/usr/bin/env python3
"""
Settings Dialog - GUI for application settings
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QLabel, QTabWidget, QWidget,
    QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt

from settings_manager import SettingsManager

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, parent=None, *, settings_manager: SettingsManager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # Tabs
        self.tabs = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout()
        
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        general_layout.addRow("OpenAI API Key:", self.openai_key_edit)
        
        self.enable_cache_check = QCheckBox()
        general_layout.addRow("Enable Page Cache:", self.enable_cache_check)
        
        general_tab.setLayout(general_layout)
        self.tabs.addTab(general_tab, "General")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def load_settings(self):
        """Load current settings into UI"""
        self.openai_key_edit.setText(self.settings_manager.get("openai_api_key", ""))
        
        cache_settings = self.settings_manager.get("cache_settings", {})
        self.enable_cache_check.setChecked(cache_settings.get("enable_page_cache", True))
        
    def save_settings(self):
        """Save settings from UI"""
        try:
            self.settings_manager.set("openai_api_key", self.openai_key_edit.text())
            
            cache_settings = self.settings_manager.get("cache_settings", {})
            cache_settings["enable_page_cache"] = self.enable_cache_check.isChecked()
            self.settings_manager.set("cache_settings", cache_settings)
            
            if self.settings_manager.save():
                QMessageBox.information(self, "Success", "Settings saved successfully")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to save settings")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving settings: {e}")
            logger.error(f"Error saving settings: {e}")