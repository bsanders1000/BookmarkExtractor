#!/usr/bin/env python3
"""
Browser Bookmark Aggregator - Main application entry point
"""
import sys
import logging
import argparse
from pathlib import Path
from getpass import getpass

from browser_detector import detect_browsers
from credential_manager import CredentialManager
from bookmark_extractor import extract_bookmarks
from bookmark_categorizer import categorize_bookmarks
from link_validator import validate_links
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
    parser.add_argument('--validate-links', action='store_true', help='Validate all bookmark links')
    parser.add_argument('--export', type=str, help='Export bookmarks to specified file')
    args = parser.parse_args()
    
    # App data directory
    app_dir = Path.home() / '.bookmark_aggregator'
    app_dir.mkdir(exist_ok=True)
    
    # Initialize credential manager
    cred_manager = CredentialManager(app_dir / 'credentials.enc')
    master_password = getpass("Enter master password (or press Enter to create one): ")
    cred_manager.initialize(master_password)
    
    # Detect installed browsers
    logger.info("Scanning for browser installations...")
    installed_browsers = detect_browsers()
    logger.info(f"Found {len(installed_browsers)} browser installations")
    
    # Extract bookmarks from each browser
    all_bookmarks = []
    for browser in installed_browsers:
        logger.info(f"Extracting bookmarks from {browser.name} {browser.version}")
        if browser.requires_credentials and not cred_manager.has_credentials(browser.id):
            username = input(f"Enter username for {browser.name}: ")
            password = getpass(f"Enter password for {browser.name}: ")
            cred_manager.store_credentials(browser.id, username, password)
        
        credentials = cred_manager.get_credentials(browser.id) if browser.requires_credentials else None
        bookmarks = extract_bookmarks(browser, credentials)
        all_bookmarks.extend(bookmarks)
    
    logger.info(f"Extracted {len(all_bookmarks)} bookmarks in total")
    
    # Categorize bookmarks
    logger.info("Categorizing bookmarks...")
    categorized_bookmarks = categorize_bookmarks(all_bookmarks)
    
    # Validate links if requested
    if args.validate_links:
        logger.info("Validating bookmark links...")
        validate_links(categorized_bookmarks)
    
    # Export if requested
    if args.export:
        from bookmark_exporter import export_bookmarks
        export_bookmarks(categorized_bookmarks, args.export)
        logger.info(f"Bookmarks exported to {args.export}")
    
    # Launch GUI unless no-gui is specified
    if not args.no_gui:
        logger.info("Launching GUI...")
        launch_gui(categorized_bookmarks, cred_manager)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())