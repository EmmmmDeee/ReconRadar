# idcrawl_scraper.py - Advanced username checker leveraging idcrawl.com automation

import asyncio
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union

# --- Setup Logging ---
logger = logging.getLogger("idcrawl_scraper")
logger.setLevel(logging.INFO)

# --- Constants ---
DEFAULT_SITES_FILE = "sites.json"
DEFAULT_TIMEOUT = 10.0  # Default timeout in seconds
DEFAULT_CONCURRENCY = 5  # Default concurrency limit
DEFAULT_MAX_RETRIES = 2  # Default number of retries
DEFAULT_RETRY_DELAY = 1.0  # Default delay between retries (seconds)

# --- Optional Dependencies Check ---
PLAYWRIGHT_AVAILABLE = False
PLAYWRIGHT_STEALTH_AVAILABLE = False
IDCRAWL_AUTOMATION_AVAILABLE = False
AUTOMATION_AVAILABLE = False  # Alias for compatibility
AUTOMATION_SCRIPT_AVAILABLE = False  # Alias for compatibility

try:
    import aiohttp
    from aiohttp.client_exceptions import ClientError, ClientResponseError, ClientConnectionError, ServerDisconnectedError
    AIOHTTP_AVAILABLE = True
except ImportError:
    logger.warning("aiohttp not available. This is required for HTTP operations.")
    AIOHTTP_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
    logger.info("Playwright automation dependencies available")
except ImportError:
    logger.warning("Playwright not available. Some features will be disabled.")

if PLAYWRIGHT_AVAILABLE:
    try:
        import playwright_stealth
        PLAYWRIGHT_STEALTH_AVAILABLE = True
        logger.debug("Playwright-stealth module available for enhanced automation")
    except ImportError:
        logger.warning("Playwright-stealth not available. Stealth automation features disabled.")

# Try to import the IdCrawl automation module
try:
    if PLAYWRIGHT_AVAILABLE:
        from idcrawl_automation import perform_search
        IDCRAWL_AUTOMATION_AVAILABLE = True
        AUTOMATION_AVAILABLE = True  # Alias for compatibility
        AUTOMATION_SCRIPT_AVAILABLE = True  # Alias for compatibility
        logger.info("IdCrawl automation module imported successfully")
except ImportError:
    logger.warning("IdCrawl automation module not available. Direct IdCrawl automation disabled.")

# --- Helper Functions ---

def load_sites_from_file(filename: str = DEFAULT_SITES_FILE) -> Dict[str, Any]:
    """
    Load site definitions from a JSON file.
    
    Args:
        filename: Path to the JSON file containing site definitions
        
    Returns:
        Dictionary of site definitions
    """
    try:
        if not os.path.exists(filename):
            logger.warning(f"Sites file not found: {filename}")
            # Create a minimal default sites file
            default_sites = {
                "twitter": {
                    "check_uri": "https://twitter.com/{username}",
                    "check_method": "HEAD",
                    "error_status_codes": [404, 400, 401, 410, 403],
                    "variations": True
                },
                "instagram": {
                    "check_uri": "https://www.instagram.com/{username}/",
                    "check_method": "HEAD",
                    "error_status_codes": [404, 204],
                    "variations": True
                },
                "facebook": {
                    "check_uri": "https://www.facebook.com/{username}",
                    "check_method": "HEAD",
                    "error_status_codes": [404, 302],
                    "variations": True
                },
                "github": {
                    "check_uri": "https://github.com/{username}",
                    "check_method": "GET",
                    "error_status_codes": [404],
                    "variations": False
                },
                "reddit": {
                    "check_uri": "https://www.reddit.com/user/{username}/",
                    "check_method": "GET",
                    "error_status_codes": [404, 302],
                    "variations": False,
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(default_sites, f, indent=2)
            logger.info(f"Created default sites file: {filename}")
            return default_sites
        
        with open(filename, 'r') as f:
            sites_data = json.load(f)
        
        logger.info(f"Loaded {len(sites_data)} site definitions from {filename}")
        return sites_data
    except Exception as e:
        logger.error(f"Error loading sites file: {e}", exc_info=True)
        # Return minimal set of sites if file can't be loaded
        return {
            "twitter": {"check_uri": "https://twitter.com/{username}", "error_status_codes": [404]},
            "github": {"check_uri": "https://github.com/{username}", "error_status_codes": [404]}
        }


def generate_username_variations(username: str) -> List[str]:
    """
    Generate common variations of a username.
    
    Args:
        username: Base username to generate variations for
        
    Returns:
        List of username variations
    """
    # Use list comprehension for efficiency
    variations = []
    
    # If the username contains spaces, treat it as a potential full name
    if ' ' in username:
        parts = username.split()
        if len(parts) == 2:  # First and last name
            first, last = parts
            variations.extend([
                first.lower() + last.lower(),
                first.lower() + '.' + last.lower(),
                first.lower() + '_' + last.lower(),
                first.lower() + '-' + last.lower(),
                first[0].lower() + last.lower(),
                last.lower() + first.lower(),
                last.lower() + '.' + first.lower(),
                last.lower() + '_' + first.lower(),
                last.lower() + '-' + first.lower()
            ])
    
    # Common username variations
    variations.extend([
        username,
        username.lower(),
        username.upper(),
        "real" + username,
        "the" + username,
        username + "1",
        username + "123",
        username + "_official",
    ])
    
    # Remove duplicates while maintaining order (use dict.fromkeys trick)
    return list(dict.fromkeys(variations))


# --- Main Username Checking Function ---

async def check_username_on_sites_async(
    username: str,
    session: aiohttp.ClientSession = None,
    sites_file: str = DEFAULT_SITES_FILE,
    timeout: float = DEFAULT_TIMEOUT,
    concurrency_limit: int = DEFAULT_CONCURRENCY,
    user_agents: List[str] = None,
    proxy: Optional[str] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    generate_variations: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Check if a username exists on various sites.
    
    Args:
        username: Username to check
        session: aiohttp ClientSession to use (created if None)
        sites_file: Path to JSON file containing site definitions
        timeout: Request timeout in seconds
        concurrency_limit: Maximum concurrent requests
        user_agents: List of user agents to rotate through
        proxy: Optional proxy server URL (http://user:pass@host:port)
        max_retries: Maximum number of retries for failed requests
        retry_delay: Delay between retries in seconds
        generate_variations: Whether to generate variations of the username
        
    Returns:
        Dictionary of site names and results
    """
    if not AIOHTTP_AVAILABLE:
        return {"error": {
            "status": "error", 
            "error_message": "aiohttp library not available"
        }}
    
    if not username:
        return {"error": {
            "status": "error", 
            "error_message": "Empty username provided"
        }}
        
    # Try the IdCrawl automated approach if available
    if IDCRAWL_AUTOMATION_AVAILABLE and PLAYWRIGHT_AVAILABLE:
        try:
            idcrawl_results = await _check_with_idcrawl_automation(
                username, 
                timeout=timeout, 
                proxy=proxy, 
                user_agent=random.choice(user_agents) if user_agents else None
            )
            if idcrawl_results:
                # If automation successful, return those results
                # The automation already enriches results with additional data
                logger.info(f"Used IdCrawl automation for '{username}'. Found profiles on {len(idcrawl_results)} sites.")
                return idcrawl_results
        except Exception as e:
            logger.warning(f"IdCrawl automation failed for '{username}': {e}. Falling back to HTTP checks.")
    
    # Otherwise, continue with HTTP-based checks
    # Load site definitions
    sites = load_sites_from_file(sites_file)
    
    # Generate username variations if enabled
    all_usernames = [username]
    if generate_variations:
        all_usernames = generate_username_variations(username)
        
    # Create session if not provided
    should_close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        should_close_session = True
        
    try:
        # Set up a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        # Create task for each site
        tasks = []
        for site_name, site_data in sites.items():
            task = asyncio.create_task(
                _check_site_with_semaphore(
                    semaphore=semaphore,
                    site_name=site_name,
                    site_data=site_data,
                    primary_username=username,
                    username_variations=all_usernames if site_data.get("variations", False) else [username],
                    session=session,
                    timeout=timeout,
                    user_agents=user_agents,
                    proxy=proxy,
                    max_retries=max_retries,
                    retry_delay=retry_delay
                ),
                name=f"check-{site_name}-{username}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions
        results: Dict[str, Dict[str, Any]] = {}
        for i, (site_name, _) in enumerate(sites.items()):
            result = results_list[i]
            
            if isinstance(result, Exception):
                logger.error(f"Error checking '{username}' on {site_name}: {result}", exc_info=True)
                results[site_name] = {
                    "site_name": site_name,
                    "status": "error",
                    "error_message": f"Task exception: {type(result).__name__}"
                }
            else:
                results[site_name] = result
                
        return results
    
    finally:
        # Close session if we created it
        if should_close_session:
            await session.close()


async def _check_site_with_semaphore(
    semaphore: asyncio.Semaphore,
    site_name: str,
    site_data: Dict[str, Any],
    primary_username: str,
    username_variations: List[str],
    session: aiohttp.ClientSession,
    timeout: float,
    user_agents: Optional[List[str]],
    proxy: Optional[str],
    max_retries: int,
    retry_delay: float
) -> Dict[str, Any]:
    """
    Check a site for a username with semaphore-based concurrency control.
    Handles username variations and retry logic.
    
    Returns:
        Dictionary with site check results in IdcrawlSiteResult format
    """
    # Basic result template
    result = {
        "site_name": site_name,
        "status": "not_found"
    }
    
    # Check each username variation
    async with semaphore:
        for username in username_variations:
            try:
                # Format the URL with the username
                url = site_data["check_uri"].format(username=username)
                
                # Get the HTTP method to use
                method = site_data.get("check_method", "GET")
                
                # Extract error status codes
                error_codes = site_data.get("error_status_codes", [404])
                
                # Apply custom headers if provided
                headers = site_data.get("headers", {})
                if user_agents and "User-Agent" not in headers:
                    headers["User-Agent"] = random.choice(user_agents)
                
                # Retry logic
                for attempt in range(max_retries + 1):
                    try:
                        # Make the request
                        response = await session.request(
                            method=method,
                            url=url,
                            headers=headers,
                            timeout=timeout,
                            proxy=proxy,
                            allow_redirects=site_data.get("follow_redirects", False),
                            ssl=site_data.get("verify_ssl", True)
                        )
                        
                        # Check if the response indicates a profile was found
                        if response.status not in error_codes:
                            # Profile found!
                            result = {
                                "site_name": site_name,
                                "status": "found",
                                "url_found": url
                            }
                            
                            # Add username variation info if it's different from primary
                            if username != primary_username:
                                result["variation_used"] = username
                                
                            # Log success
                            logger.debug(f"Profile found on {site_name} with variation '{username}': {url}")
                            
                            # No need to check other variations once we find a match
                            return result
                        else:
                            # Not found with this variation, try next
                            logger.debug(f"Profile not found on {site_name} with variation '{username}'")
                        
                        # If we've made it here, this variation didn't work
                        # but the request was successful, so don't retry
                        break
                        
                    except asyncio.TimeoutError:
                        logger.debug(f"Timeout checking '{username}' on {site_name} (attempt {attempt+1}/{max_retries+1})")
                        if attempt < max_retries:
                            # Wait before retrying
                            await asyncio.sleep(retry_delay * (attempt + 1))
                        else:
                            # Max retries reached
                            result = {
                                "site_name": site_name,
                                "status": "error",
                                "error_message": f"Request timed out after {timeout}s"
                            }
                            
                    except (ClientError, ClientResponseError, ClientConnectionError, ServerDisconnectedError) as e:
                        logger.debug(f"HTTP error checking '{username}' on {site_name}: {e} (attempt {attempt+1}/{max_retries+1})")
                        if attempt < max_retries:
                            # Wait before retrying
                            await asyncio.sleep(retry_delay * (attempt + 1))
                        else:
                            # Max retries reached
                            result = {
                                "site_name": site_name,
                                "status": "error",
                                "error_message": f"HTTP error: {str(e)}"
                            }
                            
                    except Exception as e:
                        # Log unexpected errors
                        logger.error(f"Error checking '{username}' on {site_name}: {e}", exc_info=True)
                        result = {
                            "site_name": site_name,
                            "status": "error",
                            "error_message": f"Unexpected error: {str(e)}"
                        }
                        # Don't retry on unexpected errors
                        break
                
            except Exception as e:
                # Catch any exceptions in the URL formatting or other unexpected issues
                logger.error(f"Error checking variation '{username}' on {site_name}: {e}", exc_info=True)
                result = {
                    "site_name": site_name,
                    "status": "error",
                    "error_message": f"Error: {str(e)}"
                }
    
    # Return the result (either a match or the last error/not found status)
    return result


async def _check_with_idcrawl_automation(
    username: str,
    timeout: float = 60.0,
    proxy: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Use IdCrawl automation to check for a username.
    This leverages Playwright automation to get more comprehensive results.
    
    Args:
        username: Username to check
        timeout: Timeout for automation in seconds
        proxy: Optional proxy URL
        user_agent: Optional user agent
        
    Returns:
        Dictionary of site names and results, or empty dict if automation fails
    """
    if not PLAYWRIGHT_AVAILABLE or not IDCRAWL_AUTOMATION_AVAILABLE:
        return {}
        
    try:
        # Run the IdCrawl automation
        idcrawl_data = await perform_search(
            search_term=username,
            browser_type="chromium",
            headless=True,
            proxy=proxy,
            user_agent=user_agent,
            block_resources_flag=True,
            use_stealth=PLAYWRIGHT_STEALTH_AVAILABLE
        )
        
        if not idcrawl_data:
            logger.warning(f"IdCrawl automation returned no data for '{username}'")
            return {}
        
        # Convert IdCrawl results to our format
        results: Dict[str, Dict[str, Any]] = {}
        
        # Process profiles from different sections
        profile_sections = [
            idcrawl_data.get("instagram", {}).get("profiles", []),
            idcrawl_data.get("twitter", {}).get("profiles", []),
            idcrawl_data.get("facebook", {}).get("profiles", []),
            idcrawl_data.get("linkedin", {}).get("profiles", []),
            idcrawl_data.get("pinterest", {}).get("profiles", []),
            idcrawl_data.get("youtube", {}).get("profiles", []),
            idcrawl_data.get("reddit", {}).get("profiles", []),
            idcrawl_data.get("tiktok", {}).get("profiles", [])
        ]
        
        # Process each section
        for profiles in profile_sections:
            if not profiles:
                continue
                
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue
                    
                # Extract details
                site = profile.get("site", "unknown")
                profile_url = profile.get("url")
                display_name = profile.get("name", "")
                
                if profile_url:
                    results[site] = {
                        "site_name": site,
                        "status": "found",
                        "url_found": profile_url,
                        "display_name": display_name
                    }
        
        # Also process username listings
        usernames = idcrawl_data.get("usernames", [])
        for username_data in usernames:
            if isinstance(username_data, dict):
                site = username_data.get("platform", "")
                platform_username = username_data.get("username", "")
                url = username_data.get("url", "")
                
                if site and url and site not in results:
                    results[site] = {
                        "site_name": site,
                        "status": "found",
                        "url_found": url,
                        "platform_username": platform_username
                    }
        
        # Process web results as well
        web_results = idcrawl_data.get("web_results", [])
        for i, result in enumerate(web_results):
            if isinstance(result, dict):
                title = result.get("title", "")
                url = result.get("url", "")
                snippet = result.get("snippet", "")
                
                if url and (username.lower() in title.lower() or username.lower() in snippet.lower()):
                    site_name = f"web_result_{i+1}"
                    results[site_name] = {
                        "site_name": site_name,
                        "status": "found",
                        "url_found": url,
                        "title": title,
                        "snippet": snippet
                    }
        
        logger.info(f"IdCrawl automation found {len(results)} profiles for '{username}'")
        return results
    
    except Exception as e:
        logger.error(f"Error during IdCrawl automation for '{username}': {e}", exc_info=True)
        return {}


# --- Direct Use Testing ---

async def test_username_check(username: str):
    """Test function for checking a username directly"""
    print(f"Testing username check for: {username}")
    
    async with aiohttp.ClientSession() as session:
        results = await check_username_on_sites_async(
            username=username,
            session=session,
            timeout=10.0,
            generate_variations=True
        )
        
        print(f"\nResults for {username}:")
        print("=" * 50)
        
        found_sites = []
        error_sites = []
        
        for site, data in results.items():
            status = data.get("status")
            if status == "found":
                found_sites.append((site, data.get("url_found")))
            elif status == "error":
                error_sites.append((site, data.get("error_message")))
        
        print(f"Found on {len(found_sites)} sites:")
        for site, url in found_sites:
            print(f"- {site}: {url}")
            
        print(f"\nErrors on {len(error_sites)} sites:")
        for site, error in error_sites:
            print(f"- {site}: {error}")
            
    print("\nTest complete!")


# --- Functions Used by people_finder.py ---

async def search_username_on_idcrawl(username, session=None):
    """
    Function to search for a username on IDCrawl.
    This is the main entry point used by the people_finder module.
    
    Args:
        username: Username to search for
        session: Optional aiohttp session
        
    Returns:
        Dictionary of results
    """
    # Call our existing username checker
    try:
        return await check_username_on_sites_async(
            username=username,
            session=session,
            timeout=10.0,  # Default timeout of 10 seconds
            generate_variations=True
        )
    except Exception as e:
        logger.error(f"Error in search_username_on_idcrawl: {e}", exc_info=True)
        return {"error": {"status": "error", "error_message": f"Search failed: {str(e)}"}}


async def search_person_on_idcrawl(full_name, location=None, session=None):
    """
    Function to search for a person by full name on IDCrawl.
    This function is used by the people_finder module.
    
    Args:
        full_name: Person's full name to search for
        location: Optional location info to narrow results
        session: Optional aiohttp session
        
    Returns:
        Dictionary of results
    """
    # Currently we use our username checker on the full name
    # In the future this could be improved to use specific person search functionality
    try:
        if location:
            logger.info(f"Searching for '{full_name}' in location '{location}'")
            # TODO: Use location parameter in future implementations
            
        return await check_username_on_sites_async(
            username=full_name,
            session=session,
            timeout=15.0,  # Longer timeout for full name searches
            generate_variations=True
        )
    except Exception as e:
        logger.error(f"Error in search_person_on_idcrawl: {e}", exc_info=True)
        return {"error": {"status": "error", "error_message": f"Search failed: {str(e)}"}}


def enrich_results_with_idcrawl(results, profile_data):
    """
    Enrich search results with additional data from IDCrawl.
    This function is used by the people_finder module.
    
    Args:
        results: Existing results dictionary
        profile_data: Profile data from IDCrawl
        
    Returns:
        Enriched results dictionary
    """
    # Just a simple implementation that combines the dictionaries
    if not results:
        return profile_data
    if not profile_data:
        return results
        
    # Start with the results
    enriched = dict(results)
    
    # Add/update with profile data
    for platform, data in profile_data.items():
        if platform not in enriched:
            enriched[platform] = data
        elif isinstance(enriched[platform], dict) and isinstance(data, dict):
            # Merge dictionaries
            enriched[platform].update(data)
            
    return enriched


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python idcrawl_scraper.py <username>")
        sys.exit(1)
        
    test_username = sys.argv[1]
    asyncio.run(test_username_check(test_username))