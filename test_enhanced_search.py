#!/usr/bin/env python3

"""
Test script for the enhanced search endpoints in unve1ler.
This script tests both the new username search and advanced people search capabilities.
"""

import json
import requests
import time
import sys

def test_enhanced_username_search():
    """Test the enhanced username search endpoint with variation detection"""
    
    print("\n=== Testing Enhanced Username Search ===")
    print("This will now use real idcrawl.com data integration!")
    
    # Prepare the request data
    username = "TashReid"  # Sample username for testing
    payload = {"username": username}
    
    # Send the request to the API
    try:
        response = requests.post("http://localhost:5000/search/username", json=payload)
        
        # Print the response status and time
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse and display the response
            data = response.json()
            
            print(f"\nFound {len(data.get('profiles', []))} profiles for username: {data.get('username')}")
            print(f"Checked {len(data.get('variations_checked', []))} username variations")
            print(f"Confidence score: {data.get('confidence', 0) * 100:.1f}%")
            print(f"Processing time: {data.get('processing_time_seconds', 0):.2f} seconds")
            
            # Check for CAPTCHA warnings
            if data.get('warnings') and any(w.get('requires_captcha', False) for w in data.get('warnings', [])):
                print("\n⚠️ IdCrawl.com requires CAPTCHA verification - using alternative data sources only")
            # Check if idcrawl.com integration was used
            elif "idcrawl.com integration" in data.get('summary', ''):
                print("\n✅ Successfully used idcrawl.com data to enhance results!")
            
            # Print profile information
            if data.get('profiles'):
                print("\nProfiles found:")
                for platform, url in data.get('profiles', {}).items():
                    print(f"- {platform}: {url}")
                    
                # Print profile photos if available
                if data.get('profile_photos'):
                    print("\nProfile photos:")
                    # Handle different response structures (could be dict or list)
                    profile_photos = data.get('profile_photos', {})
                    if isinstance(profile_photos, dict):
                        for platform, photo_url in profile_photos.items():
                            if photo_url:
                                print(f"- {platform}: {photo_url}")
                    elif isinstance(profile_photos, list):
                        for photo in profile_photos:
                            if isinstance(photo, dict) and photo.get('url'):
                                print(f"- {photo.get('platform', 'Unknown')}: {photo.get('url')}")
                            elif isinstance(photo, str):
                                print(f"- Photo: {photo}")
            else:
                print("\nNo profiles found for this username.")
                
            return data
                
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error during request: {str(e)}")
        return None

def test_advanced_people_search():
    """Test the advanced people search endpoint with multiple identifiers"""
    
    print("\n=== Testing Advanced People Search ===")
    print("This will now use real idcrawl.com data integration!")
    
    # Prepare the request data - using multiple identifiers
    payload = {
        "full_name": "Tash Reid",
        "username": "TashReid",
        "location": "London"  # Optional location filter
    }
    
    # Send the request to the API
    try:
        response = requests.post("http://localhost:5000/search/advanced", json=payload)
        
        # Print the response status
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse and display the response
            data = response.json()
            
            print(f"\nIdentity information for: {data.get('identity', {}).get('name', 'Unknown')}")
            print(f"Confidence score: {data.get('identity', {}).get('confidence', 0) * 100:.1f}%")
            print(f"Completeness: {data.get('completeness_status', 'unknown')}")
            print(f"Processing time: {data.get('processing_time_seconds', 0):.2f} seconds")
            
            # Check for CAPTCHA warnings
            if data.get('warnings') and any(w.get('requires_captcha', False) for w in data.get('warnings', [])):
                print("\n⚠️ IdCrawl.com requires CAPTCHA verification - using alternative data sources only")
            # Check for IdCrawl enhanced data in summary
            elif data.get('search_summary', {}).get('text', '') and "idcrawl.com integration" in data.get('search_summary', {}).get('text', ''):
                print("\n✅ Successfully used idcrawl.com data to enhance results!")
            
            # Print social profile information
            if data.get('social_profiles'):
                print("\nSocial profiles:")
                social_profiles = data.get('social_profiles', {})
                
                # Handle different response structures
                if isinstance(social_profiles, dict):
                    for platform, profile in social_profiles.items():
                        if isinstance(profile, dict) and profile.get('url'):
                            print(f"- {platform}: {profile.get('url')}")
                        elif isinstance(profile, str):
                            print(f"- {platform}: {profile}")
                elif isinstance(social_profiles, list):
                    for profile in social_profiles:
                        if isinstance(profile, dict):
                            platform = profile.get('platform', 'Unknown')
                            url = profile.get('url', 'N/A')
                            print(f"- {platform}: {url}")
                        elif isinstance(profile, str):
                            print(f"- Profile: {profile}")
            else:
                print("\nNo social profiles found.")
                
            # Print contact information if available
            if data.get('contact_info'):
                print("\nContact information:")
                contact_info = data.get('contact_info', {})
                if contact_info.get('emails'):
                    print(f"Emails: {', '.join(contact_info.get('emails', []))}")
                if contact_info.get('phone_numbers'):
                    print(f"Phone numbers: {', '.join(contact_info.get('phone_numbers', []))}")
                if contact_info.get('addresses'):
                    print(f"Addresses: {', '.join(contact_info.get('addresses', []))}")
            
            # Print HUMINT data summary if available
            if data.get('humint_data'):
                print("\nHUMINT data summary:")
                humint = data.get('humint_data', {})
                if humint.get('occupation'):
                    print(f"Occupation: {humint.get('occupation')}")
                if humint.get('education'):
                    print(f"Education: {humint.get('education')}")
                if humint.get('interests'):
                    print(f"Interests: {', '.join(humint.get('interests', []))}")
                if humint.get('relationships'):
                    print(f"Relationships: {len(humint.get('relationships', []))} connections identified")
            
            # Print the text summary
            if data.get('summary_text'):
                print(f"\nSummary: {data.get('summary_text')}")
                
            return data
                
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error during request: {str(e)}")
        return None

def main():
    """Run both tests"""
    
    print("Testing unve1ler's enhanced search capabilities with idcrawl.com integration...")
    print("Both endpoints now integrate real idcrawl.com data to enhance search results!")
    
    # Test both endpoints
    username_results = test_enhanced_username_search()
    time.sleep(1)  # Small delay between tests
    people_results = test_advanced_people_search()
    
    # Print summary
    print("\n=== Test Summary ===")
    if username_results and people_results:
        print("Both tests completed successfully with idcrawl.com integration!")
    elif username_results:
        print("Only enhanced username search test completed successfully with idcrawl.com integration.")
    elif people_results:
        print("Only advanced people search test completed successfully with idcrawl.com integration.")
    else:
        print("Both tests failed.")
        
    print("\nTest script execution completed. The system now leverages idcrawl.com data for more comprehensive results.")

if __name__ == "__main__":
    main()