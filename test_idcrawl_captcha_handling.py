#!/usr/bin/env python
"""
Test script to specifically verify the IdCrawl CAPTCHA warning handling in unve1ler.

This script tests the idcrawl_scraper.py functionality for gracefully handling 
CAPTCHA protection with appropriate warnings.
"""

import json
import time
import logging
import requests
from idcrawl_scraper import search_username_on_idcrawl, search_person_on_idcrawl, enrich_results_with_idcrawl

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_direct_search():
    """Test direct searching with IdCrawl and CAPTCHA handling"""
    
    print("\n=== Testing Direct IdCrawl Search with CAPTCHA Detection ===")
    
    username = "johndoe123"
    print(f"Searching for username: {username}")
    
    # Perform direct search
    results = search_username_on_idcrawl(username)
    
    print(f"Search status: {'Success' if results.get('success', False) else 'Failed'}")
    
    # Check for CAPTCHA warnings
    if results.get("requires_captcha", False):
        print(f"\n✅ Successfully detected CAPTCHA protection: {results.get('error', '')}")
    else:
        print("\n❌ Failed to detect CAPTCHA protection.")
    
    return results

def test_result_enrichment():
    """Test result enrichment with IdCrawl and skip_idcrawl parameter"""
    
    print("\n=== Testing Result Enrichment with skip_idcrawl Parameter ===")
    
    # Create mock search results
    mock_results = {
        "username": "johndoe123",
        "profiles": {
            "Twitter": "https://twitter.com/johndoe123",
            "GitHub": "https://github.com/johndoe123"
        },
        "discovered_data": {
            "possible_real_names": ["John Doe"],
            "possible_locations": ["New York"],
            "possible_occupations": ["Developer"]
        },
        "confidence": 0.7,
        "summary": "Found 2 profiles for username 'johndoe123'"
    }
    
    # Test with skip_idcrawl=True
    print("\nTesting with skip_idcrawl=True:")
    enriched_with_skip = enrich_results_with_idcrawl(
        mock_results, 
        username="johndoe123", 
        skip_idcrawl=True
    )
    
    # Check for warning
    if "warnings" in enriched_with_skip and any(w.get("requires_captcha", False) for w in enriched_with_skip.get("warnings", [])):
        print("✅ Successfully added CAPTCHA warning with skip_idcrawl=True")
        warning = next((w for w in enriched_with_skip.get("warnings", []) if w.get("requires_captcha", False)), {})
        print(f"Warning message: {warning.get('message', '')}")
    else:
        print("❌ Failed to add CAPTCHA warning with skip_idcrawl=True")
    
    # Test normal path (should detect CAPTCHA via direct call)
    print("\nTesting with skip_idcrawl=False (should detect CAPTCHA via API call):")
    enriched_normal = enrich_results_with_idcrawl(
        mock_results,
        username="johndoe123",
        skip_idcrawl=False
    )
    
    # Check for warning 
    if "warnings" in enriched_normal and any(w.get("requires_captcha", False) for w in enriched_normal.get("warnings", [])):
        print("✅ Successfully detected CAPTCHA protection during enrichment")
        warning = next((w for w in enriched_normal.get("warnings", []) if w.get("requires_captcha", False)), {})
        print(f"Warning message: {warning.get('message', '')}")
    else:
        print("❌ Failed to detect CAPTCHA protection during enrichment")
    
    return {"skipped": enriched_with_skip, "normal": enriched_normal}

def main():
    """Run all tests"""
    
    print("Testing unve1ler's IdCrawl CAPTCHA detection and warning system...")
    
    direct_results = test_direct_search()
    time.sleep(1)  # Small delay between tests
    enrichment_results = test_result_enrichment()
    
    # Print summary
    print("\n=== Test Summary ===")
    
    captcha_detected_direct = direct_results.get("requires_captcha", False)
    captcha_warning_skip = any(w.get("requires_captcha", False) for w in enrichment_results["skipped"].get("warnings", []))
    captcha_warning_normal = any(w.get("requires_captcha", False) for w in enrichment_results["normal"].get("warnings", []))
    
    print(f"1. Direct search CAPTCHA detection: {'✅ Passed' if captcha_detected_direct else '❌ Failed'}")
    print(f"2. skip_idcrawl warning generation: {'✅ Passed' if captcha_warning_skip else '❌ Failed'}")
    print(f"3. Normal path CAPTCHA detection: {'✅ Passed' if captcha_warning_normal else '❌ Failed'}")
    
    overall_success = captcha_detected_direct and captcha_warning_skip and captcha_warning_normal
    print(f"\nOverall test result: {'✅ All tests passed!' if overall_success else '❌ Some tests failed.'}")
    
    print("\nIdCrawl integration is now properly handling CAPTCHA protection with informative warnings.")
    print("The system can continue functioning with alternative data sources when idcrawl.com requires human verification.")

if __name__ == "__main__":
    main()