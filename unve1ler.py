import requests
import threading
import time
from datetime import datetime
import logging
from urllib.parse import quote_plus
import json
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Constants
VERSION = '1.0.2'
TIMEOUT_SECONDS = 10
MAX_THREADS = 20  # Limit number of concurrent threads to prevent overloading

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

def check_platform(username, platform, url, results, stats_lock, platform_stats):
    """
    Check if a username exists on a specific platform.
    
    Args:
        username (str): Username to check
        platform (str): Platform name
        url (str): URL to check
        results (dict): Dictionary to store results
        stats_lock (threading.Lock): Lock for updating platform stats
        platform_stats (dict): Dictionary to store platform statistics
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    start_time = time.time()
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        with stats_lock:
            platform_stats[platform] = {
                'response_time': response_time,
                'status_code': response.status_code
            }
        
        if response.status_code == 200:
            logging.debug(f"Profile found on {platform}: {url}")
            results[platform] = url
        else:
            logging.debug(f"Profile not found on {platform}")
            results[platform] = None

    except requests.exceptions.Timeout:
        logging.warning(f"Timeout while checking {platform}")
        with stats_lock:
            platform_stats[platform] = {
                'response_time': TIMEOUT_SECONDS,
                'status_code': 'timeout'
            }
        results[platform] = None
        
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while checking {platform}: {e}")
        with stats_lock:
            platform_stats[platform] = {
                'response_time': time.time() - start_time,
                'status_code': 'error',
                'error': str(e)
            }
        results[platform] = None

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

def check_social_media(username, image_link=None):
    """
    Check social media platforms for a username and generate reverse image search links.
    
    Args:
        username (str): The username to search for
        image_link (str, optional): URL to an image for reverse image search
        
    Returns:
        tuple: (results, stats, reverse_image_urls, platform_metadata)
    """
    # Clean the username (remove special chars that might cause issues)
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
    
    # Process platforms in batches to limit concurrent threads
    platform_items = list(platforms.items())
    for i in range(0, len(platform_items), MAX_THREADS):
        batch = platform_items[i:i+MAX_THREADS]
        batch_threads = []
        
        # Create and start threads for this batch
        for platform, url in batch:
            thread = threading.Thread(target=check_platform, 
                                     args=(clean_username, platform, url, results, stats_lock, platform_stats))
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
    
    # Compile found profiles
    for platform, url in results.items():
        if url:
            found_profiles[platform] = url
    
    # Generate platform metadata
    platform_metadata = {
        "categories": {},
        "response_times": {},
        "status_codes": {}
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
    
    # Compile statistics
    stats = {
        "target": username,
        "platforms_checked": len(platforms),
        "platforms_list": list(platforms.keys()),
        "time_taken": f"{elapsed_time:.2f}",
        "date": formatted_date,
        "profiles_found": found_count,
        "timeouts": timeouts,
        "errors": errors,
        "version": VERSION
    }
    
    # Return results
    return found_profiles, stats, reverse_image_urls, platform_metadata, image_metadata
