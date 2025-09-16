#!/usr/bin/env python3
"""
Analyzer Settings Dialog - GUI for configuring analyzers
"""
import logging
from typing import Dict, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QLabel, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QMessageBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt

from analyzers.registry import list_analyzer_names, get_analyzer_by_name
from config.analyzers_config import load_config, save_config

logger = logging.getLogger(__name__)

class AnalyzerSettingsDialog(QDialog):
    """Dialog for configuring analyzer settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analyzer Settings")
        self.setModal(True)
        self.resize(600, 500)
        
        self.config = load_config()
        self.widgets = {}
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # Analyzer selection
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Analyzer:"))
        
        self.analyzer_combo = QComboBox()
        analyzers = list_analyzer_names()
        self.analyzer_combo.addItems(analyzers)
        self.analyzer_combo.currentTextChanged.connect(self.on_analyzer_changed)
        selection_layout.addWidget(self.analyzer_combo)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        # Settings area
        self.scroll_area = QScrollArea()
        self.settings_widget = QWidget()
        self.settings_layout = QFormLayout()
        self.settings_widget.setLayout(self.settings_layout)
        self.scroll_area.setWidget(self.settings_widget)
        self.scroll_area.setWidgetResizable(True)
        
        layout.addWidget(self.scroll_area)
        
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
        
        # Load initial analyzer
        if analyzers:
            self.on_analyzer_changed(analyzers[0])
            
    def on_analyzer_changed(self, analyzer_name: str):
        """Handle analyzer selection change"""
        try:
            # Clear existing widgets
            while self.settings_layout.count():
                child = self.settings_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.widgets.clear()
            
            if not analyzer_name:
                return
                
            # Get analyzer and its settings schema
            analyzer = get_analyzer_by_name(analyzer_name)
            if not analyzer:
                return
                
            schema = analyzer.get_settings_schema()
            current_settings = self.config.get(analyzer_name, {})
            
            # Create widgets for each setting
            for setting_name, setting_info in schema.items():
                setting_type = setting_info.get("type", "string")
                label = setting_info.get("label", setting_name)
                description = setting_info.get("description", "")
                default = setting_info.get("default")
                current_value = current_settings.get(setting_name, default)
                
                # Create appropriate widget
                if setting_type == "boolean":
                    widget = QCheckBox()
                    widget.setChecked(bool(current_value))
                    
                elif setting_type == "integer":
                    widget = QSpinBox()
                    widget.setMinimum(setting_info.get("min", 0))
                    widget.setMaximum(setting_info.get("max", 999999))
                    widget.setValue(int(current_value) if current_value is not None else 0)
                    
                elif setting_type == "float":
                    widget = QDoubleSpinBox()
                    widget.setMinimum(setting_info.get("min", 0.0))
                    widget.setMaximum(setting_info.get("max", 999999.0))
                    widget.setDecimals(2)
                    widget.setValue(float(current_value) if current_value is not None else 0.0)
                    
                elif setting_type == "password":
                    widget = QLineEdit()
                    widget.setEchoMode(QLineEdit.Password)
                    widget.setText(str(current_value) if current_value else "")
                    
                else:  # string
                    widget = QLineEdit()
                    widget.setText(str(current_value) if current_value else "")
                
                self.widgets[setting_name] = widget
                
                # Add to layout with description
                label_widget = QLabel(label)
                if description:
                    label_widget.setToolTip(description)
                    
                self.settings_layout.addRow(label_widget, widget)
                
        except Exception as e:
            logger.error(f"Error loading analyzer settings: {e}")
            QMessageBox.warning(self, "Error", f"Error loading analyzer settings: {e}")
            
    def save_settings(self):
        """Save analyzer settings"""
        try:
            analyzer_name = self.analyzer_combo.currentText()
            if not analyzer_name:
                return
                
            # Collect values from widgets
            settings = {}
            for setting_name, widget in self.widgets.items():
                if isinstance(widget, QCheckBox):
                    settings[setting_name] = widget.isChecked()
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    settings[setting_name] = widget.value()
                elif isinstance(widget, QLineEdit):
                    settings[setting_name] = widget.text()
                    
            # Update config
            self.config[analyzer_name] = settings
            
            # Save config
            if save_config(self.config):
                QMessageBox.information(self, "Success", "Analyzer settings saved successfully")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to save analyzer settings")
                
        except Exception as e:
            logger.error(f"Error saving analyzer settings: {e}")
            QMessageBox.critical(self, "Error", f"Error saving analyzer settings: {e}")