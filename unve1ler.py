import requests
import threading
import time
from datetime import datetime
import logging

# Constants
VERSION = '1.0.1'
TIMEOUT_SECONDS = 10

def check_platform(username, platform, url, results):
    """Check if a username exists on a specific platform."""
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)

        if response.status_code == 200:
            logging.debug(f"Profile found on {platform}: {url}")
            results[platform] = url
        else:
            logging.debug(f"Profile not found on {platform}")
            results[platform] = None

    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while checking {platform}: {e}")
        results[platform] = None

def check_social_media(username, image_link=None):
    """
    Check social media platforms for a username and generate reverse image search links.
    
    Args:
        username (str): The username to search for
        image_link (str, optional): URL to an image for reverse image search
        
    Returns:
        tuple: (results, stats, reverse_image_urls)
    """
    platforms = {
        "Instagram": f"https://www.instagram.com/{username}/",
        "Twitter": f"https://twitter.com/{username}",
        "Facebook": f"https://www.facebook.com/{username}",
        "LinkedIn": f"https://www.linkedin.com/in/{username}/",
        "Pinterest": f"https://www.pinterest.com/{username}",
        "TikTok": f"https://www.tiktok.com/@{username}",
        "Snapchat": f"https://www.snapchat.com/add/{username}",
        "Linktr.ee": f"https://linktr.ee/{username}",
        "GitHub": f"https://github.com/{username}",
        "Gitlab": f"https://gitlab.com/{username}",
        "Reddit": f"https://www.reddit.com/user/{username}",
        "YouTube": f"https://www.youtube.com/user/{username}",
        "Tumblr": f"https://{username}.tumblr.com",
        "Vimeo": f"https://vimeo.com/{username}",
        "SoundCloud": f"https://soundcloud.com/{username}",
        "Flickr": f"https://www.flickr.com/people/{username}/",
        "Dribbble": f"https://dribbble.com/{username}",
        "Medium": f"https://medium.com/@{username}",
        "DeviantArt": f"https://{username}.deviantart.com",
        "Quora": f"https://www.quora.com/profile/{username}",
        "Mix": f"https://mix.com/{username}",
        "Meetup": f"https://www.meetup.com/members/{username}",
        "Goodreads": f"https://www.goodreads.com/user/show/{username}",
        "Fiverr": f"https://www.fiverr.com/{username}",
        "Wattpad": f"https://www.wattpad.com/user/{username}",
        "Steam": f"https://steamcommunity.com/id/{username}",
        "Viber": f"https://chats.viber.com/{username}",
        "Slack": f"https://{username}.slack.com",
        "Xing": f"https://www.xing.com/profile/{username}",
        "Canva": f"https://www.canva.com/{username}",
        "500px": f"https://500px.com/{username}",
        "Last.fm": f"https://www.last.fm/user/{username}",
        "Foursquare": f"https://foursquare.com/user/{username}",
        "Kik": f"https://kik.me/{username}",
        "Patreon": f"https://www.patreon.com/{username}",
        "Periscope": f"https://www.pscp.tv/{username}",
        "Twitch": f"https://www.twitch.tv/{username}",
        "Steemit": f"https://steemit.com/@{username}",
        "Vine": f"https://vine.co/u/{username}",
        "Keybase": f"https://keybase.io/{username}",
        "Zillow": f"https://www.zillow.com/profile/{username}",
        "TripAdvisor": f"https://www.tripadvisor.com/members/{username}",
        "Crunchyroll": f"https://www.crunchyroll.com/user/{username}",
        "Trello": f"https://trello.com/{username}",
        "Vero": f"https://www.vero.co/{username}",
        "CodePen": f"https://codepen.io/{username}",
        "About.me": f"https://about.me/{username}",
        "Trakt": f"https://www.trakt.tv/users/{username}",
        "Couchsurfing": f"https://www.couchsurfing.com/people/{username}",
        "Behance": f"https://www.behance.net/{username}",
        "Etsy": f"https://www.etsy.com/shop/{username}",
        "Ebay": f"https://www.ebay.com/usr/{username}",
        "Bandcamp": f"https://bandcamp.com/{username}",
        "AngelList": f"https://angel.co/u/{username}",
        "Ello": f"https://ello.co/{username}",
        "Gravatar": f"https://en.gravatar.com/{username}",
        "Instructables": f"https://www.instructables.com/member/{username}",
        "VSCO": f"https://vsco.co/{username}",
        "Letterboxd": f"https://letterboxd.com/{username}",
        "Houzz": f"https://www.houzz.com/user/{username}",
        "Digg": f"https://digg.com/@{username}",
        "Giphy": f"https://giphy.com/{username}",
        "Anchor": f"https://anchor.fm/{username}",
        "Scribd": f"https://www.scribd.com/{username}",
        "Grubhub": f"https://www.grubhub.com/profile/{username}",
        "ReverbNation": f"https://www.reverbnation.com/{username}",
        "Squarespace": f"https://{username}.squarespace.com",
        "Mixcloud": f"https://www.mixcloud.com/{username}",
        "IMDb": f"https://www.imdb.com/user/ur{username}",
        "LinkBio": f"https://lnk.bio/{username}",
        "Replit": f"https://replit.com/@{username}",
        "Ifttt": f"https://ifttt.com/p/{username}",
        "Weebly": f"https://{username}.weebly.com/",
        "Smule": f"https://www.smule.com/{username}",
        "Wordpress": f"https://{username}.wordpress.com/",
        "Tryhackme": f"https://tryhackme.com/p/{username}",
        "Myspace": f"https://myspace.com/{username}",
        "Freelancer": f"https://www.freelancer.com/u/{username}",
        "Dev.to": f"https://dev.to/{username}",
        "Blogspot": f"https://{username}.blogspot.com",
        "Gist": f"https://gist.github.com/{username}",
        "Viki": f"https://www.viki.com/users/{username}/about",
    }

    threads = []
    results = {}
    found_profiles = {}

    start_time = time.time()

    # Create and start threads
    for platform, url in platforms.items():
        thread = threading.Thread(target=check_platform, args=(username, platform, url, results))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Get statistics
    found_count = sum(1 for value in results.values() if value is not None)
    timeouts = sum(1 for value in results.values() if value is None and value is not False)
    errors = sum(1 for value in results.values() if value is False)
    
    # Format the date
    current_date = datetime.now().date()
    formatted_date = current_date.strftime("%Y-%m-%d")

    # Compile found profiles
    for platform, url in results.items():
        if url:
            found_profiles[platform] = url

    # Generate reverse image search URLs
    reverse_image_urls = None
    if image_link:
        reverse_image_urls = {
            "Google": f"https://lens.google.com/uploadbyurl?url={image_link}",
            "Bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:{image_link}",
            "Yandex": f"https://yandex.com/images/search?source=collections&&url={image_link}&rpt=imageview",
            "Baidu": f"https://graph.baidu.com/details?isfromtusoupc=1&tn=pc&carousel=0&image={image_link}"
        }
    
    # Compile statistics
    stats = {
        "target": username,
        "platforms_checked": len(platforms),
        "time_taken": f"{elapsed_time:.2f}",
        "date": formatted_date,
        "profiles_found": found_count,
        "timeouts": timeouts,
        "errors": errors
    }
    
    return found_profiles, stats, reverse_image_urls
