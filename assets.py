"""
Support for loading assets and resources that might be needed by unve1ler.
"""

import os
import re
import json
import logging
from datetime import datetime
from urllib.parse import urlparse
from web_scraper import extract_dark_web_information

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
    
    # Comprehensive social media URL patterns with enhanced matching and additional platforms
    patterns = {
        'Twitter': r'https?://(www\.)?(twitter|x)\.com/([A-Za-z0-9_]+)',
        'Instagram': r'https?://(www\.)?instagram\.com/([A-Za-z0-9_\.]+)/?',
        'Facebook': r'https?://(www\.)?facebook\.com/([A-Za-z0-9\.]+)/?',
        'LinkedIn': r'https?://(www\.)?linkedin\.com/in/([A-Za-z0-9_\-\.]+)/?',
        'GitHub': r'https?://(www\.)?github\.com/([A-Za-z0-9_\-]+)/?',
        # Additional GitHub patterns for variable formats
        'GitHub-Repo': r'github(?:\.com)?[\s:=]+(?:https?://(www\.)?github\.com/)?([A-Za-z0-9_\-]+)(?:/|\s|$)',
        'YouTube': r'https?://(www\.)?youtube\.com/(user|channel|c)/([A-Za-z0-9_\-]+)/?',
        'YouTube-Simple': r'https?://(www\.)?youtube\.com/@([A-Za-z0-9_\-]+)/?',
        'TikTok': r'https?://(www\.)?tiktok\.com/@([A-Za-z0-9_\.]+)/?',
        'Reddit': r'https?://(www\.)?reddit\.com/user/([A-Za-z0-9_\-]+)/?',
        'Pinterest': r'https?://(www\.)?pinterest\.com/([A-Za-z0-9_\-]+)/?',
        'Discord': r'https?://(www\.)?discord\.(gg|com)/(invite/)?([A-Za-z0-9_\-]+)/?',
        'Telegram': r'https?://(www\.)?t\.me/([A-Za-z0-9_]+)/?',
        'Medium': r'https?://(www\.)?medium\.com/@?([A-Za-z0-9_\-\.]+)/?',
        'Twitch': r'https?://(www\.)?twitch\.tv/([A-Za-z0-9_]+)/?',
        # Cryptocurrency and dark web platforms
        'Keybase': r'https?://(www\.)?keybase\.io/([A-Za-z0-9_\-]+)/?',
        'Bitcoin-Address': r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b',
        'Ethereum-Address': r'\b0x[a-fA-F0-9]{40}\b',
        'Onion-Service': r'https?://([a-z2-7]{16}|[a-z2-7]{56})\.onion/([^\s]*)/?',
        # Professional networks
        'Behance': r'https?://(www\.)?behance\.net/([A-Za-z0-9_\-]+)/?',
        'Dribbble': r'https?://(www\.)?dribbble\.com/([A-Za-z0-9_\-]+)/?',
        'Stack-Overflow': r'https?://(www\.)?stackoverflow\.com/users/(\d+)/([A-Za-z0-9_\-]+)/?',
        'Gitlab': r'https?://(www\.)?gitlab\.com/([A-Za-z0-9_\-\.]+)/?',
        # Coding platforms
        'Replit': r'https?://(www\.)?replit\.com/@([A-Za-z0-9_\-]+)/?',
        'CodePen': r'https?://(www\.)?codepen\.io/([A-Za-z0-9_\-]+)/?',
        'Pastebin': r'https?://(www\.)?pastebin\.com/u/([A-Za-z0-9_\-]+)/?',
        'HackerRank': r'https?://(www\.)?hackerrank\.com/([A-Za-z0-9_\-]+)/?',
        'LeetCode': r'https?://(www\.)?leetcode\.com/([A-Za-z0-9_\-]+)/?',
        # Gaming platforms
        'Steam': r'https?://(www\.)?steamcommunity\.com/(id|profiles)/([A-Za-z0-9_\-]+)/?',
        'Xbox': r'https?://(www\.)?xboxgamertag\.com/search/([A-Za-z0-9_\-\s]+)/?',
        'PSN': r'https?://(www\.)?psnprofiles\.com/([A-Za-z0-9_\-]+)/?',
        # Music platforms
        'Spotify': r'https?://(www\.)?open\.spotify\.com/user/([A-Za-z0-9_\-\.]+)/?',
        'SoundCloud': r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_\-\.]+)/?',
        'Last.fm': r'https?://(www\.)?last\.fm/user/([A-Za-z0-9_\-]+)/?',
        # Image platforms
        'Flickr': r'https?://(www\.)?flickr\.com/people/([A-Za-z0-9@_\-\.]+)/?',
        'Imgur': r'https?://(www\.)?imgur\.com/user/([A-Za-z0-9_\-]+)/?',
        'DeviantArt': r'https?://(www\.)?deviantart\.com/([A-Za-z0-9_\-]+)/?',
        # Website and blog patterns - more flexible to catch variable formats
        'Website': r'website\s*[\s:=]+\s*[\'"]?(https?://[^\s\'"]+)[\'"]?',
        'Blog': r'blog\s*[\s:=]+\s*[\'"]?(https?://[^\s\'"]+)[\'"]?',
        # Special case for the spyboy website format with direct variable assignment
        'Website-SpyBoy': r'website\s*=\s*[\'"](https?://[a-zA-Z0-9_\.\-]+\.[a-z]+/?)[\'"]',
        'Blog-SpyBoy': r'blog\s*=\s*[\'"](https?://[a-zA-Z0-9_\.\-]+\.[a-z]+/?)[\'"]',
        # Simple variable assignments (common in Python scripts)
        'Website-Direct': r'website\s*=\s*[\'"](https?://[^\s\'"]+)[\'"]',
        'Blog-Direct': r'blog\s*=\s*[\'"](https?://[^\s\'"]+)[\'"]',
        'Twitter-Direct': r'twitter_url\s*=\s*[\'"](https?://[^\s\'"]+)[\'"]',
        'Discord-Direct': r'discord\s*=\s*[\'"](https?://[^\s\'"]+)[\'"]',
        'GitHub-Direct': r'github\s*=\s*[\'"](https?://[^\s\'"]+)[\'"]',
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
                
                # Initialize url to None
                url = None
                
                # Reconstruct the full URL
                if platform == 'Twitter':
                    url = f"https://twitter.com/{username}"
                elif platform == 'Instagram':
                    url = f"https://www.instagram.com/{username}/"
                elif platform == 'Facebook':
                    url = f"https://www.facebook.com/{username}"
                elif platform == 'LinkedIn':
                    url = f"https://www.linkedin.com/in/{username}/"
                elif platform == 'GitHub' or platform == 'GitHub-Repo':
                    url = f"https://github.com/{username}"
                elif platform in ['Website', 'Blog', 'Website-SpyBoy', 'Blog-SpyBoy', 
                        'Website-Direct', 'Blog-Direct', 'Twitter-Direct', 'Discord-Direct', 'GitHub-Direct']:
                    url = username  # URL is directly captured in the regex
                elif platform == 'YouTube':
                    subpath = match[1]  # user, channel, or c
                    url = f"https://www.youtube.com/{subpath}/{username}"
                elif platform == 'YouTube-Simple':
                    url = f"https://www.youtube.com/@{username}"
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
                # New platform handling
                elif platform == 'Keybase':
                    url = f"https://keybase.io/{username}"
                elif platform == 'Bitcoin-Address' or platform == 'Ethereum-Address':
                    url = username  # Cryptocurrency addresses don't have a standard URL format
                elif platform == 'Onion-Service':
                    if match[1]:  # onion domain
                        onion_domain = match[0]
                        url = onion_domain
                elif platform == 'Behance':
                    url = f"https://www.behance.net/{username}"
                elif platform == 'Dribbble':
                    url = f"https://dribbble.com/{username}"
                elif platform == 'Stack-Overflow':
                    user_id = match[1]
                    url = f"https://stackoverflow.com/users/{user_id}/{username}"
                elif platform == 'Gitlab':
                    url = f"https://gitlab.com/{username}"
                elif platform == 'Replit':
                    url = f"https://replit.com/@{username}"
                elif platform == 'CodePen':
                    url = f"https://codepen.io/{username}"
                elif platform == 'Pastebin':
                    url = f"https://pastebin.com/u/{username}"
                elif platform == 'HackerRank':
                    url = f"https://hackerrank.com/{username}"
                elif platform == 'LeetCode':
                    url = f"https://leetcode.com/{username}"
                elif platform == 'Steam':
                    subpath = match[1]  # id or profiles
                    url = f"https://steamcommunity.com/{subpath}/{username}"
                elif platform == 'Xbox':
                    url = f"https://xboxgamertag.com/search/{username}"
                elif platform == 'PSN':
                    url = f"https://psnprofiles.com/{username}"
                elif platform == 'Spotify':
                    url = f"https://open.spotify.com/user/{username}"
                elif platform == 'SoundCloud':
                    url = f"https://soundcloud.com/{username}"
                elif platform == 'Last.fm':
                    url = f"https://last.fm/user/{username}"
                elif platform == 'Flickr':
                    url = f"https://www.flickr.com/people/{username}/"
                elif platform == 'Imgur':
                    url = f"https://imgur.com/user/{username}"
                elif platform == 'DeviantArt':
                    url = f"https://deviantart.com/{username}"
                
                # Skip if no URL was created
                if url is None:
                    continue
                    
                # Add URL to results collection
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
    Extract potential usernames from text content using advanced NLP-inspired techniques.
    
    Args:
        text_content (str): Text to analyze for usernames
        
    Returns:
        list: List of potential usernames with high confidence scores
    """
    # Load a dictionary of common English words for better filtering
    # This helps avoid matching standard language words as usernames
    common_words = set([
        'about', 'after', 'again', 'all', 'also', 'an', 'and', 'any', 'are', 'as', 'at',
        'be', 'because', 'been', 'before', 'being', 'between', 'both', 'but', 'by',
        'came', 'can', 'come', 'could', 'did', 'do', 'does', 'done', 'down', 'each',
        'few', 'for', 'from', 'further', 'get', 'had', 'has', 'have', 'having', 'he',
        'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'if', 'in',
        'into', 'is', 'it', 'its', 'itself', 'just', 'like', 'make', 'many', 'me',
        'might', 'more', 'most', 'much', 'must', 'my', 'myself', 'never', 'no', 'nor',
        'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
        'ourselves', 'out', 'over', 'own', 'said', 'same', 'see', 'should', 'so', 'some',
        'such', 'take', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves',
        'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under',
        'until', 'up', 'very', 'was', 'way', 'we', 'well', 'were', 'what', 'when', 'where',
        'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you', 'your',
        'yours', 'yourself', 'yourselves'
    ])
    
    # Advanced pattern recognition for username formats with expanded capabilities
    username_patterns = [
        # Explicit username markers with high confidence
        (r'(?:(?:user(?:name)?|account|handle|alias|id)(?:\s+(?:is|:))?\s+[\'"]?(@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?)', 1.0),
        
        # Social media style @ mentions with expanded character set - improved to catch more formats
        (r'@([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})\b', 0.95),
        
        # Discord username format (name#numbers) - high confidence pattern
        (r'\b([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})#\d{4}\b', 0.95),
        
        # HUMINT specific patterns - names with specific roles or professions
        (r'(?:researcher|investigator|analyst|specialist|officer|agent|operative|detective|journalist)\s+([A-Za-z][A-Za-z0-9_\.\-]{2,30}(?:\s+[A-Za-z][A-Za-z0-9]{1,30})?)', 0.85),
        
        # Username with common indicators including aliases
        (r'(?:follow|add|contact|find|message|dm|ping|reach|join|connect)\s+(?:me|us|him|her|them)?\s+(?:at|on|via|using|through)?\s+[\'"]?(@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?', 0.9),
        
        # "Known as" or "goes by" pattern - strong HUMINT indicator
        (r'(?:known as|goes by|aka|alias|called|nicknamed)\s+[\'"]?(@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?', 0.9),
        
        # Generic username patterns with context clues (lower confidence)
        (r'\b(?:my|the|their|his|her|our)\s+(?:id|handle|user|account|alias|nick|profile|tag|code)\s+(?:is|:)?\s+[\'"]?([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?', 0.85),
        
        # Platform-specific identifier with username (expanded platforms)
        (r'(?:twitter|x|instagram|github|reddit|snapchat|tiktok|linkedin|discord|telegram|youtube|pinterest|behance|dribbble|mastodon|twitch|gitlab|keybase|signal|session|wire|element)(?:.com|.org|.io|.gg|.me)?(?:/|\s+)(@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})\b', 0.9),
        
        # Email pattern usernames (extract username part from email)
        (r'\b([a-zA-Z0-9][a-zA-Z0-9._\-]{2,30})@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b', 0.85),
        
        # Usernames in various enclosures (parentheses, brackets, etc.)
        (r'[\(\[\{](@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\)\]\}]', 0.7),
        
        # Handle/username declaration patterns
        (r'\bhandle(?:\s+(?:is|:))?\s+[\'"]?(@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?', 0.95),
        (r'\b(?:i am|i\'m)\s+[\'"]?(@?)([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?\s+(?:on|at)\s+(?:twitter|github|reddit|discord)', 0.9),
        
        # Common username formats with special patterns
        (r'\b([A-Za-z][A-Za-z0-9]{1,20}[_.\-][A-Za-z0-9]{1,20})\b', 0.6), # pattern like john_doe, john.doe
        
        # Dark web handles with specific formats
        (r'(?:on|at|via|using|through)\s+(?:tor|onion|dark\s*web|hidden\s*service)(?:[\s\:\.])+([A-Za-z0-9_\-]{2,30})', 0.9),
        (r'(?:tor|onion|dark\s*web|hidden\s*service)\s+(?:username|handle|id|alias)(?:[\s\:\.])+([A-Za-z0-9_\-]{2,30})', 0.95),
        
        # Cryptocurrency and digital identity patterns
        (r'(?:key(?:base)?|pgp|gpg|public\s*key)\s+(?:id|fingerprint)?\s*[:\s]+([A-F0-9]{8,40})', 0.85),
        (r'(?:session|signal|matrix|element|xmpp)\s+id(?:[\s\:\.])+([A-Za-z0-9_\-\.]{4,64})', 0.9),
        
        # Hacker/security researcher handles
        (r'\b(?:hacker|security|researcher|pentester|red\s*team)\s+(?:known as|called|alias)\s+[\'"]?([A-Za-z0-9][A-Za-z0-9_\.\-]{2,30})[\'"]?', 0.9),
        
        # Generic usernames (lowest confidence, needs more validation) - now slightly higher quality filter
        (r'\b([A-Za-z][A-Za-z0-9_\.\-]{3,30})\b', 0.4)
    ]
    
    # Comprehensive exclusion lists with categories
    exclusion_categories = {
        # Platform names and domains
        'platforms': [
            'twitter', 'facebook', 'instagram', 'linkedin', 'github', 'pinterest', 'reddit',
            'tiktok', 'snapchat', 'tumblr', 'youtube', 'twitch', 'discord', 'telegram',
            'medium', 'quora', 'flickr', 'behance', 'dribbble', 'deviantart', 'vimeo',
            'soundcloud', 'spotify', 'blogger', 'wordpress', 'steam', 'stackoverflow', 
            'fiverr', 'etsy', 'patreon', 'gist', 'gitlab', 'replit', 'codepen', 'trello', 
            'anchor', 'meetup', 'imdb', 'giphy', 'goodreads', 'mixcloud', 'reverbnation', 
            'smule', 'xing', 'houzz', 'wattpad', 'canva', 'slack', 'foursquare', 'zillow', 
            'vsco', 'myspace', 'grubhub', 'digg', 'gravatar', 'letterboxd', 'keybase', 
            'periscope', 'viber', 'whatsapp', 'signal', 'mastodon', 'clubhouse', 'strava',
            'twitch', 'vimeo', 'dailymotion', 'vk', 'weibo', 'tinder', 'bumble', 'hinge'
        ],
        
        # Web and internet terms
        'web_terms': [
            'http', 'https', 'www', 'html', 'css', 'javascript', 'api', 'ajax', 'json',
            'xml', 'url', 'uri', 'domain', 'server', 'client', 'browser', 'cookie', 'cache',
            'proxy', 'firewall', 'router', 'gateway', 'bandwidth', 'download', 'upload',
            'streaming', 'cloud', 'hosting', 'webpage', 'website', 'webserver', 'frontend',
            'backend', 'database', 'query', 'index', 'search', 'filter', 'sort', 'link'
        ],
        
        # Programming terms
        'programming': [
            'function', 'method', 'class', 'object', 'array', 'string', 'integer', 'float',
            'boolean', 'null', 'undefined', 'var', 'let', 'const', 'import', 'export',
            'require', 'module', 'package', 'dependency', 'framework', 'library', 'api',
            'interface', 'abstract', 'public', 'private', 'protected', 'static', 'final',
            'async', 'await', 'promise', 'callback', 'event', 'listener', 'handler',
            'exception', 'error', 'debug', 'log', 'trace', 'info', 'warn', 'fatal',
            'assert', 'test', 'mock', 'stub', 'spy', 'request', 'response', 'get', 'post',
            'put', 'delete', 'patch', 'header', 'body', 'parameter', 'argument', 'return',
            'yield', 'throw', 'catch', 'try', 'finally', 'break', 'continue', 'while',
            'for', 'foreach', 'map', 'filter', 'reduce', 'sort', 'push', 'pop', 'shift',
            'unshift', 'join', 'split', 'slice', 'splice', 'concat'
        ],
        
        # UI and UX terms
        'ui_terms': [
            'button', 'input', 'form', 'label', 'select', 'option', 'checkbox', 'radio',
            'textarea', 'dropdown', 'menu', 'navbar', 'sidebar', 'header', 'footer',
            'main', 'section', 'article', 'div', 'span', 'container', 'wrapper', 'card',
            'panel', 'tab', 'modal', 'dialog', 'alert', 'notification', 'toast', 'tooltip',
            'popover', 'accordion', 'carousel', 'slider', 'progress', 'spinner', 'loader',
            'icon', 'image', 'avatar', 'thumbnail', 'banner', 'logo', 'layout', 'grid',
            'flex', 'responsive', 'mobile', 'desktop', 'viewport', 'media', 'query'
        ],
        
        # User actions and system messages
        'actions': [
            'login', 'logout', 'signup', 'signin', 'register', 'create', 'delete', 'update',
            'edit', 'view', 'show', 'hide', 'open', 'close', 'start', 'stop', 'pause',
            'resume', 'cancel', 'submit', 'save', 'download', 'upload', 'share', 'send',
            'receive', 'connect', 'disconnect', 'enable', 'disable', 'activate', 'deactivate',
            'block', 'unblock', 'follow', 'unfollow', 'like', 'unlike', 'comment', 'reply',
            'report', 'flag', 'pin', 'unpin', 'archive', 'unarchive', 'mute', 'unmute',
            'loading', 'processing', 'generating', 'analyzing', 'checking', 'verifying',
            'validating', 'calculating', 'searching', 'finding', 'fetching', 'retrieving'
        ],
        
        # OSINT specific terms
        'osint_terms': [
            'osint', 'investigation', 'reconnaissance', 'intelligence', 'footprint', 'digital',
            'trace', 'identity', 'anonymous', 'pseudonym', 'alias', 'avatar', 'profile',
            'metadata', 'geolocation', 'timestamp', 'exif', 'search', 'discovery', 'finding',
            'algorithm', 'analysis', 'scraping', 'crawling', 'extraction', 'enumeration',
            'detection', 'identification', 'verification', 'validation', 'correlation',
            'aggregation', 'collection', 'compilation', 'monitoring', 'tracking', 'tracing',
            'unveiling', 'revealing', 'uncovering', 'exposing', 'targeting', 'unve1ler'
        ],
        
        # Common file extensions
        'file_extensions': [
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg', 'webp', 'ico', 'pdf', 'doc',
            'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'csv', 'xml', 'json', 'html',
            'htm', 'css', 'js', 'py', 'java', 'cpp', 'c', 'h', 'cs', 'php', 'rb', 'go', 'rs',
            'swift', 'kt', 'ts', 'jsx', 'tsx', 'vue', 'sql', 'md', 'yml', 'yaml', 'toml', 'ini',
            'cfg', 'conf', 'log', 'zip', 'rar', 'tar', 'gz', '7z', 'mp3', 'mp4', 'avi', 'mov',
            'wmv', 'flv', 'wav', 'ogg', 'webm', 'exe', 'dll', 'so', 'apk', 'dmg', 'iso'
        ]
    }
    
    # Flatten the exclusion lists for easier lookup
    all_exclusions = set()
    for category in exclusion_categories.values():
        all_exclusions.update(category)
    
    # Combine with common words
    all_exclusions.update(common_words)
    
    # Domain names and TLDs to exclude
    exclude_domains = [
        'github.com', 'twitter.com', 'facebook.com', 'instagram.com', 'youtube.com',
        'linkedin.com', 'pinterest.com', 'snapchat.com', 'reddit.com', 'tiktok.com',
        'tumblr.com', 'vimeo.com', 'twitch.tv', 'spotify.com', 'soundcloud.com',
        'medium.com', 'stackoverflow.com', 'quora.com', 'flickr.com', 'dribbble.com',
        'behance.net', 'deviantart.com', 'wordpress.com', 'blogspot.com', 'gmail.com',
        'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com', 'icloud.com',
        'mail.com', 'aol.com', 'zoho.com'
    ]
    
    # TLDs to filter out standalone mentions
    common_tlds = [
        'com', 'org', 'net', 'io', 'ai', 'app', 'co', 'me', 'dev', 'info', 'edu',
        'gov', 'int', 'mil', 'biz', 'name', 'pro', 'aero', 'museum', 'coop', 'jobs',
        'travel', 'xyz', 'online', 'site', 'website', 'blog', 'tech', 'store', 'shop'
    ]
    
    # Create a scoring function that uses multiple signals to rate username likelihood
    def score_username(username, context_before="", context_after=""):
        """
        Score a potential username based on multiple heuristics with improved HUMINT and OSINT detection.
        
        Args:
            username: The potential username to score
            context_before: Text appearing before the username (for context analysis)
            context_after: Text appearing after the username (for context analysis)
            
        Returns:
            float: A score between 0 and 1, where higher values indicate higher confidence
        """
        # Start with a neutral base score
        score = 0.5
        
        # Basic disqualifiers (absolute)
        if len(username) < 3 or len(username) > 30:
            return 0.0
            
        if username.isdigit():
            return 0.0
            
        # Check if it's a common excluded term
        if username.lower() in all_exclusions:
            return 0.0
            
        # Check if it contains domain names
        for domain in exclude_domains:
            if domain in username.lower():
                return 0.0
                
        # Check if it's just a TLD
        if username.lower() in common_tlds:
            return 0.0
            
        # Full context analysis
        context = (context_before + " " + context_after).lower()
            
        # HUMINT strength indicators - significantly higher scores for human intelligence markers
        humint_markers = [
            'security researcher', 'investigator', 'analyst', 'journalist', 'officer', 'agent',
            'goes by', 'known as', 'alias', 'handle is', 'username is', 'aka', 'nickname',
            'real name', 'pseudonym', 'monitor', 'surveillance', 'intelligence', 'operative', 
            'informant', 'source', 'contact', 'asset', 'target', 'subject', 'person of interest'
        ]
        
        if any(marker in context for marker in humint_markers):
            score += 0.4  # Strong boost for HUMINT context
        
        # Dark web and cryptocurrency indicators
        dark_web_markers = [
            'tor', 'onion', 'dark web', 'hidden service', 'encrypted', 'anonymous', 'secure chat',
            'pgp key', 'bitcoin', 'ethereum', 'monero', 'zcash', 'cryptocurrency', 'wallet',
            'private key', 'secure messaging', 'signal', 'keybase', 'protonmail', 'session id'
        ]
        
        if any(marker in context for marker in dark_web_markers):
            score += 0.35  # Strong boost for dark web context
            
        # Positive signals that increase score
        
        # Username format characteristics (strong indicators)
        if '_' in username:
            score += 0.2  # Underscore is common in usernames
        
        if '-' in username:
            score += 0.15  # Hyphens are sometimes used in usernames
        
        if '.' in username and not username.endswith('.'):
            score += 0.1  # Periods are sometimes used in usernames
            
        # Mixed case that's not at the beginning (camelCase, etc.)
        if username.lower() != username and username.upper() != username:
            score += 0.15  # Intentional camelCase is a good username signal
            
        # Combination of letters and numbers (very common in usernames)
        if any(c.isalpha() for c in username) and any(c.isdigit() for c in username):
            score += 0.25  # Letter+number combinations are strong username indicators
            
        # Format matches common username patterns
        if re.match(r'^[a-z][a-z0-9_\.\-]{2,20}$', username.lower()):
            score += 0.2  # Very conventional username format
            
        # Context-based signals (weaker but useful)
        
        # Username preceded/followed by social media context
        social_media_context = [
            'username', 'user', 'account', 'profile', 'follow', 'handle', 'connect', 'id', 
            'social media', 'online', 'presence', 'digital', 'footprint', 'trace', 'activity',
            'across platforms', 'log in', 'sign in', 'credentials'
        ]
        if any(term in context for term in social_media_context):
            score += 0.15
            
        # Preceded by @ symbol is a strong indicator
        if '@' + username.lower() in context or '/@' + username.lower() in context:
            score += 0.3
            
        # Platform mentions near username
        platform_mentions = [
            'on twitter', 'on instagram', 'on github', 'github.com', 'twitter.com', 'instagram.com',
            'on telegram', 'on signal', 'on discord', 'on reddit', 'on linkedin', 'on tiktok',
            'my github', 'my twitter', 'my handle', 'find me on', 'connect with me', 'follow me at',
            'message me', 'dm me', 'reach out', 'contact me via', 'find me at', 'profile at'
        ]
        if any(mention in context for mention in platform_mentions):
            score += 0.2
        
        # Context includes verification or identification language
        verification_terms = [
            'verify', 'verification', 'confirm', 'identification', 'identify', 'authenticate',
            'validation', 'validate', 'legitimate', 'official', 'real', 'genuine', 'authentic',
            'confirmed', 'verified'
        ]
        if any(term in context for term in verification_terms):
            score += 0.15
            
        # Negative signals
        
        # Looks like a file extension
        if '.' in username and username.split('.')[-1].lower() in exclusion_categories['file_extensions']:
            score -= 0.3
            
        # Looks like a sentence fragment (multiple words)
        if ' ' in username:
            score -= 0.4
            
        # Contains too many special characters (unusual for usernames)
        special_char_count = sum(1 for c in username if not c.isalnum())
        if special_char_count > 3:
            score -= 0.2 * (special_char_count - 3)
            
        # Normalize final score to 0-1 range
        return max(0.0, min(1.0, score))
    
    # Collect username candidates with their confidence scores
    username_candidates = []
    
    # Extract usernames using the pattern matching
    for pattern, base_confidence in username_patterns:
        matches = re.finditer(pattern, text_content, re.IGNORECASE)
        for match in matches:
            # Extract the username and the surrounding context for better analysis
            match_start, match_end = match.span()
            # Get surrounding context (up to 50 chars on each side)
            context_start = max(0, match_start - 50)
            context_end = min(len(text_content), match_end + 50)
            context_before = text_content[context_start:match_start]
            context_after = text_content[match_end:context_end]
            
            # Extract username based on pattern type
            if len(match.groups()) == 1:
                username = match.group(1)
            elif len(match.groups()) >= 2 and match.group(1) == '@':
                # Handle patterns that capture both @ and the username
                username = match.group(2)
            elif len(match.groups()) >= 2:
                username = match.group(2)
            else:
                continue  # Skip if pattern doesn't match expected groups
            
            # Calculate confidence score
            confidence = score_username(username, context_before, context_after)
            
            # Apply base confidence from pattern type
            confidence = confidence * base_confidence
            
            # Only include usernames with high confidence
            if confidence > 0.6:  # Higher threshold for better precision
                username_candidates.append((username, confidence))
    
    # Sort by confidence score (highest first) and remove duplicates while preserving order
    seen = set()
    high_confidence_usernames = []
    
    for username, confidence in sorted(username_candidates, key=lambda x: x[1], reverse=True):
        if username.lower() not in seen:
            seen.add(username.lower())
            high_confidence_usernames.append(username)
    
    return high_confidence_usernames[:30]  # Return top 30 usernames to avoid overwhelming results

def extract_image_urls_from_text(text_content):
    """
    Extract potential image URLs from text content using advanced pattern recognition.
    
    Args:
        text_content (str): Text to analyze for image URLs
        
    Returns:
        list: List of potential image URLs with high confidence
    """
    # Comprehensive image URL patterns with confidence scores
    # Format: (pattern, confidence_score, needs_validation)
    image_patterns = [
        # Direct image URLs with common extensions (highest confidence)
        (r'(https?://[^\s\'"\)]+\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff))(?:\s|$|[,.\'"\)])', 0.95, False),
        
        # Common image hosting services
        (r'(https?://(?:www\.)?imgur\.com/[a-zA-Z0-9]{5,7})(?:[/\s]|$)', 0.9, True),  # Imgur links
        (r'(https?://i\.imgur\.com/[a-zA-Z0-9]{5,7}\.[a-z]{3,4})(?:[/\s]|$)', 0.95, False),  # Direct Imgur
        (r'(https?://(?:www\.)?flickr\.com/photos/[^/\s]+/\d+)(?:[/\s]|$)', 0.85, True),  # Flickr
        
        # Social media image links
        (r'(https?://(?:www\.)?instagram\.com/p/[a-zA-Z0-9_-]{10,12})(?:[/\s]|$)', 0.8, True),  # Instagram
        (r'(https?://pbs\.twimg\.com/media/[a-zA-Z0-9_-]+\.[a-z]{3,4})(?:[/\s]|$)', 0.9, False),  # Twitter
        (r'(https?://(?:www\.)?pinterest\.com/pin/\d+)(?:[/\s]|$)', 0.75, True),  # Pinterest
        
        # Image CDNs and media servers
        (r'(https?://[^\s\'"\)]+\.cloudfront\.net/[^\s\'"\)]+\.[a-z]{3,4})(?:\s|$|[,.\'"\)])', 0.9, False),
        (r'(https?://[^\s\'"\)]+\.akamaized\.net/[^\s\'"\)]+\.[a-z]{3,4})(?:\s|$|[,.\'"\)])', 0.9, False),
        (r'(https?://[^\s\'"\)]+\.staticflickr\.com/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.9, False),
        (r'(https?://[^\s\'"\)]+\.googleusercontent\.com/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.9, True),
        (r'(https?://[^\s\'"\)]+\.ggpht\.com/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.85, True),
        
        # Image search and reverse image search URLs
        (r'(https?://(?:www\.)?google\.com/imgres\?[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.7, True),
        (r'(https?://(?:www\.)?tineye\.com/search/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.7, True),
        (r'(https?://yandex\.com/images/search\?[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.7, True),
        
        # Special patterns for reverse image search templates (from unve1ler code)
        (r'(https?://lens\.google\.com/uploadbyurl\?url=\{image_link\})(?:\\n)?(?:\s|$|[,.\'"\)])', 0.8, False),
        (r'(https?://www\.bing\.com/images/search\?.*?imgurl:\{image_link\})(?:\\n)?(?:\s|$|[,.\'"\)])', 0.8, False),
        (r'(https?://yandex\.com/images/search\?.*?url=\{image_link\})(?:\\n)?(?:\s|$|[,.\'"\)])', 0.8, False),
        (r'(https?://graph\.baidu\.com/details\?.*?image=\{image_link\})(?:\\n)?(?:\s|$|[,.\'"\)])', 0.8, False),
        # Also match special formatted strings in Python f-strings found in unve1ler code
        (r'f["\'].+?(https?://lens\.google\.com/uploadbyurl\?url=\{image_link\}).+?["\']', 0.8, False),
        (r'f["\'].+?(https?://www\.bing\.com/images/search\?.+?imgurl:\{image_link\}).+?["\']', 0.8, False),
        (r'f["\'].+?(https?://yandex\.com/images/search\?.+?url=\{image_link\}).+?["\']', 0.8, False),
        (r'f["\'].+?(https?://graph\.baidu\.com/details\?.+?image=\{image_link\}).+?["\']', 0.8, False),
        # SpyBoy-specific format with color codes like f"{G}Google Lens: {Y}https://..."
        (r'[{][A-Z][}](?:Google Lens|Bing|Yandex|Baidu)[:]?\s*[{][A-Z][}](https?://.+?\{image_link\})', 0.9, False),
        
        # General photo site links (might contain images but need validation)
        (r'(https?://(?:www\.)?500px\.com/photo/\d+/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.65, True),
        (r'(https?://(?:www\.)?unsplash\.com/photos/[a-zA-Z0-9_-]+)(?:\s|$|[,.\'"\)])', 0.8, True),
        (r'(https?://(?:www\.)?pexels\.com/photo/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.8, True),
        
        # URLs with 'image' in the path (lower confidence, needs validation)
        (r'(https?://[^\s\'"\)]+/(?:images|imgs|photos|pictures|media)/[^\s\'"\)]+)(?:\s|$|[,.\'"\)])', 0.6, True),
        
        # URLs with common image query parameters (lower confidence, needs validation)
        (r'(https?://[^\s\'"\)]+\?(?:[^&]*&)*(?:image|img|photo|picture)=[^\s&\'"\)]+)(?:\s|$|[,.\'"\)])', 0.5, True)
    ]
    
    # Common image hosting domains for validation
    image_domains = [
        'imgur.com', 'i.imgur.com', 'flickr.com', 'staticflickr.com', 'instagram.com', 
        'pbs.twimg.com', 'pinimg.com', 'pinterest.com', 'unsplash.com', 'pexels.com', 
        'pixabay.com', '500px.com', 'deviantart.com', 'artstation.com', 'dropbox.com', 
        'drive.google.com', 'photos.google.com', 'cloudfront.net', 'akamaized.net', 
        'googleusercontent.com', 'ggpht.com', 'photobucket.com', 'giphy.com', 
        'media.giphy.com', 'tenor.com', 'gfycat.com', 'imgflip.com', 'cdn.discordapp.com'
    ]
    
    # Contexts that strongly suggest image URLs
    image_contexts = [
        'image', 'picture', 'photo', 'img', 'pic', 'avatar', 'thumbnail', 'banner',
        'screenshot', 'snapshot', 'gallery', 'album', 'photography', 'photographer',
        'camera', 'jpeg', 'jpg', 'png', 'gif', 'selfie', 'portrait', 'profile picture'
    ]
    
    def validate_url(url, context_text=""):
        """
        Validate if a URL is likely an image URL based on various heuristics.
        
        Args:
            url: The URL to validate
            context_text: Surrounding text for context analysis
            
        Returns:
            float: A confidence score between 0 and 1
        """
        # Start with a neutral score
        score = 0.5
        
        # Check for direct image file extensions
        if re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff)(\?|$)', url.lower()):
            score += 0.4
            
        # Check for known image hosting domains
        for domain in image_domains:
            if domain in url.lower():
                score += 0.25
                break
                
        # Check for image-related paths
        if re.search(r'/(img|image|images|photos|pictures|media|pics|thumbnails|avatars)/', url.lower()):
            score += 0.2
            
        # Check for image-related context
        context_lower = context_text.lower()
        for term in image_contexts:
            if term in context_lower:
                score += 0.15
                break
                
        # Check for image-related query parameters
        if re.search(r'[?&](img|image|photo|picture|avatar|thumbnail)=', url.lower()):
            score += 0.2
            
        # Penalize URLs that are likely not images
        if re.search(r'/(about|contact|login|signup|terms|policy|help|faq|search|cart|checkout)(/|$)', url.lower()):
            score -= 0.3
            
        # Normalize final score to 0-1 range
        return max(0.0, min(1.0, score))
    
    # Collect image URL candidates with their confidence scores
    url_candidates = []
    
    # Extract URLs using pattern matching
    for pattern, base_confidence, needs_validation in image_patterns:
        matches = re.finditer(pattern, text_content, re.IGNORECASE)
        for match in matches:
            # Extract the URL
            if len(match.groups()) >= 1:
                url = match.group(1)
                
                # Get surrounding context for validation
                match_start, match_end = match.span()
                context_start = max(0, match_start - 50)
                context_end = min(len(text_content), match_end + 50)
                context_text = text_content[context_start:context_end]
                
                # Calculate confidence score
                confidence = base_confidence
                
                # Additional validation if needed
                if needs_validation:
                    validation_score = validate_url(url, context_text)
                    confidence = (confidence + validation_score) / 2
                
                # Only include URLs with reasonable confidence
                if confidence > 0.5:  # Threshold for inclusion
                    url_candidates.append((url, confidence))
    
    # Remove duplicates and sort by confidence
    seen_urls = set()
    high_confidence_urls = []
    
    for url, confidence in sorted(url_candidates, key=lambda x: x[1], reverse=True):
        normalized_url = url.split('?')[0].rstrip('/')  # Normalize by removing query strings and trailing slashes
        if normalized_url not in seen_urls:
            seen_urls.add(normalized_url)
            high_confidence_urls.append(url)
    
    return high_confidence_urls[:20]  # Return top 20 image URLs

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
        "dark_web_information": {},
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
            
            # Extract dark web information
            # Create a mock HTML string to reuse the extract_dark_web_information function
            mock_html = f"<html><body>{content}</body></html>"
            results["dark_web_information"] = extract_dark_web_information(mock_html, content)
        
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