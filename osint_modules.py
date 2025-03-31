"""
OSINT modules for username checking across multiple sites
"""

import asyncio
import time
import logging
import json
import sys
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
import random
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
from aiohttp.client_exceptions import ClientConnectorError, ServerTimeoutError
import traceback

from models import load_config, IdcrawlSiteResult, IdcrawlUserResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("osint_modules")

# Load configuration
CONFIG = load_config()

# Import idcrawl_scraper asynchronously to avoid startup delays
idcrawl_scraper = None
try:
    from idcrawl_scraper import check_username_on_site_async
    logger.info("Successfully imported idcrawl_scraper module")
except ImportError:
    logger.warning("Could not import idcrawl_scraper, falling back to default implementation")


async def default_check_username_on_site_async(
    username: str, 
    site_name: str, 
    url_format: str, 
    session: ClientSession, 
    **kwargs
) -> IdcrawlSiteResult:
    """
    Default implementation of check_username_on_site_async if the idcrawl_scraper module is not available.
    This is a basic implementation that just checks if the URL exists.
    
    Args:
        username: Username to check
        site_name: Name of the site
        url_format: URL format string with {} placeholder for username
        session: aiohttp ClientSession to use
        **kwargs: Additional arguments
        
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
        headers = {"User-Agent": CONFIG.username_check.user_agent}
        async with session.get(
            url, 
            timeout=timeout, 
            headers=headers, 
            ssl=CONFIG.username_check.verify_ssl
        ) as response:
            result.status_code = response.status
            result.found = response.status in CONFIG.username_check.allowed_http_codes
            if result.found:
                result.profile_url = url
                result.confidence = 0.8  # Basic confidence score for successful request
            
            # Try to read some of the response for better detection
            if result.found:
                try:
                    content = await response.text(errors='ignore')
                    content_sample = content[:1000].lower()
                    
                    # Look for common error phrases that might indicate false positives
                    error_phrases = [
                        "not found", "doesn't exist", "no user", "page not found",
                        "404", "user does not exist", "user not found", "no account found"
                    ]
                    for phrase in error_phrases:
                        if phrase in content_sample:
                            result.found = False
                            result.error = f"Found error phrase: '{phrase}'"
                            result.confidence = 0
                            break
                            
                    # If we still think we found it, check for username in content
                    if result.found and username.lower() in content_sample:
                        result.confidence = 0.9  # Higher confidence if username is in the page
                        
                except Exception as e:
                    logger.debug(f"Error reading content for {site_name}: {str(e)}")
    
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


async def load_sites_data() -> Dict[str, str]:
    """
    Load site data from sites.json or fallback to default sites if not available
    
    Returns:
        Dictionary of site names and URL formats
    """
    sites_path = Path("sites.json")
    
    # Default fallback sites if no sites.json found
    default_sites = {
        "Instagram": "https://www.instagram.com/{username}/",
        "Twitter": "https://twitter.com/{username}",
        "Facebook": "https://www.facebook.com/{username}",
        "LinkedIn": "https://www.linkedin.com/in/{username}/",
        "GitHub": "https://github.com/{username}",
        "Reddit": "https://www.reddit.com/user/{username}",
        "YouTube": "https://www.youtube.com/user/{username}",
        "Pinterest": "https://www.pinterest.com/{username}/",
        "TikTok": "https://www.tiktok.com/@{username}"
    }
    
    if not sites_path.exists():
        logger.warning("sites.json not found, using default sites")
        return default_sites
    
    try:
        with open(sites_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading sites.json: {str(e)}")
        return default_sites


def generate_username_variations(username: str) -> List[str]:
    """
    Generate variations of a username
    
    Args:
        username: Base username
        
    Returns:
        List of username variations
    """
    variations = [username]  # Original username
    
    # Add basic variations
    variations.extend([
        username.lower(),
        username.upper(),
        username.capitalize(),
        f"{username}1",
        f"{username}123",
        f"{username}_",
        f"_{username}",
        f"{username}_",
        f"{username.replace(' ', '')}",
        f"{username.replace(' ', '_')}",
        f"{username.replace(' ', '-')}",
        f"{username.replace('.', '_')}",
        f"{username.replace('_', '.')}",
        f"{username.replace('-', '_')}",
    ])
    
    # Remove duplicates while maintaining order
    seen = set()
    unique_variations = []
    for variation in variations:
        if variation not in seen:
            seen.add(variation)
            unique_variations.append(variation)
    
    return unique_variations


async def run_username_checks_async(
    username: str,
    variations: bool = True,
    max_sites: Optional[int] = None,
    check_function = None
) -> IdcrawlUserResult:
    """
    Check username across multiple sites asynchronously
    
    Args:
        username: Username to check
        variations: Whether to check variations of the username
        max_sites: Maximum number of sites to check (None for all)
        check_function: Custom function to check username on a site
        
    Returns:
        IdcrawlUserResult with the results
    """
    start_time = time.time()
    
    # Determine which check function to use
    site_check_function = check_function
    if site_check_function is None:
        # Import the module function or use default
        if 'check_username_on_site_async' in globals() and globals()['check_username_on_site_async']:
            site_check_function = globals()['check_username_on_site_async']
        else:
            site_check_function = default_check_username_on_site_async
            logger.warning("Using default username check function")
    
    # Generate username variations if requested
    username_variations = [username]
    if variations:
        username_variations = generate_username_variations(username)
        logger.info(f"Generated {len(username_variations)} username variations")
    
    # Load sites
    sites = await load_sites_data()
    if max_sites:
        # Prioritize most popular sites if max_sites is limited
        popular_sites = [
            "Instagram", "Twitter", "Facebook", "LinkedIn", "TikTok", 
            "GitHub", "YouTube", "Reddit", "Pinterest"
        ]
        
        # Combine popular sites with random selection from others
        selected_popular = [s for s in popular_sites if s in sites]
        other_sites = [s for s in sites if s not in popular_sites]
        
        # Shuffle other sites for randomness
        random.shuffle(other_sites)
        
        # Combine popular sites with some others, up to max_sites
        remaining = max_sites - len(selected_popular)
        if remaining > 0:
            selected_sites = {s: sites[s] for s in selected_popular}
            selected_sites.update({s: sites[s] for s in other_sites[:remaining]})
            sites = selected_sites
    
    logger.info(f"Checking username '{username}' on {len(sites)} sites")

    # Create a result object
    result = IdcrawlUserResult(
        username=username,
        variations_checked=username_variations
    )
    
    # Execute checks
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(CONFIG.username_check.max_concurrent_checks)
        
        async def check_site(site_name, url_format):
            async with sem:
                # Check the original username first
                try:
                    site_result = await site_check_function(
                        username=username,
                        site_name=site_name,
                        url_format=url_format,
                        session=session
                    )
                    result.results.append(site_result)
                except Exception as e:
                    logger.error(f"Error checking {site_name}: {str(e)}")
                    logger.debug(traceback.format_exc())
                    error_result = IdcrawlSiteResult(
                        site_name=site_name,
                        url_checked=url_format.format(username=username),
                        found=False,
                        error=f"Exception: {str(e)}",
                        username_used=username
                    )
                    result.results.append(error_result)
                
                # If not found and variations are enabled, check variations
                if variations and not result.results[-1].found and len(username_variations) > 1:
                    # Only check a couple variations to avoid excessive requests
                    for variation in username_variations[1:3]:  # Skip the original username
                        if variation == username:
                            continue
                            
                        try:
                            var_result = await site_check_function(
                                username=variation,
                                site_name=site_name,
                                url_format=url_format,
                                session=session
                            )
                            if var_result.found:
                                result.results.append(var_result)
                                break  # Stop checking further variations if one is found
                        except Exception as e:
                            logger.debug(f"Error checking variation {variation} on {site_name}: {str(e)}")
        
        # Run checks concurrently
        tasks = [check_site(site_name, url_format) for site_name, url_format in sites.items()]
        await asyncio.gather(*tasks)
    
    # Calculate summary statistics
    result.calculate_summary_stats()
    
    # Record execution time
    end_time = time.time()
    result.execution_time = end_time - start_time
    
    logger.info(
        f"Completed username checks for '{username}' on {result.sites_checked} sites. " 
        f"Found {result.sites_with_profiles} profiles in {result.execution_time:.2f} seconds."
    )
    
    return result