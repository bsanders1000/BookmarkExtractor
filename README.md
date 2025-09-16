# Browser Bookmark Aggregator

A comprehensive tool for extracting, analyzing, and managing bookmarks from multiple browsers with AI-powered topic and keyword extraction.

## Features

- Extract bookmarks from Chrome, Firefox, Edge, and Safari
- Cross-platform support (Windows, macOS, Linux)
- AI-powered topic and keyword analysis using Google Gemini
- Secure credential management for browser access
- Rich GUI with filtering and search capabilities
- Export bookmarks to various formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/bsanders1000/BookmarkExtractor.git
cd BookmarkExtractor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the application with GUI:
```bash
python browser_aggregator.py
```

Run in console mode without GUI:
```bash
python browser_aggregator.py --no-gui
```

### AI-Powered Analysis with Gemini

The application includes a powerful AI analyzer that uses Google's Gemini 1.5 Flash model to extract topics and keywords from bookmark content.

#### Setting up Gemini API

1. **Get API Key**: Obtain a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

2. **Configure API Key** (choose one method):
   - **Environment Variable** (recommended):
     ```bash
     export GEMINI_API_KEY="your-api-key-here"
     ```
   - **GUI Settings**: Use "Settings → Analyzer Settings..." in the application
   - **Credential Manager**: Store in the secure credential manager as service "gemini"

#### Using the Gemini Analyzer

1. **Launch Analysis**: In the GUI, go to "Tools → Analyze Bookmarks..."

2. **Select Analyzer**: Choose "Gemini Topic/Keyword Analyzer" from the dropdown

3. **Configure Settings** (optional): 
   - Access via "Settings → Analyzer Settings..."
   - Adjust rate limiting, text processing, and API parameters

#### Free Tier Safety Features

The Gemini analyzer includes built-in safety features for free tier usage:

- **Rate Limiting**: Default 15 requests per minute (free tier limit)
- **Persistent Tracking**: SQLite database tracks API usage across sessions
- **Intelligent Caching**: Avoids duplicate API calls for same content
- **Cost Control**: Limits document size and skips binary files
- **Batch Processing**: Configurable delays between requests

#### Analysis Results

The analyzer extracts:
- **Primary Topic**: Main subject or theme of the bookmark
- **Secondary Topics**: 2-3 related themes  
- **Keywords**: Top 10 most relevant terms (configurable)

Results are automatically saved to your bookmark storage and persist across sessions.

#### Analyzer Settings

| Setting | Description | Default |
|---------|-------------|---------|
| API Key | Gemini API key (if not using env var) | - |
| Use Free Tier | Enable rate limiting for free accounts | True |
| Batch Delay | Seconds between API calls | 4.0 |
| Max Retries | Retry attempts for failed calls | 3 |
| Max Characters | Max content sent to API (cost control) | 10,000 |
| Min Text Length | Skip pages with less content | 600 |
| Top Keywords | Number of keywords to extract | 10 |

## Configuration

### Storage Locations

The application stores data in `~/.bookmark_aggregator/`:
- `bookmarks_processed.json` - Analyzed bookmark data
- `settings.json` - Application settings
- `credentials.enc` - Encrypted browser credentials
- `gemini_cache/` - Cached AI analysis results
- `gemini_rate_limit.db` - API rate limiting database

### Settings Management

- **General Settings**: "Settings → Settings" menu
- **Analyzer Settings**: "Settings → Analyzer Settings..." menu
- **API Keys**: Can be set via environment variables, GUI, or credential manager

## Command Line Options

```bash
python browser_aggregator.py [OPTIONS]

Options:
  --no-gui              Run without GUI interface
  --validate-links      Validate all bookmark URLs
  --export FILE         Export bookmarks to specified file
  --help               Show help message
```

## Browser Support

| Browser | Windows | macOS | Linux | Notes |
|---------|---------|--------|-------|-------|
| Chrome | ✅ | ✅ | ✅ | Full support |
| Firefox | ✅ | ✅ | ✅ | Full support |
| Edge | ✅ | ✅ | ❌ | Chromium-based |
| Safari | ❌ | ✅ | ❌ | macOS only |

## Troubleshooting

### Common Issues

1. **"No Gemini API key found"**
   - Set the `GEMINI_API_KEY` environment variable
   - Or configure in "Settings → Analyzer Settings..."

2. **"Rate limit exceeded"**
   - Wait for the rate limit window to reset (1 minute)
   - Adjust batch delay in analyzer settings

3. **"Failed to fetch content"**
   - Some sites block automated access
   - PDFs and binary files are automatically skipped
   - Check network connectivity

4. **Missing browser bookmarks**
   - Ensure browser is closed during extraction
   - Check browser profile paths in logs
   - Verify read permissions for browser data

### Log Files

Check `bookmark_aggregator.log` for detailed error information and debugging.

## Security

- Browser credentials are encrypted using industry-standard cryptography
- API keys can be stored securely in the credential manager
- No data is sent to external services except for AI analysis (when enabled)
- Cache and database files are stored locally

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

- Built with PyQt5 for the GUI framework
- Uses Google Gemini for AI-powered analysis
- Supports multiple browsers through native bookmark formats