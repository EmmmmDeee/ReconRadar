# unve1ler

Advanced OSINT tool for discovering online profiles, geolocation data, contact information, and performing reverse image searches.

## Features

- **Username Search**: Search for profiles across 90+ social media platforms
- **Reverse Image Search**: Generate reverse image search links for popular search engines
- **Metadata Extraction**: Extract metadata from profiles including avatar, bio, followers, etc.
- **Content Extraction**: Extract readable content from web pages
- **Geolocation Detection**: Extract geolocation data from websites using various methods
- **Contact Information**: Extract email addresses, phone numbers and physical addresses
- **Dark Web Detection**: Identify potential dark web services and cryptocurrency addresses
- **Username Intelligence**: Advanced pattern recognition for potential usernames

## Installation

```bash
git clone https://github.com/your-username/unve1ler.git
cd unve1ler
pip install -r requirements.txt
```

## Usage

### Web Interface

Start the web server:

```bash
python main.py
```

Then access the web interface at: http://localhost:5000

### API Endpoints

- `/search` - Search for social media profiles
- `/extract` - Extract web content and metadata
- `/analyze/text` - Analyze text content
- `/analyze/file` - Analyze file content

## Example

Search for a username:

```bash
curl -X POST "http://localhost:5000/search" \
  -H "Content-Type: application/json" \
  -d '{"username": "target_username"}'
```

Extract website content with enhanced OSINT capabilities:

```bash
curl -X POST "http://localhost:5000/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
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

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.