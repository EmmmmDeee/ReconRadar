#!/usr/bin/env python3
"""
Test client for the IdCrawl automation endpoint
"""

import requests
import json
import sys
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_idcrawl_endpoint(search_type="username", query="johndoe", location=None, use_automation=True):
    """
    Test the IdCrawl automation endpoint
    
    Args:
        search_type (str): 'username' or 'person'
        query (str): The search term to use
        location (str, optional): Location for person searches
        use_automation (bool): Whether to use automation
        
    Returns:
        dict: The response from the endpoint
    """
    url = "http://localhost:5000/test/idcrawl-automation"
    
    payload = {
        "type": search_type,
        "query": query,
        "use_automation": use_automation
    }
    
    logger.info(f"Using automation: {use_automation}")
    
    if location:
        payload["location"] = location
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Testing IdCrawl endpoint with {search_type} search for '{query}'")
        start_time = time.time()
        
        response = requests.post(url, json=payload, headers=headers)
        
        # Log timing information
        time_taken = time.time() - start_time
        logger.info(f"Request completed in {time_taken:.2f} seconds")
        
        # Parse response
        if response.status_code == 200:
            result = response.json()
            
            # Log success/failure
            if result.get("status") == "success":
                logger.info(f"Search successful! Found {len(result.get('results', {}).get('profiles', {}))} profiles")
                
                # Log automation status
                automation = result.get("automation_status", {})
                if automation.get("using_automation", False):
                    logger.info("Used browser automation for this search")
                else:
                    logger.info("Used direct HTTP requests for this search")
                
                # Return the full response for further processing
                return result
            elif result.get("status") == "captcha_required":
                logger.warning("CAPTCHA verification required. Automation may have been detected.")
                return result
            else:
                logger.error(f"Search failed: {result.get('error', 'Unknown error')}")
                return result
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            return {"error": f"HTTP {response.status_code}", "details": response.text}
            
    except Exception as e:
        logger.error(f"Error testing endpoint: {str(e)}")
        return {"error": str(e)}

def print_profiles(results):
    """
    Print profile information in a readable format
    
    Args:
        results (dict): The search results
    """
    if not results or "results" not in results:
        print("No results to display")
        return
    
    profiles = results.get("results", {}).get("profiles", {})
    if not profiles:
        print("No profiles found")
        return
    
    print("\n=== Profiles Found ===")
    for platform, url in profiles.items():
        print(f"{platform}: {url}")
    
    # Check for platform metadata
    platform_metadata = results.get("results", {}).get("platform_metadata", {})
    if platform_metadata:
        print("\n=== Platform Categories ===")
        for category, platforms in platform_metadata.get("categories", {}).items():
            if platforms:
                print(f"{category}: {', '.join(platforms)}")

if __name__ == "__main__":
    # Parse arguments
    search_type = "username"
    query = "johndoe"
    location = None
    use_automation = True
    
    # Parse all arguments
    args = sys.argv[1:]
    options = [arg for arg in args if arg.startswith("--")]
    positional = [arg for arg in args if not arg.startswith("--")]
    
    # Process positional arguments
    if len(positional) > 0:
        search_type = positional[0]
    
    if len(positional) > 1:
        query = positional[1]
    
    if len(positional) > 2 and search_type == "person":
        location = positional[2]
    
    # Process named options
    for opt in options:
        if opt.startswith("--use_automation="):
            value = opt.split("=")[1].lower()
            use_automation = value in ("true", "yes", "1", "t", "y")
        elif opt == "--no-automation":
            use_automation = False
    
    # Log parameter values
    logger.info(f"Parameters: type={search_type}, query={query}, location={location}, use_automation={use_automation}")
    
    # Run the test
    results = test_idcrawl_endpoint(search_type, query, location, use_automation)
    
    # Pretty print the results
    if results and "error" not in results:
        print_profiles(results)
        
        # Print timing information
        processing_time = results.get("processing_time_seconds", 0)
        print(f"\nProcessing time: {processing_time:.2f} seconds")
    else:
        print(f"Error: {results.get('error', 'Unknown error')}")