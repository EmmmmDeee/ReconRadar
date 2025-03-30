import requests
import threading
import time
from datetime import datetime
import logging
from urllib.parse import quote_plus, urlparse
import json
import re
from bs4 import BeautifulSoup
import trafilatura
import hashlib

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Constants
VERSION = '1.1.2'
TIMEOUT_SECONDS = 5  # Balanced timeout for better results
MAX_THREADS = 15  # Increased threads for more parallel processing
MAX_PLATFORMS = 40  # Increased platforms to get more results
METADATA_TIMEOUT = 2  # Slightly increased metadata timeout for better extraction
ENABLE_METADATA_EXTRACTION = True  # Toggle to enable/disable metadata extraction

def validate_image_url(url):
    """
    Validate if a URL points to a valid image with enhanced validation.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        dict: Dictionary with validation result, direct image URL, and metadata
    """
    if not url:
        return {"valid": False, "error": "No URL provided", "direct_url": None}
    
    # Common image file extensions
    IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg']
    
    # Common image hosting domains with validation rules
    IMAGE_HOSTS = {
        'imgur.com': {'pattern': r'https?://(i\.)?imgur\.com/(\w+)(\.\w+)?', 'direct_format': 'https://i.imgur.com/{0}.jpg'},
        'i.imgur.com': {'pattern': r'https?://i\.imgur\.com/(\w+)(\.\w+)?', 'direct_format': 'https://i.imgur.com/{0}.jpg'},
        'prnt.sc': {'pattern': r'https?://prnt\.sc/(\w+)', 'direct_format': 'https://prnt.sc/{0}'},
        'ibb.co': {'pattern': r'https?://(i\.)?ibb\.co/(\w+)/(\w+)(\.\w+)?', 'direct_format': None}, 
        'postimg.cc': {'pattern': r'https?://(i\.)?postimg\.cc/(\w+)/(\w+)(\.\w+)?', 'direct_format': None},
        'instagram.com': {'pattern': r'https?://www\.instagram\.com/p/(\w+)', 'direct_format': None},
        'facebook.com': {'pattern': r'https?://www\.facebook\.com/(photo|share)', 'direct_format': None},
    }
    
    # Initialize result
    result = {
        "valid": False,
        "direct_url": None,
        "content_type": None,
        "file_extension": None,
        "source": "unknown",
        "error": None
    }
    
    try:
        # Check for direct image URL based on extension
        url_lower = url.lower()
        if any(url_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
            # Looks like a direct image URL, try to validate it
            result["source"] = "direct"
            result["direct_url"] = url
            
        # Check if it's from a known image hosting service
        else:
            for host, rules in IMAGE_HOSTS.items():
                if host in url_lower:
                    result["source"] = host
                    import re
                    if rules['pattern'] and rules['direct_format']:
                        match = re.match(rules['pattern'], url)
                        if match:
                            # Create direct URL for known hosting services
                            result["direct_url"] = rules['direct_format'].format(match.group(1))
                    else:
                        # Use original URL for hosts without direct URL pattern
                        result["direct_url"] = url
        
        # No direct URL detected, use original
        if not result["direct_url"]:
            result["direct_url"] = url
            
        # Now validate by actually sending a request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        }
        
        # Some services block HEAD requests, try GET with stream=True instead
        response = requests.get(result["direct_url"], headers=headers, timeout=TIMEOUT_SECONDS, stream=True, 
                               allow_redirects=True)
        
        # Check if response status is successful
        if response.status_code == 200:
            # Get the final URL after any redirects
            result["direct_url"] = response.url
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            result["content_type"] = content_type
            
            # Only download a small portion to check content
            content_chunk = next(response.iter_content(chunk_size=1024), None)
            
            # Validate by content type or extension
            if content_type.startswith('image/') or any(url_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
                result["valid"] = True
                
                # Extract file extension from content-type if available
                if content_type.startswith('image/'):
                    extension = content_type.split('/')[1].split(';')[0]
                    result["file_extension"] = extension
                    
            else:
                result["error"] = f"Not an image (content-type: {content_type})"
                
        else:
            result["error"] = f"Failed to access image URL (status code: {response.status_code})"
    
    except requests.exceptions.Timeout:
        result["error"] = "Request timed out when checking image"
    except requests.exceptions.TooManyRedirects:
        result["error"] = "Too many redirects when following image URL" 
    except requests.exceptions.RequestException as e:
        result["error"] = f"Error accessing image URL: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error validating image URL: {str(e)}"
        logging.error(f"Error validating image URL: {e}")
    
    logging.info(f"Image validation result: {result}")
    return result

def check_platform(username, platform, url, results, stats_lock, platform_stats, variations=None):
    """
    Check if a username exists on a specific platform with improved validation.
    
    Args:
        username (str): Username to check
        platform (str): Platform name
        url (str): URL to check
        results (dict): Dictionary to store results
        stats_lock (threading.Lock): Lock for updating platform stats
        platform_stats (dict): Dictionary to store platform statistics
        variations (list, optional): List of username variations to try if the main username fails
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    start_time = time.time()
    
    try:
        # Use allow_redirects=True to follow redirects and get the final destination
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Store response metadata including text for metadata extraction
        with stats_lock:
            platform_stats[platform] = {
                'response_time': response_time,
                'status_code': response.status_code,
                'final_url': response.url,
                'response_text': response.text if ENABLE_METADATA_EXTRACTION else None
            }
        
        # Define platform-specific validation patterns
        login_indicators = [
            "login", "signin", "sign-in", "register", "signup", "auth", 
            "authenticate", "account", "passw", "404", "not found"
        ]
        
        # Platform-specific error patterns that indicate profile doesn't exist
        error_indicators = {
            "Instagram": ["accounts/login", "Page Not Found", "Sorry, this page", "isn't available"],
            "Twitter": ["account doesn't exist", "user not found", "suspended", "doesn't exist"],
            "Facebook": ["login/?next=", "content not found", "isn't available", "page not found"],
            "LinkedIn": ["authwall", "sign up", "join linkedin", "page doesn't exist"],
            "GitHub": ["404 not found", "page not found", "not available"],
            "Telegram": ["join telegram", "preview channel", "/404"],
            "Discord": ["404", "NOT FOUND", "not found"],
            "Medium": ["not found", "error", "link is broken"],
            "TikTok": ["couldn't find this account", "page unavailable"],
            "Pinterest": ["couldn't find that page", "page unavailable"],
            "Twitch": ["sorry", "time machine", "unavailable"],
            "Trello": ["page not found", "This page doesn't exist"],
            "VSCO": ["404 Not Found", "doesn't exist", "page could not be found"],
            "CodePen": ["404", "not found"],
            "YouTube": ["404", "not available", "doesn't exist"],
            "Reddit": ["sorry", "nobody", "goes by that name"],
            "Snapchat": ["page could not be found"],
            "Behance": ["sorry", "we couldn't find", "not found"],
            "Vero": ["404", "not found"],
            "Hackernoon": ["404", "not found", "page could not be found"],
            "HackerRank": ["Oops", "page you're looking for", "not found"],
            "Gist": ["not found", "404", "doesn't exist"]
        }
        
        # For platforms not in error_indicators, use generic patterns
        generic_error_patterns = ["404", "not found", "doesn't exist", "page unavailable", "no such user"]
        
        # Check for login or registration redirection (suspicious)
        redirected_to_login = any(indicator in response.url.lower() for indicator in login_indicators)
        
        # Check for error messages in content
        has_error_indicators = False
        if platform in error_indicators:
            has_error_indicators = any(indicator.lower() in response.text.lower() for indicator in error_indicators[platform])
        else:
            has_error_indicators = any(pattern.lower() in response.text.lower() for pattern in generic_error_patterns)
        
        # Special platform-specific validation
        if platform == "Instagram" and ("accounts/login" in response.url or "login" in response.url):
            profile_exists = False
        elif platform == "Facebook" and ("login" in response.url or "/login/" in response.url):
            profile_exists = False
        elif platform == "LinkedIn" and ("authwall" in response.url or "login" in response.url):
            profile_exists = False
        elif platform == "Codechef" and response.status_code == 302:
            # Codechef returns 302 for existing profiles
            profile_exists = True
        else:
            # Default validation logic
            profile_exists = (response.status_code == 200 and not has_error_indicators and not redirected_to_login)
            
            # Additional check for platforms known to return 200 for non-existent profiles
            if profile_exists and platform in ["Twitter", "Instagram", "Facebook"]:
                # Look for clear profile indicators like 'followers', 'tweets', etc.
                profile_indicators = ["followers", "following", "tweets", "posts", "photos", "profile"]
                profile_exists = any(indicator in response.text.lower() for indicator in profile_indicators)
        
        # Update platform stats with validation info
        with stats_lock:
            platform_stats[platform]['validated'] = profile_exists
            platform_stats[platform]['variation_used'] = username
        
        if profile_exists:
            logging.debug(f"Profile found on {platform}: {url}")
            results[platform] = url
            return True  # Profile found, no need to try variations
        else:
            logging.debug(f"Profile not found on {platform} with primary username")
            
            # Try username variations if provided and initial check failed
            if variations:
                found = try_username_variations(platform, variations, results, stats_lock, platform_stats)
                if found:
                    return True  # Found with a variation
            
            # If we reach here, no profile was found with any variation
            results[platform] = None
            return False

    except requests.exceptions.Timeout:
        logging.warning(f"Timeout while checking {platform}")
        with stats_lock:
            platform_stats[platform] = {
                'response_time': TIMEOUT_SECONDS,
                'status_code': 'timeout'
            }
        results[platform] = None
        return False
        
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while checking {platform}: {e}")
        with stats_lock:
            platform_stats[platform] = {
                'response_time': time.time() - start_time,
                'status_code': 'error',
                'error': str(e)
            }
        results[platform] = None
        return False

def try_username_variations(platform, variations, results, stats_lock, platform_stats):
    """
    Try different username variations for a platform.
    
    Args:
        platform (str): Platform name
        variations (list): List of username variations to try
        results (dict): Dictionary to store results
        stats_lock (threading.Lock): Lock for updating platform stats
        platform_stats (dict): Dictionary to store platform statistics
        
    Returns:
        bool: True if a profile is found with any variation, False otherwise
    """
    # Skip the first variation as it's the primary username already checked
    for var in variations[1:]:
        # Clean variation to ensure it's valid for URLs
        clean_var = re.sub(r'[^\w.-]', '', var)
        
        # Generate the URL for this platform with this variation
        var_url = ""
        
        # Common URL patterns based on platform
        if platform == "Instagram":
            var_url = f"https://www.instagram.com/{clean_var}/"
        elif platform == "Twitter":
            var_url = f"https://twitter.com/{clean_var}"
        elif platform == "GitHub":
            var_url = f"https://github.com/{clean_var}"
        elif platform == "Telegram":
            var_url = f"https://t.me/{clean_var}"
        elif platform == "TikTok":
            var_url = f"https://www.tiktok.com/@{clean_var}"
        elif platform == "Facebook":
            var_url = f"https://www.facebook.com/{clean_var}"
        elif platform == "LinkedIn":
            var_url = f"https://www.linkedin.com/in/{clean_var}/"
        elif platform == "Pinterest":
            var_url = f"https://www.pinterest.com/{clean_var}"
        elif platform == "Snapchat":
            var_url = f"https://www.snapchat.com/add/{clean_var}"
        elif platform == "Linktr.ee":
            var_url = f"https://linktr.ee/{clean_var}"
        elif platform == "Gitlab":
            var_url = f"https://gitlab.com/{clean_var}"
        elif platform == "Reddit":
            var_url = f"https://www.reddit.com/user/{clean_var}"
        elif platform == "YouTube":
            var_url = f"https://www.youtube.com/user/{clean_var}"
        elif platform == "Tumblr":
            var_url = f"https://{clean_var}.tumblr.com"
        elif platform == "Vimeo":
            var_url = f"https://vimeo.com/{clean_var}"
        elif platform == "SoundCloud":
            var_url = f"https://soundcloud.com/{clean_var}"
        elif platform == "Flickr":
            var_url = f"https://www.flickr.com/people/{clean_var}/"
        elif platform == "Dribbble":
            var_url = f"https://dribbble.com/{clean_var}"
        elif platform == "Medium":
            var_url = f"https://medium.com/@{clean_var}"
        elif platform == "DeviantArt":
            var_url = f"https://{clean_var}.deviantart.com"
        elif platform == "Quora":
            var_url = f"https://www.quora.com/profile/{clean_var}"
        elif platform == "Steam":
            var_url = f"https://steamcommunity.com/id/{clean_var}"
        elif platform == "Discord":
            var_url = f"https://discord.com/users/{clean_var}"
        elif platform == "Twitch":
            var_url = f"https://www.twitch.tv/{clean_var}"
        elif platform == "HackerRank":
            var_url = f"https://hackerrank.com/{clean_var}"
        elif platform == "Hackernoon":
            var_url = f"https://hackernoon.com/u/{clean_var}"
        elif platform == "Trello":
            var_url = f"https://trello.com/{clean_var}"
        elif platform == "Codechef":
            var_url = f"https://www.codechef.com/users/{clean_var}"
        elif platform == "Gist":
            var_url = f"https://gist.github.com/{clean_var}"
        # Add more platform-specific URL patterns here
        else:
            # For others, construct a generic URL if we can determine the pattern
            # Try to extract the pattern from the original URL
            if platform in results and results[platform] and "://" in results[platform]:
                original_url = results[platform]
                # Find where the username appears in the URL
                parts = original_url.split('/')
                for i, part in enumerate(parts):
                    if part and part.lower() == clean_var.lower():
                        # Replace that part with the new username variation
                        parts[i] = clean_var
                        var_url = '/'.join(parts)
                        break
        
        # Skip if we couldn't generate a URL
        if not var_url:
            continue
            
        # Now check this variation using the same validation as the main check_platform function
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            start_time = time.time()
            response = requests.get(var_url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=True)
            response_time = time.time() - start_time
            
            # Define platform-specific validation patterns (same as in check_platform)
            login_indicators = [
                "login", "signin", "sign-in", "register", "signup", "auth", 
                "authenticate", "account", "passw", "404", "not found"
            ]
            
            # Platform-specific error patterns that indicate profile doesn't exist
            error_indicators = {
                "Instagram": ["accounts/login", "Page Not Found", "Sorry, this page", "isn't available"],
                "Twitter": ["account doesn't exist", "user not found", "suspended", "doesn't exist"],
                "Facebook": ["login/?next=", "content not found", "isn't available", "page not found"],
                "LinkedIn": ["authwall", "sign up", "join linkedin", "page doesn't exist"],
                "GitHub": ["404 not found", "page not found", "not available"],
                "Telegram": ["join telegram", "preview channel", "/404"],
                "Discord": ["404", "NOT FOUND", "not found"],
                "Medium": ["not found", "error", "link is broken"],
                "TikTok": ["couldn't find this account", "page unavailable"],
                "Pinterest": ["couldn't find that page", "page unavailable"],
                "Twitch": ["sorry", "time machine", "unavailable"],
                "Trello": ["page not found", "This page doesn't exist"],
                "VSCO": ["404 Not Found", "doesn't exist", "page could not be found"],
                "CodePen": ["404", "not found"],
                "Gist": ["not found", "404", "doesn't exist"]
            }
            
            # For platforms not in error_indicators, use generic patterns
            generic_error_patterns = ["404", "not found", "doesn't exist", "page unavailable", "no such user"]
            
            # Check for login or registration redirection (suspicious)
            redirected_to_login = any(indicator in response.url.lower() for indicator in login_indicators)
            
            # Check for error messages in content
            has_error_indicators = False
            if platform in error_indicators:
                has_error_indicators = any(indicator.lower() in response.text.lower() for indicator in error_indicators[platform])
            else:
                has_error_indicators = any(pattern.lower() in response.text.lower() for pattern in generic_error_patterns)
            
            # Profile validation logic, same as in check_platform
            profile_exists = False
            
            # Special platform-specific validation
            if platform == "Instagram" and ("accounts/login" in response.url or "login" in response.url):
                profile_exists = False
            elif platform == "Facebook" and ("login" in response.url or "/login/" in response.url):
                profile_exists = False
            elif platform == "LinkedIn" and ("authwall" in response.url or "login" in response.url):
                profile_exists = False
            elif platform == "Codechef" and response.status_code == 302:
                # Codechef returns 302 for existing profiles
                profile_exists = True
            else:
                # Default validation logic
                profile_exists = (response.status_code == 200 and not has_error_indicators and not redirected_to_login)
                
                # Additional check for platforms known to return 200 for non-existent profiles
                if profile_exists and platform in ["Twitter", "Instagram", "Facebook"]:
                    # Look for clear profile indicators like 'followers', 'tweets', etc.
                    profile_indicators = ["followers", "following", "tweets", "posts", "photos", "profile"]
                    profile_exists = any(indicator in response.text.lower() for indicator in profile_indicators)
            
            if profile_exists:
                logging.debug(f"Profile found on {platform} with variation '{var}': {var_url}")
                
                # Update results and stats
                results[platform] = var_url
                with stats_lock:
                    platform_stats[platform] = {
                        'response_time': response_time,
                        'status_code': response.status_code,
                        'variation_used': var,
                        'validated': True,
                        'final_url': response.url,
                        'response_text': response.text if ENABLE_METADATA_EXTRACTION else None
                    }
                return True
                
        except Exception as e:
            logging.debug(f"Error checking variation '{var}' on {platform}: {e}")
            continue
    
    return False

def extract_profile_metadata(platform, url, response_text=None):
    """
    Extract metadata from a social media profile.
    
    Args:
        platform (str): Platform name
        url (str): URL of the profile
        response_text (str, optional): HTML content of the profile page if already fetched
        
    Returns:
        dict: Dictionary containing extracted metadata
    """
    # Use a shorter timeout to prevent worker process from hanging
    global METADATA_TIMEOUT
    # Initialize metadata dictionary
    metadata = {
        "platform": platform,
        "url": url,
        "username": None,
        "name": None,
        "bio": None,
        "followers_count": None,
        "following_count": None,
        "posts_count": None,
        "location": None,
        "website": None,
        "join_date": None,
        "avatar_url": None,
        "banner_url": None,
        "verified": None,
        "last_active": None,
        "connections": [],
        "profile_id": None,
        "content_sample": []
    }
    
    # Skip extraction if disabled
    if not ENABLE_METADATA_EXTRACTION:
        return metadata
    
    # Get HTML content if not provided
    html_content = response_text
    if not html_content:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=METADATA_TIMEOUT)
            if response.status_code == 200:
                html_content = response.text
            else:
                return metadata  # Return empty metadata if can't fetch content
        except Exception as e:
            logging.error(f"Error fetching profile content for {platform}: {e}")
            return metadata
    
    if not html_content:
        return metadata
        
    try:
        # Extract username from URL
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) > 0:
            metadata["username"] = path_parts[-1]
            # Some platforms have @ in usernames
            if metadata["username"].startswith('@'):
                metadata["username"] = metadata["username"][1:]
        
        # Create a unique profile ID using hash
        profile_hash = hashlib.md5(url.encode()).hexdigest()
        metadata["profile_id"] = f"{platform.lower()}_{profile_hash[:8]}"
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract cleaned text with trafilatura for content sample
        try:
            # Set a very short timeout for trafilatura to prevent worker timeouts
            cleaned_text = trafilatura.extract(html_content, include_comments=False, include_tables=False, include_images=False, include_links=False)
            if cleaned_text:
                # Get a sample of content (first 500 chars)
                metadata["content_sample"] = cleaned_text[:500].strip()
        except Exception as e:
            logging.warning(f"Failed to extract content with trafilatura: {e}")
            # Fallback to a simple text extraction from the first paragraph
            try:
                paragraphs = soup.find_all('p')
                if paragraphs and len(paragraphs) > 0:
                    metadata["content_sample"] = paragraphs[0].get_text(strip=True)[:500]
            except:
                pass
        
        # Platform-specific extraction logic
        if platform == "Twitter":
            # Extract name
            name_elem = soup.select_one('h1[data-testid="primaryColumn"] span')
            if name_elem:
                metadata["name"] = name_elem.get_text(strip=True)
            
            # Extract bio
            bio_elem = soup.select_one('div[data-testid="primaryColumn"] div[data-testid="UserDescription"]')
            if bio_elem:
                metadata["bio"] = bio_elem.get_text(strip=True)
            
            # Extract follower counts
            followers_elem = soup.select_one('a[href*="/followers"] span')
            if followers_elem:
                followers_text = followers_elem.get_text(strip=True)
                metadata["followers_count"] = followers_text
            
            # Extract following count
            following_elem = soup.select_one('a[href*="/following"] span')
            if following_elem:
                following_text = following_elem.get_text(strip=True)
                metadata["following_count"] = following_text
                
            # Extract avatar
            avatar_elem = soup.select_one('img[src*="profile_images"]')
            if avatar_elem and avatar_elem.has_attr('src'):
                metadata["avatar_url"] = avatar_elem['src']
                
            # Check verification
            verified_elem = soup.select_one('svg[data-testid="icon-verified"]')
            metadata["verified"] = verified_elem is not None
                
        elif platform == "Instagram":
            # Instagram often redirects to login, but we can try to extract from meta tags
            meta_title = soup.select_one('meta[property="og:title"]')
            if meta_title and meta_title.has_attr('content'):
                title_content = meta_title['content']
                if isinstance(title_content, str) and '•' in title_content:
                    metadata["name"] = title_content.split('•')[0].strip()
                else:
                    metadata["name"] = title_content
                
            # Try to get bio from meta description
            meta_desc = soup.select_one('meta[property="og:description"]')
            if meta_desc and meta_desc.has_attr('content'):
                desc_text = meta_desc['content']
                if isinstance(desc_text, str):  # Ensure desc_text is a string
                    # Extract follower count if available
                    follower_match = re.search(r'(\d+(?:\.\d+)?[km]?) Followers', desc_text, re.IGNORECASE)
                    if follower_match:
                        metadata["followers_count"] = follower_match.group(1)
                    # Extract bio
                    metadata["bio"] = desc_text
                
            # Get avatar from meta image
            meta_image = soup.select_one('meta[property="og:image"]')
            if meta_image and meta_image.has_attr('content'):
                metadata["avatar_url"] = meta_image['content']
                
        elif platform == "GitHub":
            # Extract name
            name_elem = soup.select_one('span.p-name.vcard-fullname')
            if name_elem:
                metadata["name"] = name_elem.get_text(strip=True)
                
            # Extract bio
            bio_elem = soup.select_one('div.p-note.user-profile-bio')
            if bio_elem:
                metadata["bio"] = bio_elem.get_text(strip=True)
                
            # Extract follower counts
            followers_elem = soup.select_one('span.text-bold.color-fg-default')
            if followers_elem:
                metadata["followers_count"] = followers_elem.get_text(strip=True)
                
            # Extract location
            location_elem = soup.select_one('li[itemprop="homeLocation"] span.p-label')
            if location_elem:
                metadata["location"] = location_elem.get_text(strip=True)
                
            # Extract website
            website_elem = soup.select_one('li[itemprop="url"] a')
            if website_elem and website_elem.has_attr('href'):
                metadata["website"] = website_elem['href']
                
            # Extract join date
            join_elem = soup.select_one('relative-time')
            if join_elem and join_elem.has_attr('datetime'):
                metadata["join_date"] = join_elem['datetime']
                
            # Extract avatar
            avatar_elem = soup.select_one('img.avatar.avatar-user')
            if avatar_elem and avatar_elem.has_attr('src'):
                metadata["avatar_url"] = avatar_elem['src']
                
        elif platform == "LinkedIn":
            # LinkedIn is usually heavily restricted, but try meta tags
            meta_title = soup.select_one('meta[property="og:title"]')
            if meta_title and meta_title.has_attr('content'):
                metadata["name"] = meta_title['content']
                
            meta_desc = soup.select_one('meta[property="og:description"]')
            if meta_desc and meta_desc.has_attr('content'):
                metadata["bio"] = meta_desc['content']
                
            meta_image = soup.select_one('meta[property="og:image"]')
            if meta_image and meta_image.has_attr('content'):
                metadata["avatar_url"] = meta_image['content']
                
        elif platform == "TikTok":
            # Extract name
            name_elem = soup.select_one('h2.tiktok-arkop9-h2')
            if name_elem:
                metadata["name"] = name_elem.get_text(strip=True)
                
            # Extract bio
            bio_elem = soup.select_one('h2.tiktok-arkop9-h2 + span')
            if bio_elem:
                metadata["bio"] = bio_elem.get_text(strip=True)
                
            # Extract follower count
            follower_count = soup.select_one('strong[title="Followers"]')
            if follower_count:
                metadata["followers_count"] = follower_count.get_text(strip=True)
                
            # Extract following count
            following_count = soup.select_one('strong[title="Following"]')
            if following_count:
                metadata["following_count"] = following_count.get_text(strip=True)
                
            # Extract likes count
            likes_count = soup.select_one('strong[title="Likes"]')
            if likes_count:
                metadata["likes_count"] = likes_count.get_text(strip=True)
                
            # Extract profile image
            avatar_elem = soup.select_one('img.tiktok-uha12h-img')
            if avatar_elem and avatar_elem.has_attr('src'):
                metadata["avatar_url"] = avatar_elem['src']
                
            # Verification
            verified_badge = soup.select_one('svg.tiktok-shsbhf-svgverifiedbadge')
            metadata["verified"] = verified_badge is not None
                
        # Add platform-specific extraction for other platforms as needed
        
        # Generic extraction from meta tags (works for many platforms)
        if not metadata["name"]:
            meta_name = soup.select_one('meta[property="og:title"], meta[name="twitter:title"]')
            if meta_name and meta_name.has_attr('content'):
                metadata["name"] = meta_name['content']
                
        if not metadata["bio"]:
            meta_desc = soup.select_one('meta[property="og:description"], meta[name="twitter:description"], meta[name="description"]')
            if meta_desc and meta_desc.has_attr('content'):
                metadata["bio"] = meta_desc['content']
                
        if not metadata["avatar_url"]:
            meta_image = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
            if meta_image and meta_image.has_attr('content'):
                metadata["avatar_url"] = meta_image['content']
        
        # Remove None values for cleaner output
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        return metadata
        
    except Exception as e:
        logging.error(f"Error extracting metadata for {platform}: {str(e)}")
        return metadata  # Return partially filled metadata

def categorize_platforms(platforms):
    """
    Categorize platforms into groups based on type.
    
    Args:
        platforms (dict): Dictionary of platforms and URLs
        
    Returns:
        dict: Dictionary of platform categories
    """
    categories = {
        'Social Media': ['Instagram', 'Twitter', 'Facebook', 'LinkedIn', 'Pinterest', 'TikTok', 'Snapchat', 'Reddit'],
        'Professional': ['LinkedIn', 'GitHub', 'Gitlab', 'AngelList', 'Behance', 'Dribbble', 'Freelancer', 'Fiverr', 'Dev.to', 'Replit', 'CodePen'],
        'Content Creation': ['YouTube', 'Twitch', 'Medium', 'Blogger', 'WordPress', 'Tumblr', 'Blogspot', 'Vimeo', 'SoundCloud'],
        'Shopping': ['Etsy', 'Ebay', 'Amazon'],
        'Gaming': ['Steam', 'Twitch', 'Discord'],
        'Arts & Entertainment': ['DeviantArt', 'Flickr', 'Giphy', '500px', 'Dribbble', 'Behance', 'Letterboxd', 'IMDb'],
        'Other': []
    }
    
    # Create a reverse lookup to categorize all platforms
    platform_categories = {}
    for platform in platforms.keys():
        categorized = False
        for category, platform_list in categories.items():
            if platform in platform_list:
                platform_categories[platform] = category
                categorized = True
                break
        
        if not categorized:
            platform_categories[platform] = 'Other'
    
    return platform_categories

def generate_username_variations(username):
    """
    Generate common variations of a username that people often use across platforms.
    
    Args:
        username (str): Base username to generate variations from
        
    Returns:
        list: List of username variations
    """
    variations = [username]  # Start with the original
    
    # Step 1: Check if the username contains separators
    has_dot = '.' in username
    has_underscore = '_' in username
    has_dash = '-' in username
    has_space = ' ' in username
    
    # Step 2: Generate base variations without special characters
    # Remove all separators
    clean_base = re.sub(r'[^\w]', '', username)
    if clean_base != username:
        variations.append(clean_base)
    
    # Step 3: Split the username into parts by separators
    parts = re.split(r'[._\-\s]', username)
    if len(parts) > 1:  # Only process if there are actual parts
        
        # Step 4: Generate variations with different separators
        # Dots
        if not has_dot:
            variations.append('.'.join(parts))
        
        # Underscores
        if not has_underscore:
            variations.append('_'.join(parts))
        
        # Dashes
        if not has_dash:
            variations.append('-'.join(parts))
        
        # No separators (concat)
        variations.append(''.join(parts))
        
        # Capitalize each part
        variations.append('.'.join([p.capitalize() for p in parts]))
        variations.append('_'.join([p.capitalize() for p in parts]))
        variations.append(''.join([p.capitalize() for p in parts]))
        
        # First part only
        if len(parts[0]) > 3:  # Only use first part if it's substantial
            variations.append(parts[0])
        
        # First and last parts only with dot
        if len(parts) > 2:
            variations.append(f"{parts[0]}.{parts[-1]}")
            variations.append(f"{parts[0]}_{parts[-1]}")
    
    # Step 5: Generate common replacements
    # Replace dots
    if has_dot:
        variations.append(username.replace('.', '_'))
        variations.append(username.replace('.', '-'))
        variations.append(username.replace('.', ''))
    
    # Replace underscores
    if has_underscore:
        variations.append(username.replace('_', '.'))
        variations.append(username.replace('_', '-'))
        variations.append(username.replace('_', ''))
    
    # Replace dashes
    if has_dash:
        variations.append(username.replace('-', '.'))
        variations.append(username.replace('-', '_'))
        variations.append(username.replace('-', ''))
    
    # Replace spaces (if any)
    if has_space:
        variations.append(username.replace(' ', '.'))
        variations.append(username.replace(' ', '_'))
        variations.append(username.replace(' ', '-'))
        variations.append(username.replace(' ', ''))
    
    # Step 6: Case variations
    # Original already in the list, try other cases
    if username.islower():
        variations.append(username.upper())
        variations.append(username.capitalize())
    elif username.isupper():
        variations.append(username.lower())
    else:
        variations.append(username.lower())
        variations.append(username.upper())
    
    # Step 7: Common username patterns
    # Add 'real' prefix (common for some platforms)
    if not username.startswith('real'):
        variations.append(f"real{username}")
    
    # Add 'the' prefix (common for some platforms)
    if not username.startswith('the'):
        variations.append(f"the{username}")
    
    # Add common number suffixes (used when preferred username is taken)
    variations.append(f"{username}1")
    variations.append(f"{username}123")
    variations.append(f"{username}_official")
    
    # Step 8: Remove duplicates while preserving order
    unique_variations = []
    seen = set()
    for var in variations:
        clean_var = var.strip()
        if clean_var and clean_var not in seen and len(clean_var) > 2:  # Avoid empty or very short variations
            unique_variations.append(clean_var)
            seen.add(clean_var)
    
    return unique_variations

def check_social_media(username, image_link=None):
    """
    Check social media platforms for a username and generate reverse image search links.
    
    Args:
        username (str): The username to search for
        image_link (str, optional): URL to an image for reverse image search
        
    Returns:
        tuple: (results, stats, reverse_image_urls, platform_metadata, image_metadata)
    """
    # Ensure we only check a limited number of platforms to prevent worker timeouts
    global MAX_PLATFORMS, TIMEOUT_SECONDS, MAX_THREADS
    # Generate username variations
    username_variations = generate_username_variations(username)
    
    # Use the provided username as primary and clean it
    primary_username = username
    clean_username = re.sub(r'[^\w.-]', '', username)
    
    # Dictionary mapping platform names to their URL patterns
    platforms = {
        "Instagram": f"https://www.instagram.com/{clean_username}/",
        "Twitter": f"https://twitter.com/{clean_username}",
        "Facebook": f"https://www.facebook.com/{clean_username}",
        "LinkedIn": f"https://www.linkedin.com/in/{clean_username}/",
        "Pinterest": f"https://www.pinterest.com/{clean_username}",
        "TikTok": f"https://www.tiktok.com/@{clean_username}",
        "Snapchat": f"https://www.snapchat.com/add/{clean_username}",
        "Linktr.ee": f"https://linktr.ee/{clean_username}",
        "GitHub": f"https://github.com/{clean_username}",
        "Gitlab": f"https://gitlab.com/{clean_username}",
        "Reddit": f"https://www.reddit.com/user/{clean_username}",
        "YouTube": f"https://www.youtube.com/user/{clean_username}",
        "Tumblr": f"https://{clean_username}.tumblr.com",
        "Vimeo": f"https://vimeo.com/{clean_username}",
        "SoundCloud": f"https://soundcloud.com/{clean_username}",
        "Flickr": f"https://www.flickr.com/people/{clean_username}/",
        "Dribbble": f"https://dribbble.com/{clean_username}",
        "Medium": f"https://medium.com/@{clean_username}",
        "DeviantArt": f"https://{clean_username}.deviantart.com",
        "Quora": f"https://www.quora.com/profile/{clean_username}",
        "Mix": f"https://mix.com/{clean_username}",
        "Meetup": f"https://www.meetup.com/members/{clean_username}",
        "Goodreads": f"https://www.goodreads.com/user/show/{clean_username}",
        "Fiverr": f"https://www.fiverr.com/{clean_username}",
        "Wattpad": f"https://www.wattpad.com/user/{clean_username}",
        "Steam": f"https://steamcommunity.com/id/{clean_username}",
        "Viber": f"https://chats.viber.com/{clean_username}",
        "Slack": f"https://{clean_username}.slack.com",
        "Xing": f"https://www.xing.com/profile/{clean_username}",
        "Canva": f"https://www.canva.com/{clean_username}",
        "500px": f"https://500px.com/{clean_username}",
        "Last.fm": f"https://www.last.fm/user/{clean_username}",
        "Foursquare": f"https://foursquare.com/user/{clean_username}",
        "Kik": f"https://kik.me/{clean_username}",
        "Patreon": f"https://www.patreon.com/{clean_username}",
        "Periscope": f"https://www.pscp.tv/{clean_username}",
        "Twitch": f"https://www.twitch.tv/{clean_username}",
        "Steemit": f"https://steemit.com/@{clean_username}",
        "Vine": f"https://vine.co/u/{clean_username}",
        "Keybase": f"https://keybase.io/{clean_username}",
        "Zillow": f"https://www.zillow.com/profile/{clean_username}",
        "TripAdvisor": f"https://www.tripadvisor.com/members/{clean_username}",
        "Crunchyroll": f"https://www.crunchyroll.com/user/{clean_username}",
        "Trello": f"https://trello.com/{clean_username}",
        "Vero": f"https://www.vero.co/{clean_username}",
        "CodePen": f"https://codepen.io/{clean_username}",
        "About.me": f"https://about.me/{clean_username}",
        "Trakt": f"https://www.trakt.tv/users/{clean_username}",
        "Couchsurfing": f"https://www.couchsurfing.com/people/{clean_username}",
        "Behance": f"https://www.behance.net/{clean_username}",
        "Etsy": f"https://www.etsy.com/shop/{clean_username}",
        "Ebay": f"https://www.ebay.com/usr/{clean_username}",
        "Bandcamp": f"https://bandcamp.com/{clean_username}",
        "AngelList": f"https://angel.co/u/{clean_username}",
        "Ello": f"https://ello.co/{clean_username}",
        "Gravatar": f"https://en.gravatar.com/{clean_username}",
        "Instructables": f"https://www.instructables.com/member/{clean_username}",
        "VSCO": f"https://vsco.co/{clean_username}",
        "Letterboxd": f"https://letterboxd.com/{clean_username}",
        "Houzz": f"https://www.houzz.com/user/{clean_username}",
        "Digg": f"https://digg.com/@{clean_username}",
        "Giphy": f"https://giphy.com/{clean_username}",
        "Anchor": f"https://anchor.fm/{clean_username}",
        "Scribd": f"https://www.scribd.com/{clean_username}",
        "Grubhub": f"https://www.grubhub.com/profile/{clean_username}",
        "ReverbNation": f"https://www.reverbnation.com/{clean_username}",
        "Squarespace": f"https://{clean_username}.squarespace.com",
        "Mixcloud": f"https://www.mixcloud.com/{clean_username}",
        "IMDb": f"https://www.imdb.com/user/ur{clean_username}",
        "LinkBio": f"https://lnk.bio/{clean_username}",
        "Replit": f"https://replit.com/@{clean_username}",
        "Ifttt": f"https://ifttt.com/p/{clean_username}",
        "Weebly": f"https://{clean_username}.weebly.com/",
        "Smule": f"https://www.smule.com/{clean_username}",
        "Wordpress": f"https://{clean_username}.wordpress.com/",
        "Tryhackme": f"https://tryhackme.com/p/{clean_username}",
        "Myspace": f"https://myspace.com/{clean_username}",
        "Freelancer": f"https://www.freelancer.com/u/{clean_username}",
        "Dev.to": f"https://dev.to/{clean_username}",
        "Blogspot": f"https://{clean_username}.blogspot.com",
        "Gist": f"https://gist.github.com/{clean_username}",
        "Viki": f"https://www.viki.com/users/{clean_username}/about",
        "Discord": f"https://discord.com/users/{clean_username}",
        "Telegram": f"https://t.me/{clean_username}",
        "Discord.me": f"https://discord.me/user/{clean_username}",
        "HackerOne": f"https://hackerone.com/{clean_username}",
        "Kaggle": f"https://www.kaggle.com/{clean_username}",
        "Hackernoon": f"https://hackernoon.com/u/{clean_username}",
        "ProductHunt": f"https://www.producthunt.com/@{clean_username}",
        "Atlassian": f"https://community.atlassian.com/t5/user/{clean_username}",
        "HackerRank": f"https://hackerrank.com/{clean_username}",
        "LeetCode": f"https://leetcode.com/{clean_username}",
        "Codechef": f"https://www.codechef.com/users/{clean_username}",
        "Mastodon": f"https://mastodon.social/@{clean_username}",
    }

    # Categorize platforms
    platform_categories = categorize_platforms(platforms)
    
    threads = []
    results = {}
    found_profiles = {}
    
    # Lock for thread-safe operations
    stats_lock = threading.Lock()
    platform_stats = {}
    
    start_time = time.time()
    
    # Limit platforms to check to prevent timeouts
    # Sort platforms by popularity/importance
    top_platforms = [
        "Instagram", "Twitter", "Facebook", "TikTok", "LinkedIn", 
        "GitHub", "Reddit", "Pinterest", "YouTube", "Snapchat",
        "Twitch", "Medium", "Telegram", "Discord", "Tumblr",
        "SoundCloud", "Spotify", "Linktr.ee", "Behance", "Dribbble",
        "Flickr", "DeviantArt", "Trello", "Gitlab", "Steam"
    ]
    
    # Create a prioritized platform dictionary with the top platforms first
    prioritized_platforms = {}
    
    # First add all top platforms that exist in our platforms dictionary
    for p in top_platforms:
        if p in platforms:
            prioritized_platforms[p] = platforms[p]
    
    # Then add remaining platforms until we reach MAX_PLATFORMS
    remaining_slots = MAX_PLATFORMS - len(prioritized_platforms)
    if remaining_slots > 0:
        for p, url in platforms.items():
            if p not in prioritized_platforms and len(prioritized_platforms) < MAX_PLATFORMS:
                prioritized_platforms[p] = url
    
    # Process prioritized platforms in batches to limit concurrent threads
    platform_items = list(prioritized_platforms.items())
    for i in range(0, len(platform_items), MAX_THREADS):
        batch = platform_items[i:i+MAX_THREADS]
        batch_threads = []
        
        # Create and start threads for this batch
        for platform, url in batch:
            thread = threading.Thread(target=check_platform, 
                                     args=(clean_username, platform, url, results, stats_lock, platform_stats, username_variations))
            thread.start()
            batch_threads.append(thread)
            threads.append(thread)
        
        # Wait for this batch to complete before starting the next
        for thread in batch_threads:
            thread.join()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Get statistics
    found_count = sum(1 for value in results.values() if value is not None)
    timeouts = sum(1 for platform, stats in platform_stats.items() if stats.get('status_code') == 'timeout')
    errors = sum(1 for platform, stats in platform_stats.items() if stats.get('status_code') == 'error')
    
    # Format the date
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Compile found profiles and extract metadata if enabled
    profile_metadata_collection = {}
    
    for platform, url in results.items():
        if url:
            found_profiles[platform] = url
            
            # Extract metadata if enabled
            if ENABLE_METADATA_EXTRACTION:
                try:
                    # Pass response text from platform stats if available to avoid re-fetching
                    response_text = None
                    if platform in platform_stats and 'response_text' in platform_stats[platform]:
                        response_text = platform_stats[platform]['response_text']
                    
                    # Extract metadata
                    metadata = extract_profile_metadata(platform, url, response_text)
                    profile_metadata_collection[platform] = metadata
                except Exception as e:
                    logging.error(f"Error extracting metadata for {platform}: {e}")
    
    # Generate platform metadata
    platform_metadata = {
        "categories": {},
        "response_times": {},
        "status_codes": {},
        "detailed_metadata": profile_metadata_collection
    }
    
    # Populate platform metadata
    for platform, category in platform_categories.items():
        if platform in found_profiles:
            if category not in platform_metadata["categories"]:
                platform_metadata["categories"][category] = []
            platform_metadata["categories"][category].append(platform)
    
    # Add response time data
    for platform, stats in platform_stats.items():
        if platform in found_profiles:
            platform_metadata["response_times"][platform] = stats.get('response_time', 0)
            platform_metadata["status_codes"][platform] = stats.get('status_code', None)
    
    # Validate and generate reverse image search URLs
    reverse_image_urls = None
    image_metadata = None
    
    if image_link:
        # Validate the image URL with our enhanced validation
        validation_result = validate_image_url(image_link)
        
        # Setup image metadata based on validation result
        image_metadata = {
            "url": image_link,  # Original URL
            "validated": validation_result.get("valid", False),
            "error": validation_result.get("error", None) if not validation_result.get("valid", False) else None,
            "content_type": validation_result.get("content_type"),
            "source": validation_result.get("source")
        }
        
        # Get the direct URL from validation if available, otherwise use original
        direct_url = validation_result.get("direct_url", image_link) or image_link
        
        # Always create search URLs (even for invalid images) to allow frontend to handle accordingly
        # Just because our validation may fail doesn't mean search engines can't process the image
        encoded_image_url = quote_plus(direct_url)
        
        reverse_image_urls = {
            "Google": f"https://lens.google.com/uploadbyurl?url={encoded_image_url}",
            "Bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:{encoded_image_url}",
            "Yandex": f"https://yandex.com/images/search?source=collections&&url={encoded_image_url}&rpt=imageview",
            "Baidu": f"https://graph.baidu.com/details?isfromtusoupc=1&tn=pc&carousel=0&image={encoded_image_url}",
            "TinEye": f"https://tineye.com/search?url={encoded_image_url}"
        }
        
        # Update search engines count
        image_metadata["search_engines"] = len(reverse_image_urls)
        
        # Force validation to true for Facebook URLs to allow reverse image search to work
        # This is a special case as Facebook blocks direct image validation but reverse engines can still work
        if "facebook.com" in image_link.lower() and not validation_result.get("valid", False):
            image_metadata["validated"] = True
    
    # Compile statistics and information about username variations
    variations_used = {}
    
    # Check which platforms were found using which username variations
    for platform, platform_data in platform_stats.items():
        if platform in found_profiles and 'variation_used' in platform_data:
            variations_used[platform] = platform_data['variation_used']
    
    # Compile statistics
    stats = {
        "target": username,
        "platforms_checked": len(platforms),
        "platforms_list": list(platforms.keys()),
        "username_variations": username_variations,
        "variations_used": variations_used,
        "time_taken": f"{elapsed_time:.2f}",
        "date": formatted_date,
        "profiles_found": found_count,
        "timeouts": timeouts,
        "errors": errors,
        "version": VERSION
    }
    
    # Return results
    return found_profiles, stats, reverse_image_urls, platform_metadata, image_metadata
