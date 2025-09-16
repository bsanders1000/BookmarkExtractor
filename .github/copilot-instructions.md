# Browser Bookmark Aggregator

Browser Bookmark Aggregator is a Python PyQt5 desktop application with CLI support that extracts, analyzes, and manages bookmarks from multiple browsers (Chrome, Firefox, Edge, Safari) with AI-powered topic and keyword extraction using Google Gemini.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap and Dependencies
- **Install Python dependencies**: `pip install -r requirements.txt` -- installs PyQt5, google-generativeai, cryptography, requests, beautifulsoup4 (takes ~30 seconds)
- **Install development tools**: `pip install flake8 pytest` -- for linting and testing (takes ~15 seconds)
- **Extended ML dependencies**: `pip install -r requirements_Version2.txt` -- **WARNING: Network timeouts common. May fail due to firewall limitations. Contains BERTopic, sentence-transformers, scikit-learn, etc.**

### Running the Application
- **GUI mode**: `python3 browser_aggregator.py` -- launches PyQt5 GUI (requires X11/display)
- **Console mode**: `python3 browser_aggregator.py --no-gui` -- runs without GUI, extracts bookmarks only
- **Export bookmarks**: `python3 browser_aggregator.py --no-gui --export output.json`
- **Validate links**: `python3 browser_aggregator.py --no-gui --validate-links`
- **Help**: `python3 browser_aggregator.py --help`

### Build and Test Commands
- **Startup time**: ~0.5 seconds for module import
- **Browser detection**: ~0.04 seconds (finds Chrome, Firefox automatically)
- **Link validation**: ~0.35 seconds for 3 URLs
- **Categorization**: ~0.17 seconds for 5 bookmarks
- **Linting**: `python3 -m flake8 browser_aggregator.py --max-line-length=100` -- takes ~0.3 seconds, currently shows whitespace/formatting issues

### Validation Scenarios
**ALWAYS test these core workflows after making changes:**

1. **Basic Functionality Test**:
```bash
python3 -c "
from bookmark_extractor import Bookmark
from bookmark_categorizer import categorize_bookmarks
from link_validator import validate_links

# Test bookmark creation and categorization
bookmarks = [Bookmark('https://github.com', 'GitHub', '', '')]
categorized = categorize_bookmarks(bookmarks)
validate_links(categorized)
print('✓ Core functionality verified')
"
```

2. **Component Integration Test**:
```bash
python3 -c "
from browser_detector import detect_browsers
from analyzers.registry import list_analyzer_names
from analyzers.gemini_topic_analyzer import GeminiTopicAnalyzer

browsers = detect_browsers()
analyzers = list_analyzer_names()
gemini = GeminiTopicAnalyzer()

print(f'✓ Found {len(browsers)} browsers')
print(f'✓ Found {len(analyzers)} analyzers')
print(f'✓ Gemini analyzer configured')
"
```

3. **Manual Application Test** (requires master password input):
```bash
echo '' | python3 browser_aggregator.py --no-gui
```

## Application Architecture

### Core Modules
- **browser_aggregator.py** -- Main entry point, CLI argument parsing, orchestration
- **browser_detector.py** -- Detects installed browsers (Chrome, Firefox, Edge, Safari)
- **bookmark_extractor.py** -- Extracts bookmarks from browser databases/files
- **bookmark_categorizer.py** -- Categorizes bookmarks into 12 predefined categories
- **link_validator.py** -- Validates bookmark URLs (parallel processing, 20 workers)
- **credential_manager.py** -- Secure credential storage using Fernet encryption

### GUI Components (PyQt5)
- **gui/main_window.py** -- Main application window with tree view, search, filtering
- **gui/settings_dialog.py** -- Application settings configuration
- **gui/analyzer_settings_dialog.py** -- AI analyzer settings (Gemini API key, etc.)
- **gui/keyword_browser.py** -- Keyword and topic browsing interface

### AI Analysis
- **analyzers/gemini_topic_analyzer.py** -- Google Gemini API integration for topic/keyword extraction
- **analyzers/registry.py** -- Pluggable analyzer system
- **gemini_usage_manager.py** -- API rate limiting and quota management

### Configuration
- **settings_manager.py** -- Application settings persistence
- **config/analyzers_config.py** -- Analyzer configuration management

## Common Issues and Workarounds

### Network Dependencies
- **PyPI timeouts**: Extended ML packages (`requirements_Version2.txt`) often fail due to network timeouts. Core app works with basic requirements only.
- **API connectivity**: Gemini API requires network access and valid API key from Google AI Studio.

### Authentication
- **Master password required**: All runs require master password input for credential manager initialization.
- **Browser access**: May require browser closure during bookmark extraction for file lock access.

### GUI Requirements
- **X11 required**: GUI mode needs display. Use `--no-gui` for headless environments.
- **Qt dependencies**: PyQt5 requires system Qt libraries.

## Development Workflow

### Code Quality
- **Always run linting**: `python3 -m flake8 browser_aggregator.py --max-line-length=100`
- **Current linting issues**: Whitespace problems, line length violations in main file
- **No existing tests**: Repository has no test suite or CI pipeline

### AI Configuration
- **Gemini API setup**: Requires API key from Google AI Studio (https://makersuite.google.com/app/apikey)
- **Configuration methods**: Environment variable `GEMINI_API_KEY`, GUI settings, or credential manager
- **Rate limiting**: Built-in free tier protection (2 requests/minute, 50 requests/day)

### Storage Locations
- **App data**: `~/.bookmark_aggregator/`
- **Bookmarks**: `bookmarks_processed.json`
- **Settings**: `settings.json`
- **Credentials**: `credentials.enc` (encrypted)
- **Logs**: `bookmark_aggregator.log`

## Timing Expectations

- **Module imports**: 0.5 seconds
- **Browser detection**: 0.04 seconds  
- **Bookmark categorization**: 0.17 seconds (5 bookmarks)
- **Link validation**: 0.35 seconds (3 URLs, parallel)
- **Linting**: 0.3 seconds
- **Dependency installation**: 30 seconds (basic), may timeout (extended)

## Browser Support Matrix

| Browser | Windows | macOS | Linux | Notes |
|---------|---------|-------|-------|-------|
| Chrome | ✅ | ✅ | ✅ | Full support |
| Firefox | ✅ | ✅ | ✅ | Full support |
| Edge | ✅ | ✅ | ❌ | Chromium-based |
| Safari | ❌ | ✅ | ❌ | macOS only |

## Environment Notes

- **Python version**: Tested with Python 3.12
- **Operating system**: Cross-platform (Windows, macOS, Linux)
- **Network**: Some functionality requires internet for API calls and link validation
- **Display**: GUI requires X11; CLI mode works headless