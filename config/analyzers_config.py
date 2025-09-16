#!/usr/bin/env python3
"""
Analyzer Configuration - Manages analyzer configuration
"""
import logging
from pathlib import Path
from typing import Dict, Any

from settings_manager import SettingsManager

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load analyzer configuration"""
    settings_manager = SettingsManager()
    return settings_manager.get("analyzer_settings", {})

def save_config(config: Dict[str, Any]) -> bool:
    """Save analyzer configuration"""
    try:
        settings_manager = SettingsManager()
        settings_manager.set("analyzer_settings", config)
        return settings_manager.save()
    except Exception as e:
        logger.error(f"Failed to save analyzer config: {e}")
        return False