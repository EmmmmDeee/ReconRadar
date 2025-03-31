#!/usr/bin/env python3
"""
Test file for verifying the integration of IDCrawl automation
"""

import logging
import json
from idcrawl_scraper import (
    search_username_on_idcrawl, 
    search_person_on_idcrawl,
    enrich_results_with_idcrawl
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_username_search(username="test_user123", use_automation=True):
    """Test searching for a username with automation"""
    logger.info(f"Testing username search for '{username}' with automation={use_automation}")
    result = search_username_on_idcrawl(username, use_automation=use_automation)
    logger.info(f"Search successful: {result.get('success', False)}")
    logger.info(f"Profiles found: {len(result.get('profiles', {}))}")
    return result

def test_person_search(name="John Smith", location=None, use_automation=True):
    """Test searching for a person with automation"""
    logger.info(f"Testing person search for '{name}' with automation={use_automation}")
    result = search_person_on_idcrawl(name, location, use_automation=use_automation)
    logger.info(f"Search successful: {result.get('success', False)}")
    logger.info(f"Profiles found: {len(result.get('profiles', {}))}")
    return result

def test_result_enrichment(use_automation=True):
    """Test enriching search results with data from IDCrawl"""
    # Create fake original results
    original_results = {
        "search_term": "johndoe",
        "profiles": {
            "Twitter": "https://twitter.com/johndoe",
            "GitHub": "https://github.com/johndoe"
        },
        "confidence": 0.7,
        "discovered_data": {
            "possible_real_names": ["John Doe"],
            "possible_locations": [],
            "possible_occupations": []
        }
    }
    
    logger.info(f"Testing result enrichment with automation={use_automation}")
    result = enrich_results_with_idcrawl(
        original_results, 
        username="johndoe", 
        skip_idcrawl=False,
        use_automation=use_automation
    )
    
    if "warnings" in result and any(w.get("requires_captcha", False) for w in result.get("warnings", [])):
        logger.warning("CAPTCHA detected during enrichment")
    
    # Check if new profiles were added
    original_count = len(original_results.get("profiles", {}))
    new_count = len(result.get("profiles", {}))
    logger.info(f"Original profiles: {original_count}, New profiles: {new_count}")
    logger.info(f"New confidence: {result.get('confidence', 0)}")
    
    return result

if __name__ == "__main__":
    import sys
    
    print("=== IDCrawl Automation Integration Test ===")
    print("Note: These tests require browser installation.")
    print("  Run 'python -m playwright install' first for full functionality.")
    print()
    
    test_type = "all"
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    
    # By default, try with automation
    use_automation = True
    if len(sys.argv) > 2 and sys.argv[2].lower() == "no-automation":
        use_automation = False
        print("Running tests with automation disabled (will use direct HTTP requests)")
    
    if test_type in ["username", "all"]:
        print("\n=== Username Search Test ===")
        username = "john_doe123" if len(sys.argv) <= 3 else sys.argv[3]
        result = test_username_search(username, use_automation)
        print(f"Result summary: {'Success' if result.get('success', False) else 'Failed'}")
        
    if test_type in ["person", "all"]:
        print("\n=== Person Search Test ===")
        name = "Jane Smith" if len(sys.argv) <= 4 else sys.argv[4]
        location = None if len(sys.argv) <= 5 else sys.argv[5]
        result = test_person_search(name, location, use_automation)
        print(f"Result summary: {'Success' if result.get('success', False) else 'Failed'}")
        
    if test_type in ["enrich", "all"]:
        print("\n=== Result Enrichment Test ===")
        result = test_result_enrichment(use_automation)
        if "warnings" in result and any(w.get("requires_captcha", False) for w in result.get("warnings", [])):
            print("Result: CAPTCHA detected, enrichment limited to original data")
        else:
            print(f"Result: Enrichment {'successful' if result.get('success', False) else 'failed'}")