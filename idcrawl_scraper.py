"""
IdCrawl Integration Module for unve1ler

This module provides functionality to scrape and extract data from idcrawl.com,
leveraging their comprehensive people search capabilities to enhance our own results.

It supports two methods:
1. Direct HTTP requests (basic, subject to CAPTCHA)
2. Browser automation via Playwright (advanced, more reliable)
"""

import logging
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import os
import asyncio
import sys
import time
import hashlib
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the automation dependencies are available
AUTOMATION_AVAILABLE = False
try:
    import playwright
    from tenacity import retry
    AUTOMATION_AVAILABLE = True
    logger.info("Playwright automation dependencies available")
except ImportError:
    logger.warning("Playwright automation dependencies not available. "
                  "For enhanced IdCrawl access, install with: "
                  "pip install playwright playwright-stealth tenacity")
    
# Import our custom automation module if it exists
try:
    from idcrawl_automation import perform_search
    logger.info("IdCrawl automation module imported successfully")
    AUTOMATION_SCRIPT_AVAILABLE = True
except ImportError:
    logger.warning("IdCrawl automation script not found")
    AUTOMATION_SCRIPT_AVAILABLE = False
    
    # Define a dummy function to avoid errors if automation is not available
    async def perform_search(*args, **kwargs):
        """Dummy function when the real automation script is not available"""
        logger.error("perform_search called but automation script is not available")
        return {
            "metadata": {
                "success": False,
                "error": "Automation script not available",
                "captcha_detected": False
            }
        }

class IdCrawlScraper:
    """Class for scraping and extracting data from idcrawl.com"""
    
    def __init__(self, user_agent=None, timeout=10):
        """
        Initialize the IdCrawl scraper with custom user agent and timeout
        
        Args:
            user_agent (str, optional): Custom user agent string
            timeout (int): Request timeout in seconds
        """
        self.base_url = "https://www.idcrawl.com"
        self.search_url = urljoin(self.base_url, "/search")
        self.timeout = timeout
        
        # Use a browser-like user agent to avoid detection
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Set up session with appropriate headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        })
    
    def search_username(self, username):
        """
        Search for a username on idcrawl.com
        
        Args:
            username (str): Username to search for
            
        Returns:
            dict: Structured results from idcrawl.com
        """
        logger.info(f"Searching idcrawl.com for username: {username}")
        
        try:
            # First, visit the homepage to get any necessary cookies
            self.session.get(self.base_url, timeout=self.timeout)
            
            # Use query parameters in the URL for a GET request instead of POST
            search_url = urljoin(self.base_url, f"/u/{quote_plus(username)}")
            
            # Set up headers for a regular web browser GET request
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": self.base_url
            }
            
            # Perform the search request as GET
            response = self.session.get(
                search_url, 
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse results
            return self._parse_search_results(response.text, username)
        except requests.RequestException as e:
            error_message = str(e)
            logger.error(f"Error searching idcrawl.com: {error_message}")
            
            # Check if this is a CAPTCHA challenge (HTTP 405 with specific WAF action)
            if "405" in error_message:
                captcha_message = ("IdCrawl.com requires human verification (CAPTCHA). "
                                  "Direct scraping is not possible due to bot protection. "
                                  "Please consider using alternative sources or manual verification.")
                logger.warning(captcha_message)
                return {
                    "success": False,
                    "error": captcha_message,
                    "requires_captcha": True,
                    "profiles": {},
                    "platform_metadata": {},
                    "image_metadata": None
                }
            else:
                return {
                    "success": False,
                    "error": error_message,
                    "profiles": {},
                    "platform_metadata": {},
                    "image_metadata": None
                }
    
    def search_person(self, full_name=None, location=None):
        """
        Search for a person by name and optional location on idcrawl.com
        
        Args:
            full_name (str): Person's full name
            location (str, optional): Location for filtering results
            
        Returns:
            dict: Structured results from idcrawl.com
        """
        if not full_name:
            return {"success": False, "error": "Full name is required"}
        
        logger.info(f"Searching idcrawl.com for person: {full_name}" + 
                   (f" in {location}" if location else ""))
        
        try:
            # First, visit the homepage to get any necessary cookies
            self.session.get(self.base_url, timeout=self.timeout)
            
            # Format the name for the URL
            name_query = quote_plus(full_name)
            
            # Use query parameters in the URL for a GET request
            search_url = urljoin(self.base_url, f"/p/{name_query}")
            
            # Add location to the URL if provided
            if location:
                search_url += f"?location={quote_plus(location)}"
            
            # Set up headers for a regular web browser GET request
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": self.base_url
            }
            
            # Perform the search request as GET
            response = self.session.get(
                search_url, 
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse results
            return self._parse_search_results(response.text, full_name)
        except requests.RequestException as e:
            error_message = str(e)
            logger.error(f"Error searching idcrawl.com: {error_message}")
            
            # Check if this is a CAPTCHA challenge (HTTP 405 with specific WAF action)
            if "405" in error_message:
                captcha_message = ("IdCrawl.com requires human verification (CAPTCHA). "
                                  "Direct scraping is not possible due to bot protection. "
                                  "Please consider using alternative sources or manual verification.")
                logger.warning(captcha_message)
                return {
                    "success": False,
                    "error": captcha_message,
                    "requires_captcha": True,
                    "profiles": {},
                    "platform_metadata": {},
                    "image_metadata": None
                }
            else:
                return {
                    "success": False,
                    "error": error_message,
                    "profiles": {},
                    "platform_metadata": {},
                    "image_metadata": None
                }
    
    def _parse_search_results(self, html_content, search_term):
        """
        Parse search results HTML from idcrawl.com
        
        Args:
            html_content (str): HTML content from search results page
            search_term (str): The search term used
            
        Returns:
            dict: Structured results with profiles, platforms, etc.
        """
        results = {
            "success": True,
            "search_term": search_term,
            "profiles": {},
            "platform_metadata": {
                "categories": {
                    "Social Media": [],
                    "Professional": [],
                    "Content Creation": [],
                    "Gaming": [],
                    "Other": []
                },
                "detailed_metadata": {}
            },
            "image_metadata": None
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract profile cards
            profile_cards = soup.select('.profile-card, .result-card')
            
            for card in profile_cards:
                platform_data = self._extract_profile_card_data(card)
                if platform_data:
                    platform_name = platform_data.get("platform")
                    if platform_name:
                        # Add to profiles
                        results["profiles"][platform_name] = platform_data.get("url", "")
                        
                        # Add to platform metadata
                        platform_category = self._categorize_platform(platform_name)
                        if platform_category and platform_name not in results["platform_metadata"]["categories"][platform_category]:
                            results["platform_metadata"]["categories"][platform_category].append(platform_name)
                        
                        # Add detailed metadata
                        results["platform_metadata"]["detailed_metadata"][platform_name] = platform_data
            
            # Extract image data if available
            image_data = self._extract_image_data(soup)
            if image_data:
                results["image_metadata"] = image_data
                
            # If no profiles found, set success to false
            if not results["profiles"]:
                results["success"] = False
                results["error"] = "No profiles found for the search term"
                
        except Exception as e:
            logger.error(f"Error parsing idcrawl.com results: {str(e)}")
            results["success"] = False
            results["error"] = f"Error parsing results: {str(e)}"
        
        return results
    
    def _extract_profile_card_data(self, card):
        """
        Extract data from a profile card element
        
        Args:
            card (BeautifulSoup element): Profile card element
            
        Returns:
            dict: Structured data from the profile card
        """
        try:
            platform_data = {}
            
            # Extract platform name
            platform_elm = card.select_one('.platform-name, .result-title')
            if platform_elm:
                platform_data["platform"] = platform_elm.get_text().strip()
            
            # Extract profile URL
            url_elm = card.select_one('a.profile-link, a.result-link')
            if url_elm and url_elm.has_attr('href'):
                profile_url = url_elm['href']
                # Fix relative URLs
                if profile_url.startswith('/'):
                    profile_url = urljoin(self.base_url, profile_url)
                platform_data["url"] = profile_url
            
            # Extract username
            username_elm = card.select_one('.username, .result-username')
            if username_elm:
                platform_data["username"] = username_elm.get_text().strip()
            
            # Extract avatar/image
            avatar_elm = card.select_one('img.avatar, img.result-image')
            if avatar_elm and avatar_elm.has_attr('src'):
                avatar_url = avatar_elm['src']
                if avatar_url.startswith('/'):
                    avatar_url = urljoin(self.base_url, avatar_url)
                platform_data["avatar_url"] = avatar_url
            
            # Extract name
            name_elm = card.select_one('.display-name, .result-name')
            if name_elm:
                platform_data["name"] = name_elm.get_text().strip()
            
            # Extract bio/description
            bio_elm = card.select_one('.bio, .result-description')
            if bio_elm:
                platform_data["bio"] = bio_elm.get_text().strip()
            
            # Extract profile content sample
            content_elm = card.select_one('.content-sample, .result-content')
            if content_elm:
                platform_data["content_sample"] = content_elm.get_text().strip()
            
            # Extract connections/followers/following if available
            connections_elm = card.select_one('.connections, .result-connections')
            if connections_elm:
                connections_text = connections_elm.get_text().strip()
                platform_data["connections"] = self._parse_connections(connections_text)
            else:
                platform_data["connections"] = []
            
            # Extract profile ID (some platforms have unique IDs)
            profile_id = ""
            if "url" in platform_data:
                # Try to extract ID from URL
                id_match = re.search(r'\/([^\/]+)$', platform_data["url"])
                if id_match:
                    profile_id = id_match.group(1)
                else:
                    # Generate a unique ID
                    platform = platform_data.get("platform", "").lower().replace(" ", "_")
                    username = platform_data.get("username", "").lower().replace(" ", "_")
                    profile_id = f"{platform}_{hash(platform_data['url']) & 0xffffffff:x}"
            
            platform_data["profile_id"] = profile_id
            
            return platform_data
        except Exception as e:
            logger.error(f"Error extracting profile card data: {str(e)}")
            return None
    
    def _extract_image_data(self, soup):
        """
        Extract image metadata from search results
        
        Args:
            soup (BeautifulSoup): Parsed HTML soup
            
        Returns:
            dict: Image metadata or None if not found
        """
        try:
            image_section = soup.select_one('.image-results, .reverse-image-results')
            if not image_section:
                return None
                
            image_data = {
                "original_image": None,
                "similar_images": [],
                "possible_sources": []
            }
            
            # Extract original image
            orig_img = image_section.select_one('.original-image img')
            if orig_img and orig_img.has_attr('src'):
                image_data["original_image"] = orig_img['src']
            
            # Extract similar images
            similar_imgs = image_section.select('.similar-image img')
            for img in similar_imgs:
                if img.has_attr('src'):
                    image_url = img['src']
                    if image_url.startswith('/'):
                        image_url = urljoin(self.base_url, image_url)
                    image_data["similar_images"].append(image_url)
            
            # Extract possible sources
            source_links = image_section.select('.image-source a')
            for link in source_links:
                if link.has_attr('href'):
                    source_url = link['href']
                    if source_url.startswith('/'):
                        source_url = urljoin(self.base_url, source_url)
                    source_text = link.get_text().strip()
                    image_data["possible_sources"].append({
                        "url": source_url,
                        "text": source_text
                    })
            
            return image_data
        except Exception as e:
            logger.error(f"Error extracting image data: {str(e)}")
            return None
    
    def _parse_connections(self, connections_text):
        """
        Parse connections text into structured data
        
        Args:
            connections_text (str): Text containing connection information
            
        Returns:
            list: List of connection objects
        """
        connections = []
        
        # Common patterns: "123 followers", "Following: 45", etc.
        follower_match = re.search(r'(\d+)\s*followers?', connections_text, re.I)
        following_match = re.search(r'(\d+)\s*following', connections_text, re.I)
        friends_match = re.search(r'(\d+)\s*friends?', connections_text, re.I)
        
        if follower_match:
            connections.append({
                "type": "followers",
                "count": int(follower_match.group(1))
            })
        
        if following_match:
            connections.append({
                "type": "following",
                "count": int(following_match.group(1))
            })
        
        if friends_match:
            connections.append({
                "type": "friends",
                "count": int(friends_match.group(1))
            })
        
        return connections
    
    def _categorize_platform(self, platform_name):
        """
        Categorize a platform into predefined categories
        
        Args:
            platform_name (str): The platform name to categorize
            
        Returns:
            str: Category name or None if not categorized
        """
        platform = platform_name.lower()
        
        # Social Media platforms
        if platform in ['facebook', 'twitter', 'instagram', 'snapchat', 'tiktok', 'pinterest']:
            return "Social Media"
        
        # Professional platforms
        elif platform in ['linkedin', 'github', 'gitlab', 'behance', 'dribbble', 'medium', 'dev.to', 'quora']:
            return "Professional"
        
        # Content Creation platforms
        elif platform in ['youtube', 'vimeo', 'twitch', 'soundcloud', 'bandcamp', 'mixcloud', 'patreon', 'substack']:
            return "Content Creation"
        
        # Gaming platforms
        elif platform in ['steam', 'discord', 'xbox', 'playstation', 'nintendo', 'battle.net', 'epic games']:
            return "Gaming"
        
        # Default to Other
        else:
            return "Other"


# Stand-alone functions for easy integration with unve1ler

def search_username_on_idcrawl(username, use_automation=True):
    """
    Search for a username on idcrawl.com
    
    Args:
        username (str): Username to search for
        use_automation (bool): Whether to use browser automation if available
        
    Returns:
        dict: Structured results from idcrawl.com
    """
    # First try automation if available and requested
    if use_automation and AUTOMATION_AVAILABLE and AUTOMATION_SCRIPT_AVAILABLE:
        try:
            logger.info(f"Using Playwright automation to search IDCrawl for username: {username}")
            
            # Check if browser dependencies are available
            try:
                import tempfile
                temp_json = os.path.join(tempfile.gettempdir(), f"idcrawl_{username}_{int(time.time())}.json")
                
                # Run the search asynchronously with headless mode
                automation_results = asyncio.run(perform_search(
                    search_term=username,
                    json_output_path=temp_json,
                    browser_type="chromium",
                    block_resources_flag=True,
                    use_stealth=True,
                    headless=True  # Use headless mode to avoid system dependency issues
                ))
            except Exception as browser_error:
                if "missing dependencies" in str(browser_error).lower():
                    logger.warning(f"Browser dependencies missing: {str(browser_error)}")
                    # Create a special error result
                    return {
                        "success": False,
                        "error": "Browser automation dependencies missing. Install system libraries or use direct method.",
                        "requires_system_deps": True,
                        "missing_deps_error": str(browser_error),
                        "profiles": {},
                        "platform_metadata": {},
                        "image_metadata": None
                    }
                else:
                    # Re-raise for other types of errors
                    raise
            
            # Check if automation was successful
            if automation_results.get("metadata", {}).get("success", False):
                logger.info(f"Successfully retrieved IDCrawl results for {username} via automation")
                
                # Convert automation results to the expected format
                converted_results = {
                    "success": True,
                    "search_term": username,
                    "profiles": {},
                    "platform_metadata": {
                        "categories": {
                            "Social Media": [],
                            "Professional": [],
                            "Content Creation": [],
                            "Gaming": [],
                            "Other": []
                        },
                        "detailed_metadata": {}
                    },
                    "image_metadata": None
                }
                
                # Map platforms to their URLs and categories
                for platform in ["Instagram", "Twitter", "Facebook", "TikTok", "LinkedIn", "Quora"]:
                    platform_results = automation_results.get(platform, [])
                    
                    for item in platform_results:
                        profile_url = item.get("url", "")
                        if profile_url:
                            # Add to profiles
                            converted_results["profiles"][platform] = profile_url
                            
                            # Categorize the platform
                            platform_category = "Social Media"  # Default
                            if platform in ["LinkedIn"]:
                                platform_category = "Professional"
                            elif platform in ["Quora"]:
                                platform_category = "Content Creation"
                            
                            # Add to categories if not already there
                            if platform not in converted_results["platform_metadata"]["categories"][platform_category]:
                                converted_results["platform_metadata"]["categories"][platform_category].append(platform)
                            
                            # Add detailed metadata
                            converted_results["platform_metadata"]["detailed_metadata"][platform] = {
                                "platform": platform,
                                "url": profile_url,
                                "username": item.get("secondary_text", ""),
                                "name": item.get("primary_text", ""),
                                "avatar_url": item.get("img_src", ""),
                                "bio": item.get("full_text", ""),
                                "connections": [],
                                "profile_id": hashlib.md5(profile_url.encode()).hexdigest()[:12]
                            }
                
                # Add web results to other relevant data
                web_results = automation_results.get("Web results", [])
                if web_results:
                    converted_results["web_results"] = web_results
                
                # Add usernames list
                usernames = automation_results.get("Usernames", [])
                if usernames:
                    converted_results["usernames"] = usernames
                
                # Add sponsored links
                sponsored = automation_results.get("Sponsored", {})
                if sponsored:
                    converted_results["sponsored_links"] = sponsored
                
                # Clean up temporary file if necessary
                try:
                    if os.path.exists(temp_json):
                        os.remove(temp_json)
                except:
                    pass
                
                return converted_results
            elif automation_results.get("metadata", {}).get("captcha_detected", False):
                logger.warning(f"CAPTCHA detected during automation for {username}")
            else:
                logger.warning(f"Automation failed for {username}: {automation_results.get('metadata', {}).get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error using automation for IDCrawl: {str(e)}")
            # Continue to fallback method
    
    # Fallback to direct scraping method
    logger.info(f"Using direct scraping method for IDCrawl search: {username}")
    scraper = IdCrawlScraper()
    return scraper.search_username(username)

def search_person_on_idcrawl(full_name, location=None, use_automation=True):
    """
    Search for a person by name and optional location on idcrawl.com
    
    Args:
        full_name (str): Person's full name
        location (str, optional): Location for filtering results
        use_automation (bool): Whether to use browser automation if available
        
    Returns:
        dict: Structured results from idcrawl.com
    """
    # First try automation if available and requested
    if use_automation and AUTOMATION_AVAILABLE and AUTOMATION_SCRIPT_AVAILABLE:
        try:
            logger.info(f"Using Playwright automation to search IDCrawl for: {full_name}")
            
            # Check if browser dependencies are available
            try:
                import tempfile
                import time
                import hashlib
                temp_json = os.path.join(tempfile.gettempdir(), f"idcrawl_{hashlib.md5(full_name.encode()).hexdigest()[:8]}_{int(time.time())}.json")
                
                # Run the search asynchronously with headless mode
                automation_results = asyncio.run(perform_search(
                    search_term=full_name,
                    state=location,  # Pass location as state parameter
                    json_output_path=temp_json,
                    browser_type="chromium",
                    block_resources_flag=True,
                    use_stealth=True,
                    headless=True  # Use headless mode to avoid system dependency issues
                ))
            except Exception as browser_error:
                if "missing dependencies" in str(browser_error).lower():
                    logger.warning(f"Browser dependencies missing: {str(browser_error)}")
                    # Create a special error result
                    return {
                        "success": False,
                        "error": "Browser automation dependencies missing. Install system libraries or use direct method.",
                        "requires_system_deps": True,
                        "missing_deps_error": str(browser_error),
                        "profiles": {},
                        "platform_metadata": {},
                        "image_metadata": None
                    }
                else:
                    # Re-raise for other types of errors
                    raise
            
            # Check if automation was successful - same conversion logic as above
            if automation_results.get("metadata", {}).get("success", False):
                logger.info(f"Successfully retrieved IDCrawl results for {full_name} via automation")
                
                # Convert automation results to the expected format (same as in search_username_on_idcrawl)
                converted_results = {
                    "success": True,
                    "search_term": full_name,
                    "profiles": {},
                    "platform_metadata": {
                        "categories": {
                            "Social Media": [],
                            "Professional": [],
                            "Content Creation": [],
                            "Gaming": [],
                            "Other": []
                        },
                        "detailed_metadata": {}
                    },
                    "image_metadata": None
                }
                
                # Map platforms to their URLs and categories
                for platform in ["Instagram", "Twitter", "Facebook", "TikTok", "LinkedIn", "Quora"]:
                    platform_results = automation_results.get(platform, [])
                    
                    for item in platform_results:
                        profile_url = item.get("url", "")
                        if profile_url:
                            # Add to profiles
                            converted_results["profiles"][platform] = profile_url
                            
                            # Categorize the platform
                            platform_category = "Social Media"  # Default
                            if platform in ["LinkedIn"]:
                                platform_category = "Professional"
                            elif platform in ["Quora"]:
                                platform_category = "Content Creation"
                            
                            # Add to categories if not already there
                            if platform not in converted_results["platform_metadata"]["categories"][platform_category]:
                                converted_results["platform_metadata"]["categories"][platform_category].append(platform)
                            
                            # Add detailed metadata
                            converted_results["platform_metadata"]["detailed_metadata"][platform] = {
                                "platform": platform,
                                "url": profile_url,
                                "username": item.get("secondary_text", ""),
                                "name": item.get("primary_text", ""),
                                "avatar_url": item.get("img_src", ""),
                                "bio": item.get("full_text", ""),
                                "connections": [],
                                "profile_id": hashlib.md5(profile_url.encode()).hexdigest()[:12]
                            }
                
                # Add web results to other relevant data
                web_results = automation_results.get("Web results", [])
                if web_results:
                    converted_results["web_results"] = web_results
                
                # Add usernames list
                usernames = automation_results.get("Usernames", [])
                if usernames:
                    converted_results["usernames"] = usernames
                
                # Add sponsored links
                sponsored = automation_results.get("Sponsored", {})
                if sponsored:
                    converted_results["sponsored_links"] = sponsored
                
                # Clean up temporary file if necessary
                try:
                    if os.path.exists(temp_json):
                        os.remove(temp_json)
                except:
                    pass
                
                return converted_results
            elif automation_results.get("metadata", {}).get("captcha_detected", False):
                logger.warning(f"CAPTCHA detected during automation for {full_name}")
            else:
                logger.warning(f"Automation failed for {full_name}: {automation_results.get('metadata', {}).get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error using automation for IDCrawl: {str(e)}")
            # Continue to fallback method
    
    # Fallback to direct scraping method
    logger.info(f"Using direct scraping method for IDCrawl search: {full_name}")
    scraper = IdCrawlScraper()
    return scraper.search_person(full_name, location)

def enrich_results_with_idcrawl(original_results, username=None, full_name=None, location=None, skip_idcrawl=False, use_automation=True):
    """
    Enrich existing search results with data from idcrawl.com
    
    Args:
        original_results (dict): Original search results to enrich
        username (str, optional): Username to search for
        full_name (str, optional): Person's full name
        location (str, optional): Location for filtering results
        skip_idcrawl (bool, optional): Skip idcrawl.com API calls (for testing or when CAPTCHA is known to be present)
        use_automation (bool, optional): Whether to attempt browser automation for bypassing CAPTCHA
        
    Returns:
        dict: Enriched search results
    """
    # Clone original results to avoid modifying the original
    enriched_results = original_results.copy()
    
    # If skipping idcrawl, add a warning and return original results
    if skip_idcrawl:
        if "warnings" not in enriched_results:
            enriched_results["warnings"] = []
        enriched_results["warnings"].append({
            "source": "idcrawl",
            "message": "IdCrawl.com integration was skipped (CAPTCHA protection is active)",
            "requires_captcha": True
        })
        logger.info("Skipping idcrawl.com integration due to CAPTCHA protection")
        return enriched_results
    
    # Check if we have automation available
    automation_status = "available" if AUTOMATION_AVAILABLE and AUTOMATION_SCRIPT_AVAILABLE else "unavailable"
    logger.info(f"IDCrawl automation is {automation_status} (use_automation={use_automation})")
    
    # Track which search method to use
    idcrawl_results = None
    
    if username:
        idcrawl_results = search_username_on_idcrawl(username, use_automation=use_automation)
    elif full_name:
        idcrawl_results = search_person_on_idcrawl(full_name, location, use_automation=use_automation)
    else:
        return original_results  # No search criteria provided
    
    # Check if the search was successful
    if not idcrawl_results.get("success", False):
        error_message = idcrawl_results.get('error', 'Unknown error')
        # Check if this is a CAPTCHA error
        if idcrawl_results.get("requires_captcha", False):
            logger.warning(f"IdCrawl search requires CAPTCHA verification: {error_message}")
            # Add the captcha warning to the enriched results
            if "warnings" not in enriched_results:
                enriched_results["warnings"] = []
            enriched_results["warnings"].append({
                "source": "idcrawl",
                "message": error_message,
                "requires_captcha": True
            })
            # Continue using only the original results
            return enriched_results
        else:
            logger.warning(f"IdCrawl search failed: {error_message}")
            return original_results
    
    # Merge profiles
    if "profiles" in original_results and "profiles" in idcrawl_results:
        for platform, url in idcrawl_results["profiles"].items():
            if platform not in original_results["profiles"]:
                enriched_results["profiles"][platform] = url
                logger.info(f"Added new profile from IdCrawl: {platform}")
    
    # Add or merge discovered data
    if "discovered_data" in original_results:
        if "platform_metadata" in idcrawl_results and "detailed_metadata" in idcrawl_results["platform_metadata"]:
            for platform, metadata in idcrawl_results["platform_metadata"]["detailed_metadata"].items():
                # Extract possible real names
                if "name" in metadata and metadata["name"]:
                    name = metadata["name"]
                    if name not in enriched_results["discovered_data"]["possible_real_names"]:
                        enriched_results["discovered_data"]["possible_real_names"].append(name)
                
                # Extract possible locations from bio text
                if "bio" in metadata and metadata["bio"]:
                    bio = metadata["bio"]
                    # Basic location extraction - could be improved with NLP
                    location_matches = re.findall(r'\b(?:from|in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', bio)
                    for loc in location_matches:
                        if loc not in enriched_results["discovered_data"]["possible_locations"]:
                            enriched_results["discovered_data"]["possible_locations"].append(loc)
                
                # Extract possible occupations from bio
                if "bio" in metadata and metadata["bio"]:
                    bio = metadata["bio"]
                    # Basic occupation extraction
                    occupation_matches = re.findall(r'\b(?:am\s+a|am\s+an|I\'m\s+a|I\'m\s+an|work\s+as\s+a|work\s+as\s+an)\s+([a-z]+(?:\s+[a-z]+){0,2})', bio, re.I)
                    for occ in occupation_matches:
                        if occ not in enriched_results["discovered_data"]["possible_occupations"]:
                            enriched_results["discovered_data"]["possible_occupations"].append(occ)
    
    # Add image data if available and not already present
    if "image_metadata" in idcrawl_results and idcrawl_results["image_metadata"]:
        if "image_metadata" not in enriched_results or not enriched_results["image_metadata"]:
            enriched_results["image_metadata"] = idcrawl_results["image_metadata"]
    
    # Update confidence if more profiles were found
    if "confidence" in original_results:
        original_profile_count = len(original_results.get("profiles", {}))
        new_profile_count = len(enriched_results.get("profiles", {}))
        
        if new_profile_count > original_profile_count:
            # Boost confidence based on additional profiles found
            additional_profiles = new_profile_count - original_profile_count
            confidence_boost = min(0.2, additional_profiles * 0.04)  # Up to 0.2 boost
            enriched_results["confidence"] = min(1.0, original_results.get("confidence", 0) + confidence_boost)
    
    return enriched_results


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        logger.info(f"Searching idcrawl.com for: {search_term}")
        
        results = search_username_on_idcrawl(search_term)
        
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python idcrawl_scraper.py <username or name>")