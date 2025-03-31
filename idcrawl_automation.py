#!/usr/bin/env python3
"""
IDCrawl Automation Script for unve1ler OSINT Tool
This script uses Playwright to automate searches on idcrawl.com and extract profile data
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
import argparse
import sys
import random
import time
import json
import re
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('idcrawl_automation')

# --- Constants ---
DEFAULT_TIMEOUT = 60000  # 60 seconds
NAVIGATION_TIMEOUT = 90000  # 90 seconds
RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5
BLOCK_RESOURCE_TYPES = ["image", "font", "media", "stylesheet"]
BLOCK_URL_PATTERNS = [
    "*google-analytics.com*", "*googletagmanager.com*", "*doubleclick.net*",
    "*facebook.net/tr*", "*scorecardresearch.com*", "*quantserve.com*"
]
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
]

# --- Actual Selectors from IDCrawl based on provided HTML ---
# Homepage elements
SEARCH_INPUT_SELECTOR = 'input[type="text"][name="q"]'
SEARCH_BUTTON_SELECTOR = 'button[type="submit"]'
STATE_SELECTOR = 'select[name="state"]'
CSRF_META_SELECTOR = 'meta[name="csrf-token"]'

# Results page sections
INSTAGRAM_ITEMS_SELECTOR = 'h2:has-text("Instagram") + .results .item'
TWITTER_ITEMS_SELECTOR = 'h2:has-text("Twitter") + .results .item'
FACEBOOK_ITEMS_SELECTOR = 'h2:has-text("Facebook") + .results .item'
TIKTOK_ITEMS_SELECTOR = 'h2:has-text("TikTok") + .results .item'
LINKEDIN_ITEMS_SELECTOR = 'h2:has-text("LinkedIn") + .results .item'
QUORA_ITEMS_SELECTOR = 'h2:has-text("Quora") + .results .item'
USERNAMES_ITEMS_SELECTOR = 'h2:has-text("Usernames") + .results li'
WEB_RESULTS_ITEMS_SELECTOR = 'h2:has-text("Web results") + .results .result'

# Selectors relative to result items
PROFILE_LINK_SELECTOR = "a"
PROFILE_NAME_SELECTOR = ".name, .title, h3, strong"
PROFILE_USERNAME_SELECTOR = ".username, .handle, .subtitle"
PROFILE_IMAGE_SELECTOR = "img"

# Web results specific selectors
WEB_RESULT_TITLE_SELECTOR = "h3.title > a, .title > a"
WEB_RESULT_LINK_SELECTOR = "h3.title > a, .title > a"
WEB_RESULT_SNIPPET_SELECTOR = ".snippet, .description"

# Sponsored Blocks Selectors
SPONSORED_BLOCK_SELECTOR = ".sponsor-unit, .sponsored"
SPONSORED_TOPIC_SELECTOR = "xpath=preceding-sibling::h2[1]"  # Relative to sponsor block
SPONSORED_LINK_SELECTOR = "a.cta, a.button, a.link"  # Relative to sponsor block

# --- Helper Functions ---
async def safe_get_text(locator, default="N/A"):
    """Safely extract text content from a locator with timeout handling"""
    try:
        return (await locator.text_content(timeout=5000) or "").strip() or default
    except Exception:
        return default

async def safe_get_attribute(locator, attribute, default="N/A"):
    """Safely extract attribute from a locator with timeout handling"""
    try:
        return (await locator.get_attribute(attribute, timeout=5000) or "").strip() or default
    except Exception:
        return default

# --- Retry Decorator ---
retry_decorator = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_fixed(RETRY_WAIT_SECONDS),
    retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
    reraise=True
)

# --- Resource Blocker ---
async def block_resources(route, request):
    """Block specified resource types and URL patterns to speed up page loads"""
    is_blocked_type = request.resource_type in BLOCK_RESOURCE_TYPES
    is_blocked_url = any(re.match(pattern.replace("*", ".*"), request.url) for pattern in BLOCK_URL_PATTERNS)
    if is_blocked_type or is_blocked_url:
        await route.abort()
    else:
        await route.continue_()

# --- Parsing Functions ---
async def parse_generic_profile_section(page, section_name, item_selector, data_dict):
    """Extract profile data from a section like Instagram, Twitter, etc."""
    items_data = []
    logger.info(f"Parsing '{section_name}' section")
    try:
        item_locators = page.locator(item_selector)
        count = await item_locators.count()
        logger.info(f"Found {count} potential '{section_name}' items")
        
        for i in range(count):
            item = item_locators.nth(i)
            link_locator = item.locator(PROFILE_LINK_SELECTOR).first
            primary_text_locator = item.locator(PROFILE_NAME_SELECTOR).first
            secondary_text_locator = item.locator(PROFILE_USERNAME_SELECTOR).first
            img_locator = item.locator(PROFILE_IMAGE_SELECTOR).first
            
            url = await safe_get_attribute(link_locator, 'href')
            primary_text = await safe_get_text(primary_text_locator)
            secondary_text = await safe_get_text(secondary_text_locator)
            full_text = await safe_get_text(item) if primary_text == "N/A" else primary_text
            img_src = await safe_get_attribute(img_locator, 'src')
            
            if url != "N/A":
                items_data.append({
                    "primary_text": primary_text,
                    "secondary_text": secondary_text,
                    "full_text": full_text.strip(),
                    "url": url,
                    "img_src": img_src
                })
        
        data_dict[section_name] = items_data
        logger.info(f"Parsed {len(items_data)} '{section_name}' items")
    except Exception as e:
        logger.error(f"Error parsing '{section_name}': {e}")
        data_dict[section_name] = []

async def parse_usernames(page, item_selector, data_dict):
    """Extract username listings"""
    usernames = []
    logger.info(f"Parsing 'Usernames' section")
    try:
        username_locators = page.locator(item_selector)
        count = await username_locators.count()
        logger.info(f"Found {count} potential username elements")
        
        for i in range(count):
            username_text = await safe_get_text(username_locators.nth(i))
            if username_text != "N/A" and "show all results" not in username_text.lower():
                usernames.append(username_text.strip())
        
        data_dict["Usernames"] = usernames
        logger.info(f"Parsed {len(usernames)} usernames")
    except Exception as e:
        logger.error(f"Error parsing Usernames: {e}")
        data_dict["Usernames"] = []

async def parse_web_results(page, item_selector, title_selector, link_selector, snippet_selector, data_dict):
    """Extract web search results"""
    web_results = []
    logger.info(f"Parsing 'Web results' section")
    try:
        item_locators = page.locator(item_selector)
        count = await item_locators.count()
        logger.info(f"Found {count} potential Web results")
        
        for i in range(count):
            item = item_locators.nth(i)
            title_elem = item.locator(title_selector).first
            link_elem = item.locator(link_selector).first
            snippet_elem = item.locator(snippet_selector).first
            
            title = await safe_get_text(title_elem)
            link = await safe_get_attribute(link_elem, 'href')
            snippet = await safe_get_text(snippet_elem)
            
            if link != "N/A":
                web_results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })
        
        data_dict["Web results"] = web_results
        logger.info(f"Parsed {len(web_results)} Web results")
    except Exception as e:
        logger.error(f"Error parsing Web results: {e}")
        data_dict["Web results"] = []

async def parse_sponsored(page, block_selector, topic_selector, link_selector, data_dict):
    """Extract sponsored blocks and links"""
    sponsored_links = {}
    logger.info(f"Parsing 'Sponsored' sections")
    try:
        sponsor_blocks = page.locator(block_selector)
        count = await sponsor_blocks.count()
        logger.info(f"Found {count} potential Sponsored blocks")
        
        for i in range(count):
            block = sponsor_blocks.nth(i)
            
            # Get topic from preceding h2
            topic_elem = block.locator(topic_selector)
            topic = await safe_get_text(topic_elem, "Sponsored")
            
            # Get links within the block
            links = block.locator(link_selector)
            link_count = await links.count()
            link_data = []
            
            for j in range(link_count):
                link_elem = links.nth(j)
                url = await safe_get_attribute(link_elem, 'href')
                text = await safe_get_text(link_elem)
                if url != "N/A":
                    link_data.append({"text": text, "url": url})
            
            if topic not in sponsored_links:
                sponsored_links[topic] = []
            
            sponsored_links[topic].extend(link_data)
        
        data_dict["Sponsored"] = sponsored_links
        total_links = sum(len(links) for links in sponsored_links.values())
        logger.info(f"Parsed {total_links} Sponsored links from {len(sponsored_links)} categories")
    except Exception as e:
        logger.error(f"Error parsing Sponsored sections: {e}")
        data_dict["Sponsored"] = {}

# --- Main Search Function ---
@retry_decorator
async def perform_search(search_term, state=None, browser_type="chromium", 
                         screenshot_path=None, html_output_path=None, 
                         json_output_path=None, proxy=None, user_agent=None,
                         block_resources_flag=True, use_stealth=True, headless=False):
    """
    Perform an automated search on idcrawl.com and extract results
    
    Args:
        search_term: The person's name or username to search for
        state: Optional state filter for US searches
        browser_type: Browser to use (chromium, firefox, webkit)
        screenshot_path: Optional path to save screenshot
        html_output_path: Optional path to save HTML content
        json_output_path: Optional path to save JSON results
        proxy: Optional proxy server to use
        user_agent: Optional user agent to use
        block_resources_flag: Whether to block unnecessary resources
        use_stealth: Whether to use stealth techniques
        headless: Whether to run in headless mode (default: False)
        
    Returns:
        Dictionary containing parsed results
    """
    results = {
        "search_info": {
            "search_term": search_term,
            "state": state,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "Instagram": [],
        "Twitter": [],
        "Facebook": [],
        "TikTok": [],
        "LinkedIn": [],
        "Quora": [],
        "Usernames": [],
        "Web results": [],
        "Sponsored": {},
        "metadata": {
            "success": False,
            "captcha_detected": False,
            "error": None,
        }
    }
    
    start_time = time.time()
    
    try:
        logger.info(f"Starting search for '{search_term}'")
        if state:
            logger.info(f"Using state filter: {state}")
        
        async with async_playwright() as p:
            browser_options = {}
            if proxy:
                browser_options["proxy"] = {"server": proxy}
            
            # Select browser based on input
            if browser_type == "firefox":
                browser = await p.firefox.launch(headless=headless, **browser_options)
            elif browser_type == "webkit":
                browser = await p.webkit.launch(headless=headless, **browser_options)
            else:  # Default to chromium
                browser = await p.chromium.launch(headless=headless, **browser_options)
            
            # Create context with random user agent for fingerprint diversity
            selected_user_agent = user_agent or random.choice(USER_AGENTS)
            context = await browser.new_context(
                user_agent=selected_user_agent,
                viewport={"width": 1280, "height": 800},
                device_scale_factor=1.0,
                java_script_enabled=True,
                has_touch=False,
                is_mobile=False,
                locale="en-US",
                timezone_id="America/New_York",
            )
            
            # Apply stealth if requested
            if use_stealth:
                try:
                    from playwright_stealth import stealth_async
                    page = await context.new_page()
                    await stealth_async(page)
                    logger.info("Applied stealth techniques to page")
                except ImportError:
                    logger.warning("playwright-stealth not available, continuing without stealth")
                    page = await context.new_page()
            else:
                page = await context.new_page()
            
            # Set timeouts
            page.set_default_timeout(DEFAULT_TIMEOUT)
            page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
            
            # Block unnecessary resources if requested
            if block_resources_flag:
                await page.route("**/*", block_resources)
                logger.info("Resource blocking enabled")
            
            # Navigate to IDCrawl
            logger.info("Navigating to idcrawl.com")
            try:
                await page.goto("https://www.idcrawl.com/", wait_until="domcontentloaded")
            except PlaywrightTimeoutError:
                logger.warning("Initial page load timed out, will try to continue")
            
            # Check for CAPTCHA or bot detection
            if await page.title() and "captcha" in await page.title().lower() or await page.content() and "captcha" in await page.content().lower():
                logger.error("CAPTCHA detected on homepage")
                results["metadata"]["captcha_detected"] = True
                await browser.close()
                return results
            
            # Wait for search input to be visible
            try:
                search_input = page.locator(SEARCH_INPUT_SELECTOR)
                await search_input.wait_for(state="visible", timeout=10000)
                
                # Enter search term
                await search_input.fill(search_term)
                logger.info(f"Entered search term: {search_term}")
                
                # Set state if provided
                if state:
                    state_select = page.locator(STATE_SELECTOR)
                    if await state_select.count() > 0:
                        await state_select.select_option(state)
                        logger.info(f"Selected state: {state}")
                
                # Submit search
                search_button = page.locator(SEARCH_BUTTON_SELECTOR)
                await search_button.click()
                logger.info("Submitted search")
                
                # Wait for search results
                await page.wait_for_load_state("domcontentloaded")
                logger.info("Results page loaded")
                
                # Check for CAPTCHA on results page
                if await page.title() and "captcha" in await page.title().lower() or await page.content() and "captcha" in await page.content().lower():
                    logger.error("CAPTCHA detected on results page")
                    results["metadata"]["captcha_detected"] = True
                    await browser.close()
                    return results
                
                # Take screenshot if requested
                if screenshot_path:
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"Screenshot saved to {screenshot_path}")
                
                # Save HTML content if requested
                if html_output_path:
                    content = await page.content()
                    with open(html_output_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"HTML content saved to {html_output_path}")
                
                # Parse different sections
                await parse_generic_profile_section(page, "Instagram", INSTAGRAM_ITEMS_SELECTOR, results)
                await parse_generic_profile_section(page, "Twitter", TWITTER_ITEMS_SELECTOR, results)
                await parse_generic_profile_section(page, "Facebook", FACEBOOK_ITEMS_SELECTOR, results)
                await parse_generic_profile_section(page, "TikTok", TIKTOK_ITEMS_SELECTOR, results)
                await parse_generic_profile_section(page, "LinkedIn", LINKEDIN_ITEMS_SELECTOR, results)
                await parse_generic_profile_section(page, "Quora", QUORA_ITEMS_SELECTOR, results)
                await parse_usernames(page, USERNAMES_ITEMS_SELECTOR, results)
                await parse_web_results(page, WEB_RESULTS_ITEMS_SELECTOR, WEB_RESULT_TITLE_SELECTOR, 
                                       WEB_RESULT_LINK_SELECTOR, WEB_RESULT_SNIPPET_SELECTOR, results)
                await parse_sponsored(page, SPONSORED_BLOCK_SELECTOR, SPONSORED_TOPIC_SELECTOR, 
                                     SPONSORED_LINK_SELECTOR, results)
                
                results["metadata"]["success"] = True
                end_time = time.time()
                results["metadata"]["processing_time"] = round(end_time - start_time, 2)
                logger.info(f"Search completed successfully in {results['metadata']['processing_time']} seconds")
                
            except PlaywrightTimeoutError as e:
                logger.error(f"Timeout error: {e}")
                results["metadata"]["error"] = f"Timeout: {str(e)}"
                if screenshot_path:
                    await page.screenshot(path=f"error_{screenshot_path}", full_page=True)
            except PlaywrightError as e:
                logger.error(f"Playwright error: {e}")
                results["metadata"]["error"] = f"Browser error: {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                results["metadata"]["error"] = f"Error: {str(e)}"
            
            # Save results to JSON if requested
            if json_output_path:
                with open(json_output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Results saved to {json_output_path}")
            
            await browser.close()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        results["metadata"]["error"] = f"Fatal error: {str(e)}"
    
    return results

# --- Command Line Interface ---
async def main():
    """Command line interface for IDCrawl automation script"""
    parser = argparse.ArgumentParser(description="IDCrawl Automation Script")
    parser.add_argument("-s", "--search", required=True, help="Search term (name or username)")
    parser.add_argument("--state", help="State filter for US searches")
    parser.add_argument("-b", "--browser", default="chromium", choices=["chromium", "firefox", "webkit"], 
                        help="Browser to use")
    parser.add_argument("-p", "--screenshot", help="Path to save screenshot")
    parser.add_argument("-o", "--html-output", help="Path to save HTML content")
    parser.add_argument("-j", "--json-output", help="Path to save JSON results")
    parser.add_argument("--proxy", help="Proxy server (e.g., http://proxy:port)")
    parser.add_argument("-u", "--user-agent", help="Custom User-Agent")
    parser.add_argument("--no-block", action="store_true", help="Disable resource blocking")
    parser.add_argument("--no-stealth", action="store_true", help="Disable stealth techniques")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Perform search
    results = await perform_search(
        search_term=args.search,
        state=args.state,
        browser_type=args.browser,
        screenshot_path=args.screenshot,
        html_output_path=args.html_output,
        json_output_path=args.json_output,
        proxy=args.proxy,
        user_agent=args.user_agent,
        block_resources_flag=not args.no_block,
        use_stealth=not args.no_stealth,
        headless=args.headless
    )
    
    # Print summary to console
    print("\n--- Search Summary ---")
    print(f"Search term: {args.search}")
    if args.state:
        print(f"State: {args.state}")
    print(f"Success: {results['metadata']['success']}")
    
    if results['metadata']['captcha_detected']:
        print("WARNING: CAPTCHA detected, results may be limited")
    
    if results['metadata']['error']:
        print(f"Error: {results['metadata']['error']}")
    
    print("\n--- Results Summary ---")
    for platform in ["Instagram", "Twitter", "Facebook", "TikTok", "LinkedIn", "Quora"]:
        print(f"{platform}: {len(results[platform])} profiles found")
    
    print(f"Usernames: {len(results['Usernames'])} found")
    print(f"Web results: {len(results['Web results'])} found")
    
    sponsor_count = sum(len(links) for links in results["Sponsored"].values())
    print(f"Sponsored links: {sponsor_count} found in {len(results['Sponsored'])} categories")
    
    if not args.json_output:
        print("\nTip: Use -j/--json-output to save full results to a JSON file")

if __name__ == "__main__":
    asyncio.run(main())