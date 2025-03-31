# IDCrawl Username Checking Integration

This module provides an enhanced username searching capability for your ReconRadar OSINT tool, similar to the IDCrawl service. It can check usernames across multiple social media and online platforms concurrently, with configurable behavior and robust error handling.

## Files Overview

- **config.json**: Configuration settings for timeouts, concurrency, and other parameters
- **models.py**: Pydantic models for validating configuration and structuring results
- **osint_modules.py**: Core orchestrator that manages the username checking process
- **idcrawl_username_checker.py**: The implementation of the username checking logic
- **sites.json**: Definition of sites to check, with their URL patterns
- **test_idcrawl_integration.py**: Script to test the username checking functionality
- **idcrawl_api_integration.py**: Sample code to integrate with your Flask API

## Installation

1. Copy all the files to your Replit project root directory
2. Make sure to install the required dependencies:

```bash
pip install aiohttp pydantic beautifulsoup4
```

Or if using Poetry:

```bash
poetry add aiohttp pydantic beautifulsoup4
```

## Configuration

### config.json

You can customize the behavior by editing the `config.json` file:

- **timeout**: Request timeout for checking each site
- **max_concurrent_checks**: Maximum number of concurrent site checks per username
- **retry_attempts**: Number of retries for failed requests
- **idcrawl_integration.headless**: Whether to run browser automation in headless mode

### sites.json

This file contains the list of websites to check, with their URL patterns. Each entry should have the site name as the key and the URL pattern as the value, with `{username}` as a placeholder:

```json
{
  "Instagram": "https://www.instagram.com/{username}/",
  "Twitter": "https://twitter.com/{username}",
  "GitHub": "https://github.com/{username}"
}
```

## Usage

### Direct Usage in Python

```python
import asyncio
import aiohttp
from osint_modules import run_username_checks_async

async def check_usernames(usernames):
    async with aiohttp.ClientSession() as session:
        results = await run_username_checks_async(usernames, session)
        # Process results
        for username, user_result in results.items():
            print(f"Results for {username}:")
            for site, site_data in user_result.__root__.items():
                if site_data.status == "found":
                    print(f"- Found on {site}: {site_data.url_found}")

# Run the function
asyncio.run(check_usernames(["johndoe", "janedoe"]))
```

### Using the Test Script

```bash
python test_idcrawl_integration.py johndoe janedoe -o results.json -v
```

### Integration with Flask

Add the following to your main `app.py` file:

```python
from idcrawl_api_integration import register_idcrawl_blueprint

# After creating your Flask app:
register_idcrawl_blueprint(app)
```

Then you can make requests to the API endpoint:

```
POST /api/username-check
Content-Type: application/json

{
  "usernames": ["johndoe", "janedoe"]
}
```

## Customization

### Adding More Sites

To add more sites to check, simply edit the `sites.json` file and add new entries with the site name and URL pattern.

### Custom Detection Logic

You can enhance the detection logic in `idcrawl_username_checker.py` by adding more platform-specific patterns in the `PLATFORM_DETECTION_PATTERNS` dictionary.

## Fallback to Sherlock

If your custom implementation has issues, the system will automatically try to use the `sherlock-project` package as a fallback. Make sure to install it:

```bash
pip install sherlock-project
```

## Technical Details

- Asynchronous requests with `aiohttp` for high performance
- Concurrency control with semaphores at both global and per-username levels
- Pydantic models for data validation and structured results
- Platform-specific detection patterns for improved accuracy
- Comprehensive error handling and retry logic