"""
Support for loading assets and resources that might be needed by unve1ler.
"""

import os
import re
import json
import logging
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)

def extract_social_profiles_from_text(text_content):
    """
    Extract potential social media profiles from text content.
    
    Args:
        text_content (str): Text to analyze for social media profiles
        
    Returns:
        dict: Dictionary of platforms and extracted profile URLs
    """
    results = {}
    
    # Common social media URL patterns
    patterns = {
        'Twitter': r'https?://(www\.)?(twitter|x)\.com/([A-Za-z0-9_]+)',
        'Instagram': r'https?://(www\.)?instagram\.com/([A-Za-z0-9_\.]+)/?',
        'Facebook': r'https?://(www\.)?facebook\.com/([A-Za-z0-9\.]+)/?',
        'LinkedIn': r'https?://(www\.)?linkedin\.com/in/([A-Za-z0-9_\-\.]+)/?',
        'GitHub': r'https?://(www\.)?github\.com/([A-Za-z0-9_\-]+)/?',
        'YouTube': r'https?://(www\.)?youtube\.com/(user|channel|c)/([A-Za-z0-9_\-]+)/?',
        'TikTok': r'https?://(www\.)?tiktok\.com/@([A-Za-z0-9_\.]+)/?',
        'Reddit': r'https?://(www\.)?reddit\.com/user/([A-Za-z0-9_\-]+)/?',
        'Pinterest': r'https?://(www\.)?pinterest\.com/([A-Za-z0-9_\-]+)/?',
        'Discord': r'https?://(www\.)?discord\.(gg|com)/(invite/)?([A-Za-z0-9_\-]+)/?',
        'Telegram': r'https?://(www\.)?t\.me/([A-Za-z0-9_]+)/?',
        'Medium': r'https?://(www\.)?medium\.com/@?([A-Za-z0-9_\-\.]+)/?',
        'Twitch': r'https?://(www\.)?twitch\.tv/([A-Za-z0-9_]+)/?',
    }
    
    # Extract profile URLs based on patterns
    for platform, pattern in patterns.items():
        matches = re.findall(pattern, text_content)
        if matches:
            if platform not in results:
                results[platform] = []
            for match in matches:
                # Extract the username part from the match tuple
                if platform == 'YouTube':
                    username = match[2]  # YouTube pattern has 3 groups
                elif platform == 'Discord':
                    username = match[3]  # Discord pattern has 4 groups
                else:
                    username = match[-1]  # For most platforms, username is the last group
                
                # Reconstruct the full URL
                if platform == 'Twitter':
                    url = f"https://twitter.com/{username}"
                elif platform == 'Instagram':
                    url = f"https://www.instagram.com/{username}/"
                elif platform == 'Facebook':
                    url = f"https://www.facebook.com/{username}"
                elif platform == 'LinkedIn':
                    url = f"https://www.linkedin.com/in/{username}/"
                elif platform == 'GitHub':
                    url = f"https://github.com/{username}"
                elif platform == 'YouTube':
                    subpath = match[1]  # user, channel, or c
                    url = f"https://www.youtube.com/{subpath}/{username}"
                elif platform == 'TikTok':
                    url = f"https://www.tiktok.com/@{username}"
                elif platform == 'Reddit':
                    url = f"https://www.reddit.com/user/{username}"
                elif platform == 'Pinterest':
                    url = f"https://www.pinterest.com/{username}/"
                elif platform == 'Discord':
                    invite_part = 'invite/' if match[2] == 'invite/' else ''
                    url = f"https://discord.gg/{invite_part}{username}"
                elif platform == 'Telegram':
                    url = f"https://t.me/{username}"
                elif platform == 'Medium':
                    url = f"https://medium.com/@{username}"
                elif platform == 'Twitch':
                    url = f"https://www.twitch.tv/{username}"
                
                # Use the url we already built above
                if platform in results:
                    # If the platform is already in results, append the URL to the list
                    if isinstance(results[platform], list):
                        if url not in results[platform]:
                            results[platform].append(url)
                    else:
                        # If it's not a list yet, convert it to a list
                        results[platform] = [results[platform], url]
                else:
                    # First URL for this platform
                    results[platform] = [url]
    
    # Convert lists to single URLs for compatibility with unve1ler format
    for platform in results:
        if len(results[platform]) == 1:
            results[platform] = results[platform][0]
    
    return results

def extract_usernames_from_text(text_content):
    """
    Extract potential usernames from text content.
    
    Args:
        text_content (str): Text to analyze for usernames
        
    Returns:
        list: List of potential usernames
    """
    # Patterns to identify potential usernames
    patterns = [
        r'@([A-Za-z0-9_\.]+)',  # Twitter/Instagram style @username
        r'([A-Za-z][A-Za-z0-9_\.]{2,24})'  # Generic username pattern (3-25 chars, must start with letter)
    ]
    
    # Common terms to exclude
    exclude_terms = [
        # Web related terms
        'www', 'http', 'https', 'com', 'co', 'org', 'net', 'io', 'fm', 'me', 'tv',
        
        # Common programming terms
        'response', 'request', 'time', 'date', 'thread', 'print', 'import', 'from',
        'def', 'str', 'int', 'bool', 'list', 'dict', 'set', 'tuple', 'class', 'self',
        'function', 'module', 'package', 'object', 'return', 'yield', 'except', 'try',
        'finally', 'raise', 'assert', 'lambda', 'global', 'nonlocal', 'and', 'or', 'not',
        'is', 'in', 'for', 'while', 'break', 'continue', 'if', 'else', 'elif', 'with',
        'match', 'case', 'end', 'start', 'append', 'extend', 'remove', 'pop', 'clear',
        'join', 'split', 'strip', 'lower', 'upper', 'title', 'capitalize', 'status',
        'code', 'error', 'warning', 'info', 'debug', 'exception', 'platforms', 'items',
        
        # Platform names (these are often mentioned as text, not usernames)
        'twitter', 'facebook', 'instagram', 'linkedin', 'github', 'pinterest', 'reddit',
        'tiktok', 'snapchat', 'tumblr', 'youtube', 'twitch', 'discord', 'telegram',
        'medium', 'quora', 'flickr', 'behance', 'dribbble', 'deviantart', 'vimeo',
        'soundcloud', 'spotify', 'pinterest', 'blogger', 'wordpress', 'steam',
        'stackoverflow', 'fiverr', 'etsy', 'patreon', 'gist', 'gitlab', 'replit',
        'codepen', 'trello', 'anchor', 'meetup', 'imdb', 'giphy', 'goodreads',
        'mixcloud', 'reverbnation', 'smule', 'xing', 'houzz', 'wattpad', 'canva',
        'slack', 'foursquare', 'zillow', 'vsco', 'myspace', 'grubhub', 'digg',
        'gravatar', 'letterboxd', 'about', 'angel', 'relpit', 'keybase', 'periscope',
        
        # Common UI and feature terms
        'login', 'signup', 'signin', 'register', 'profile', 'account', 'password',
        'username', 'email', 'search', 'welcome', 'logout', 'media', 'photo', 'video',
        'image', 'audio', 'link', 'post', 'comment', 'share', 'like', 'follow', 'friend',
        'loading', 'error', 'success', 'warning', 'failure', 'target', 'version',
        'created', 'found', 'searching', 'note', 'false', 'none', 'true', 'null',
        'timeout', 'invalid', 'reverse', 'clues', 'footprints', 'digital', 'visual',
        'revealing', 'unve1ler', 'blog', 'urls', 'errors', 'timeouts', 'python3'
    ]
    
    # Common domains and URL components to exclude
    exclude_domains = ['github.com', 'twitter.com', 'facebook.com', 'instagram.com', 
                       'youtube.com', 'linkedin.com', 'pinterest.com', 'snapchat.com', 
                       'reddit.com', 'tiktok.com', 'tumblr.com', 'vimeo.com', 'twitch.tv',
                       'spotify.com', 'soundcloud.com', 'medium.com', 'stackoverflow.com',
                       'quora.com', 'flickr.com', 'dribbble.com', 'behance.net', 'deviantart.com',
                       'wordpress.com', 'blogspot.com']
    
    # Check if a string might be a valid username
    def is_likely_username(username):
        # Basic checks
        if len(username) < 3 or len(username) > 25:
            return False
        
        if username.isdigit():
            return False
        
        # Exclude common programming terms and domains
        if username.lower() in exclude_terms:
            return False
        
        # Exclude domains and URL components
        for domain in exclude_domains:
            if domain in username:
                return False
            
        # Check for likely username formatting (not just common words)
        # Must contain an underscore, period, or combination of letters and numbers
        has_underscore = '_' in username
        has_period = '.' in username
        has_mixed_case = username.lower() != username and username.upper() != username
        has_letter_number_mix = any(c.isalpha() for c in username) and any(c.isdigit() for c in username)
        
        return has_underscore or has_period or has_mixed_case or has_letter_number_mix
    
    usernames = set()
    for pattern in patterns:
        matches = re.findall(pattern, text_content)
        for match in matches:
            if is_likely_username(match):
                usernames.add(match)
    
    return list(usernames)

def extract_image_urls_from_text(text_content):
    """
    Extract potential image URLs from text content.
    
    Args:
        text_content (str): Text to analyze for image URLs
        
    Returns:
        list: List of potential image URLs
    """
    # Common image URL patterns
    patterns = [
        r'https?://[^\s]+\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff)',  # Direct image URLs
        r'https?://(www\.)?(imgur|i\.imgur)\.com/[^\s/]+',  # Imgur
        r'https?://(www\.)?flickr\.com/photos/[^\s/]+',  # Flickr
        r'https?://(www\.)?instagram\.com/p/[^\s/]+',  # Instagram posts
        r'https?://(www\.)?pbs\.twimg\.com/media/[^\s/]+',  # Twitter images
    ]
    
    image_urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text_content)
        for match in matches:
            if isinstance(match, tuple):
                # Skip the extension part captured by the first pattern
                continue
            
            # Find the full URL that matched
            url_pattern = r'https?://[^\s]+' + re.escape(match)
            full_urls = re.findall(url_pattern, text_content)
            if full_urls:
                for url in full_urls:
                    if url not in image_urls:
                        image_urls.append(url)
    
    return image_urls

def process_attached_file(filename):
    """
    Process an attached text file to extract potentially useful information.
    
    Args:
        filename (str): Path to the file to process
        
    Returns:
        dict: Dictionary containing extracted information
    """
    if not os.path.exists(filename):
        return {"error": f"File not found: {filename}"}
    
    results = {
        "social_profiles": {},
        "potential_usernames": [],
        "potential_image_urls": [],
        "processing_timestamp": datetime.now().isoformat()
    }
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Extract social profiles
            results["social_profiles"] = extract_social_profiles_from_text(content)
            
            # Extract potential usernames
            results["potential_usernames"] = extract_usernames_from_text(content)
            
            # Extract potential image URLs
            results["potential_image_urls"] = extract_image_urls_from_text(content)
        
        return results
    
    except Exception as e:
        logging.error(f"Error processing file {filename}: {e}")
        return {"error": f"Failed to process file: {str(e)}"}

# Example usage
if __name__ == "__main__":
    # Process an example file from the attached_assets folder
    example_file = "attached_assets/Pasted--usr-bin-env-python3-unve1ler-Revealing-Digital-Footprints-and-Visual-Clues-on-the-Internet-A-1743374661556.txt"
    results = process_attached_file(example_file)
    print(json.dumps(results, indent=2))