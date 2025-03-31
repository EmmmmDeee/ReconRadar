"""
Enhanced username checker implementation for the unve1ler OSINT tool
Built on top of idcrawl_scraper.py to provide improved social media profile detection
"""

import asyncio
import time
import logging
import re
import random
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
from aiohttp.client_exceptions import ClientConnectorError, ServerTimeoutError
from bs4 import BeautifulSoup
import json
from urllib.parse import quote_plus, urljoin
from pathlib import Path

from models import load_config, IdcrawlSiteResult, IdcrawlUserResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("idcrawl_username_checker")

# Load configuration
CONFIG = load_config()

# Platform-specific detection rules
PLATFORM_DETECTION_PATTERNS = {
    "Instagram": {
        "user_pattern": r'"username":"([^"]+)"',
        "full_name_pattern": r'"full_name":"([^"]+)"',
        "bio_pattern": r'"biography":"([^"]+)"',
        "followers_pattern": r'"edge_followed_by":{"count":(\d+)}',
        "error_phrases": ["Sorry, this page isn't available"],
        "success_elements": ["id='react-root'", "profile-page"]
    },
    "Twitter": {
        "user_pattern": r'<div class="profile" data-screen-name="([^"]+)"',
        "full_name_pattern": r'<h1[^>]*>([^<]+)</h1>',
        "error_phrases": ["This account doesn't exist", "page doesn't exist"],
        "success_elements": ["ProfileHeaderCard", "ProfileAvatar", "js-tweet-text-container"]
    },
    "Facebook": {
        "user_pattern": r'"entity_id":"(\d+)"',
        "full_name_pattern": r'<title>([^<|]+)',
        "error_phrases": ["The page you requested was not found", "content isn't available right now"],
        "success_elements": ["ProfileTimeline", "userContentWrapper", "photoContainer"]
    },
    "LinkedIn": {
        "user_pattern": r'"publicIdentifier":"([^"]+)"',
        "full_name_pattern": r'"formattedName":"([^"]+)"',
        "error_phrases": ["The profile you're looking for doesn't exist", "page not found", "page doesn't exist"],
        "success_elements": ["profile-nav-item", "core-rail", "pv-top-card"]
    },
    "GitHub": {
        "user_pattern": r'<meta property="profile:username" content="([^"]+)"',
        "full_name_pattern": r'<title>([^<|(]+)',
        "error_phrases": ["Not Found", "Page not found", "404"],
        "success_elements": ["js-profile-editable-area", "pinned-items-container", "js-repo-filter"]
    },
    "Reddit": {
        "user_pattern": r'"username":"([^"]+)"',
        "error_phrases": ["Sorry, nobody on Reddit goes by that name", "page not found", "doesn't exist"],
        "success_elements": ["ProfileCard", "Profile__overlay", "UserInfoTooltip"]
    },
    "YouTube": {
        "user_pattern": r'"channelId":"([^"]+)"',
        "full_name_pattern": r'"title":"([^"]+)"',
        "error_phrases": ["This page isn't available", "404", "does not exist"],
        "success_elements": ["channel-header", "subscriber-count", "meta-item subscribers"]
    },
    "TikTok": {
        "user_pattern": r'"uniqueId":"([^"]+)"',
        "full_name_pattern": r'"nickname":"([^"]+)"',
        "error_phrases": ["Couldn't find this account", "page not found"],
        "success_elements": ["share-title", "user-page", "tiktok-avatar"]
    }
}

# Default rules for platforms without specific patterns
DEFAULT_DETECTION = {
    "user_pattern": r'profile|username|@([a-zA-Z0-9._-]+)',
    "error_phrases": ["not found", "doesn't exist", "no results", "no user", "no profile", "error", "404", "no account"],
    "success_elements": ["profile", "account", "user", "bio", "avatar", "follow", "subscriber"]
}


async def analyze_response(
    response_text: str, 
    site_name: str, 
    username: str
) -> Dict[str, Any]:
    """
    Analyze response text for indicators of profile existence
    
    Args:
        response_text: HTML response text
        site_name: Name of the site
        username: Username being checked
        
    Returns:
        Dictionary with analysis results
    """
    results = {
        "found": False,
        "confidence": 0.0,
        "metadata": {}
    }
    
    # Get detection patterns for this platform or use defaults
    patterns = PLATFORM_DETECTION_PATTERNS.get(site_name, DEFAULT_DETECTION)
    
    # Check for error phrases that indicate profile doesn't exist
    for phrase in patterns.get("error_phrases", []):
        if phrase.lower() in response_text.lower():
            results["metadata"]["error_phrase_found"] = phrase
            return results
    
    # Look for success elements that indicate profile exists
    element_count = 0
    for element in patterns.get("success_elements", []):
        if element.lower() in response_text.lower():
            element_count += 1
    
    results["metadata"]["success_elements_found"] = element_count
    
    # Extract metadata if available
    try:
        # Try to extract username from response
        user_pattern = patterns.get("user_pattern", DEFAULT_DETECTION["user_pattern"])
        user_match = re.search(user_pattern, response_text)
        if user_match:
            extracted_username = user_match.group(1)
            results["metadata"]["extracted_username"] = extracted_username
            
            # Compare extracted username with search username
            if extracted_username.lower() == username.lower():
                results["confidence"] += 0.5
            
        # Try to extract full name from response
        if "full_name_pattern" in patterns:
            fullname_match = re.search(patterns["full_name_pattern"], response_text)
            if fullname_match:
                results["metadata"]["extracted_fullname"] = fullname_match.group(1).strip()
                results["confidence"] += 0.1
                
        # Try to extract bio if available
        if "bio_pattern" in patterns:
            bio_match = re.search(patterns["bio_pattern"], response_text)
            if bio_match:
                results["metadata"]["extracted_bio"] = bio_match.group(1).strip()
                results["confidence"] += 0.1
                
        # Try to extract followers count if available
        if "followers_pattern" in patterns:
            followers_match = re.search(patterns["followers_pattern"], response_text)
            if followers_match:
                results["metadata"]["followers_count"] = int(followers_match.group(1))
                results["confidence"] += 0.1
    except Exception as e:
        logger.debug(f"Error extracting metadata: {str(e)}")
    
    # Calculate confidence based on success elements
    if element_count >= 3:
        results["confidence"] += 0.3
    elif element_count >= 1:
        results["confidence"] += 0.1 * element_count
        
    # Simple check for username in content
    if username.lower() in response_text.lower():
        results["confidence"] += 0.1
        
    # Determine if profile is found based on confidence
    results["found"] = results["confidence"] >= 0.5
    
    return results


async def check_username_on_site_async(
    username: str, 
    site_name: str, 
    url_format: str, 
    session: ClientSession, 
    **kwargs
) -> IdcrawlSiteResult:
    """
    Check if a username exists on a specific site
    
    Args:
        username: Username to check
        site_name: Name of the site
        url_format: URL format string with {username} placeholder
        session: aiohttp ClientSession
        **kwargs: Additional keyword arguments
        
    Returns:
        IdcrawlSiteResult object with check results
    """
    start_time = time.time()
    url = url_format.format(username=username)
    
    result = IdcrawlSiteResult(
        site_name=site_name,
        url_checked=url,
        found=False,
        username_used=username
    )
    
    timeout = ClientTimeout(total=CONFIG.username_check.timeout)
    
    try:
        # Random delay to avoid being blocked
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Prepare headers with random user agent from a pool
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1"
        }
        
        async with session.get(
            url, 
            timeout=timeout, 
            headers=headers, 
            ssl=CONFIG.username_check.verify_ssl,
            allow_redirects=True
        ) as response:
            result.status_code = response.status
            
            # Check if status code indicates success
            if response.status in CONFIG.username_check.allowed_http_codes:
                content = await response.text(errors='ignore')
                
                # Analyze the response
                analysis = await analyze_response(content, site_name, username)
                result.found = analysis["found"]
                result.confidence = analysis["confidence"]
                
                if result.found:
                    result.profile_url = url
                    result.metadata.update(analysis["metadata"])
                    
                    # Additional metadata from response headers
                    if "last-modified" in response.headers:
                        result.metadata["last_modified"] = response.headers["last-modified"]
                    
                else:
                    # If analysis suggests profile doesn't exist
                    result.error = "Profile not found according to content analysis"
            else:
                result.error = f"HTTP status code: {response.status}"
                
    except ClientConnectorError:
        result.error = "Connection error"
    except ServerTimeoutError:
        result.error = "Timeout"
    except asyncio.TimeoutError:
        result.error = "Timeout"
    except ClientError as e:
        result.error = f"Client error: {str(e)}"
    except Exception as e:
        result.error = f"Error: {str(e)}"
    
    end_time = time.time()
    result.response_time = end_time - start_time
    
    return result


async def test_username_checker():
    """
    Test function for the username checker
    """
    username = "testuser"
    site_name = "GitHub"
    url_format = "https://github.com/{username}"
    
    async with aiohttp.ClientSession() as session:
        result = await check_username_on_site_async(
            username=username,
            site_name=site_name,
            url_format=url_format,
            session=session
        )
        
        print(f"Result for {username} on {site_name}:")
        print(f"Found: {result.found}")
        print(f"Confidence: {result.confidence}")
        print(f"Error: {result.error}")
        print(f"Metadata: {result.metadata}")
        print(f"Response time: {result.response_time}")


if __name__ == "__main__":
    asyncio.run(test_username_checker())