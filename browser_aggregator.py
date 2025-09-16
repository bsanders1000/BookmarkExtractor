#!/usr/bin/env python3
"""
Browser Bookmark Aggregator - Main application entry point
"""
import sys
import logging
import argparse
from pathlib import Path

from credential_manager import CredentialManager
from gui.main_window import launch_gui

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bookmark_aggregator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Browser Bookmark Aggregator')
    parser.add_argument('--no-gui', action='store_true', help='Run in console mode without GUI')
    args = parser.parse_args()
    
    # App data directory
    app_dir = Path.home() / '.bookmark_aggregator'
    app_dir.mkdir(exist_ok=True)
    
    # Create credential manager instance (but don't initialize yet)
    cred_manager = CredentialManager(app_dir / 'credentials.enc')
    
    # Handle --no-gui flag
    if args.no_gui:
        print("Bookmark extraction has been moved to the GUI.")
        print("Please run without --no-gui to access extraction functionality.")
        return 0
    
    # Launch GUI immediately with empty bookmarks
    logger.info("Launching GUI...")
    launch_gui({}, cred_manager)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())