# unve1ler

Advanced OSINT tool for discovering online profiles, geolocation data, contact information, and performing reverse image searches.

## Features

- **Username Search**: Search for profiles across 90+ social media platforms
- **IDCrawl Integration**: Automated browser-based scraping of idcrawl.com for enhanced results
- **Reverse Image Search**: Generate reverse image search links for popular search engines
- **Metadata Extraction**: Extract metadata from profiles including avatar, bio, followers, etc.
- **Content Extraction**: Extract readable content from web pages
- **Geolocation Detection**: Extract geolocation data from websites using various methods
- **Contact Information**: Extract email addresses, phone numbers and physical addresses
- **Dark Web Detection**: Identify potential dark web services and cryptocurrency addresses
- **Username Intelligence**: Advanced pattern recognition for potential usernames

## Installation

### Basic Installation

```bash
git clone https://github.com/your-username/unve1ler.git
cd unve1ler
pip install -r requirements.txt
```

### Browser Automation for IDCrawl Integration

The IDCrawl automation feature requires additional system dependencies for browser automation:

```bash
# Install Playwright browsers
playwright install

# For Debian/Ubuntu systems, you might need:
apt-get update
apt-get install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libnss3 libxcomposite1 \
                   libxrandr2 libgbm1 libxkbcommon0 libpango-1.0-0 libasound2 \
                   libxdamage1 libenchant1c2a libicu-dev
```

If you're unable to install these dependencies, the system will gracefully fall back to the direct HTTP method for IDCrawl searches.

## Usage

### Web Interface

Start the web server:

```bash
python main.py
```

Then access the web interface at: http://localhost:5000

### API Endpoints

- `/search` - Search for social media profiles
- `/search/advanced` - Advanced people search (including IDCrawl integration)
- `/search/username` - Search specifically for usernames (with enhanced variation detection)
- `/extract` - Extract web content and metadata
- `/analyze/text` - Analyze text content
- `/analyze/file` - Analyze file content
- `/analyze/humint` - Analyze for human intelligence information
- `/analyze/darkweb` - Analyze for dark web indicators
- `/test/idcrawl-automation` - Test the IDCrawl automation functionality

## Examples

### Basic Username Search

```bash
curl -X POST "http://localhost:5000/search" \
  -H "Content-Type: application/json" \
  -d '{"username": "target_username"}'
```

### Advanced People Search with IDCrawl Integration

```bash
curl -X POST "http://localhost:5000/search/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Smith",
    "location": "New York",
    "username": "jsmith",
    "email": "john.smith@example.com"
  }'
```

### Test IDCrawl Automation 

```bash
curl -X POST "http://localhost:5000/test/idcrawl-automation" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "username", 
    "query": "janedoe", 
    "use_automation": true
  }'
```

### Extract Website Content

```bash
curl -X POST "http://localhost:5000/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Analyze for Dark Web Indicators

```bash
curl -X POST "http://localhost:5000/analyze/darkweb" \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact me at mysite.onion or send BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'
```

## Advanced Features

### Geolocation Extraction

The tool can extract geolocation data from websites using:

- Meta tags (OpenGraph, geo.position)
- Schema.org structured data
- Embedded maps (Google Maps)
- Text analysis for coordinates and location mentions

### Dark Web Detection

Identifies references to:

- Onion services (.onion domains)
- Cryptocurrency addresses (Bitcoin, Ethereum)
- Dark web usernames and aliases

### Contact Information Extraction

Extracts:

- Email addresses in various formats
- Phone numbers (international and local formats)
- Physical addresses with intelligent pattern matching

### IDCrawl Integration

Leverages the power of idcrawl.com to find additional profiles:

- Automated browser-based scraping using Playwright
- CAPTCHA detection and avoidance
- Browser fingerprint randomization
- Stealth techniques to prevent detection
- Graceful fallback to direct method when browser automation is not available
- Comprehensive data extraction from search results

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.