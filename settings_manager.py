#!/usr/bin/env python3
"""
Settings Manager - Manages application settings
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages application settings storage and retrieval"""
    
    def __init__(self, settings_path: Optional[Path] = None):
        if settings_path is None:
            settings_path = Path.home() / ".bookmark_aggregator" / "settings.json"
        self.settings_path = settings_path
        self.settings: Dict[str, Any] = {}
        self.load()
        
    def load(self) -> bool:
        """Load settings from file"""
        try:
            if not self.settings_path.exists():
                logger.info("Settings file does not exist, using defaults")
                self.settings = self._get_default_settings()
                return True
                
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
                
            # Merge with defaults for any missing keys
            defaults = self._get_default_settings()
            for key, value in defaults.items():
                if key not in self.settings:
                    self.settings[key] = value
                    
            logger.info(f"Loaded settings from {self.settings_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self.settings = self._get_default_settings()
            return False
            
    def save(self) -> bool:
        """Save settings to file"""
        try:
            # Ensure directory exists
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved settings to {self.settings_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self.settings[key] = value
        
    def get_all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self.settings.copy()
        
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings"""
        self.settings.update(updates)
        
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            "openai_api_key": "",
            "analyzer_settings": {},
            "ui_settings": {
                "window_geometry": None,
                "splitter_state": None
            },
            "cache_settings": {
                "enable_page_cache": True,
                "cache_expiry_days": 7
            }
        }