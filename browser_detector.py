#!/usr/bin/env python3
"""
Browser detection functionality
"""
import os
import sys
import logging
import winreg
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class BrowserInfo:
    """Represents a detected browser installation"""
    id: str
    name: str
    version: str
    path: Path
    profile_path: Path
    requires_credentials: bool = False
    
def detect_browsers() -> List[BrowserInfo]:
    """
    Detect installed browsers on the system
    
    Returns:
        List[BrowserInfo]: List of detected browser installations
    """
    if sys.platform == 'win32':
        return _detect_browsers_windows()
    elif sys.platform == 'darwin':
        return _detect_browsers_macos()
    elif sys.platform.startswith('linux'):
        return _detect_browsers_linux()
    else:
        logger.warning(f"Unsupported platform: {sys.platform}")
        return []

def _detect_browsers_windows() -> List[BrowserInfo]:
    """Detect browsers on Windows"""
    browsers = []
    
    # Check for Chrome
    try:
        chrome_path = _get_windows_app_path("chrome.exe")
        if chrome_path:
            profile_path = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
            if profile_path.exists():
                version = _get_chrome_version(chrome_path)
                browsers.append(BrowserInfo(
                    id="chrome",
                    name="Google Chrome",
                    version=version,
                    path=chrome_path,
                    profile_path=profile_path
                ))
    except Exception as e:
        logger.error(f"Error detecting Chrome: {e}")
    
    # Check for Firefox
    try:
        firefox_path = _get_windows_app_path("firefox.exe")
        if firefox_path:
            profile_path = Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
            if profile_path.exists():
                version = _get_firefox_version(firefox_path)
                browsers.append(BrowserInfo(
                    id="firefox",
                    name="Mozilla Firefox",
                    version=version,
                    path=firefox_path,
                    profile_path=profile_path
                ))
    except Exception as e:
        logger.error(f"Error detecting Firefox: {e}")
    
    # Check for Edge
    try:
        edge_path = _get_windows_app_path("msedge.exe")
        if edge_path:
            profile_path = Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"
            if profile_path.exists():
                version = _get_edge_version(edge_path)
                browsers.append(BrowserInfo(
                    id="edge",
                    name="Microsoft Edge",
                    version=version,
                    path=edge_path,
                    profile_path=profile_path
                ))
    except Exception as e:
        logger.error(f"Error detecting Edge: {e}")
    
    # Add more browsers as needed
    
    return browsers

def _detect_browsers_macos() -> List[BrowserInfo]:
    """Detect browsers on macOS"""
    browsers = []
    applications_dir = Path("/Applications")
    
    # Check for Chrome
    chrome_path = applications_dir / "Google Chrome.app"
    if chrome_path.exists():
        profile_path = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
        version = _get_macos_app_version(chrome_path)
        browsers.append(BrowserInfo(
            id="chrome",
            name="Google Chrome",
            version=version,
            path=chrome_path,
            profile_path=profile_path
        ))
    
    # Check for Firefox
    firefox_path = applications_dir / "Firefox.app"
    if firefox_path.exists():
        profile_path = Path.home() / "Library" / "Application Support" / "Firefox" / "Profiles"
        version = _get_macos_app_version(firefox_path)
        browsers.append(BrowserInfo(
            id="firefox",
            name="Mozilla Firefox",
            version=version,
            path=firefox_path,
            profile_path=profile_path
        ))
    
    # Check for Safari
    safari_path = applications_dir / "Safari.app"
    if safari_path.exists():
        profile_path = Path.home() / "Library" / "Safari"
        version = _get_macos_app_version(safari_path)
        browsers.append(BrowserInfo(
            id="safari",
            name="Safari",
            version=version,
            path=safari_path,
            profile_path=profile_path
        ))
    
    # Add more browsers as needed
    
    return browsers

def _detect_browsers_linux() -> List[BrowserInfo]:
    """Detect browsers on Linux"""
    browsers = []
    
    # Check for Chrome
    chrome_paths = [
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/google-chrome-stable")
    ]
    for chrome_path in chrome_paths:
        if chrome_path.exists():
            profile_path = Path.home() / ".config" / "google-chrome"
            version = _get_linux_app_version(chrome_path)
            browsers.append(BrowserInfo(
                id="chrome",
                name="Google Chrome",
                version=version,
                path=chrome_path,
                profile_path=profile_path
            ))
            break
    
    # Check for Firefox
    firefox_path = Path("/usr/bin/firefox")
    if firefox_path.exists():
        profile_path = Path.home() / ".mozilla" / "firefox"
        version = _get_linux_app_version(firefox_path)
        browsers.append(BrowserInfo(
            id="firefox",
            name="Mozilla Firefox",
            version=version,
            path=firefox_path,
            profile_path=profile_path
        ))
    
    # Add more browsers as needed
    
    return browsers

def _get_windows_app_path(exe_name: str) -> Optional[Path]:
    """Get application path from Windows registry"""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\\" + exe_name) as key:
            path, _ = winreg.QueryValueEx(key, "")
            return Path(path) if path else None
    except WindowsError:
        return None

def _get_chrome_version(path: Path) -> str:
    """Get Chrome version"""
    # Implementation would depend on extracting version info from the executable
    return "Unknown"

def _get_firefox_version(path: Path) -> str:
    """Get Firefox version"""
    # Implementation would depend on extracting version info from the executable
    return "Unknown"

def _get_edge_version(path: Path) -> str:
    """Get Edge version"""
    # Implementation would depend on extracting version info from the executable
    return "Unknown"

def _get_macos_app_version(path: Path) -> str:
    """Get macOS application version"""
    # Implementation would use macOS-specific APIs
    return "Unknown"

def _get_linux_app_version(path: Path) -> str:
    """Get Linux application version"""
    # Implementation would depend on the specific application
    return "Unknown"