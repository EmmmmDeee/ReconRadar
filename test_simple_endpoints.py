#!/usr/bin/env python3
"""
Test script for the simplified HUMINT and Dark Web analysis endpoints
"""

import json
import requests
import time

def test_simple_humint():
    """Test the simplified HUMINT analysis endpoint"""
    print("\n--- Testing Simple HUMINT Analysis ---")
    
    # Load the test data
    with open('attached_assets/combined_test_data.txt', 'r') as f:
        sample_text = f.read()
    
    # Time the request
    start_time = time.time()
    
    # Make the request to the simple endpoint
    response = requests.post(
        'http://localhost:5000/analyze/simple_humint',
        json={
            'text': sample_text,
            'threshold': 0.5
        }
    )
    
    end_time = time.time()
    
    # Print the time taken
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        
        # Print the results
        if 'humint_data' in data:
            humint_data = data['humint_data']
            
            # Print confidence
            print(f"Confidence: {humint_data.get('confidence', 0):.2f}")
            
            # Print names
            if 'names' in humint_data and humint_data['names']:
                print(f"Names ({len(humint_data['names'])}): {', '.join(humint_data['names'][:3])}")
                
            # Print aliases
            if 'aliases' in humint_data and humint_data['aliases']:
                print(f"Aliases ({len(humint_data['aliases'])}): {', '.join(humint_data['aliases'][:3])}")
                
            # Print organizations
            if 'organizations' in humint_data and humint_data['organizations']:
                print(f"Organizations ({len(humint_data['organizations'])}): {', '.join(humint_data['organizations'][:3])}")
                
            # Print occupations
            if 'occupations' in humint_data and humint_data['occupations']:
                print(f"Occupations ({len(humint_data['occupations'])}): {', '.join(humint_data['occupations'][:3])}")
                
            # Print relationships
            if 'relationships' in humint_data and humint_data['relationships']:
                print(f"Relationships ({len(humint_data['relationships'])}): {', '.join(humint_data['relationships'][:3])}")
                
            # Print biographical data
            if 'biographical' in humint_data:
                bio = humint_data['biographical']
                print("\nBiographical Information:")
                if bio.get('age'):
                    print(f"  Age: {bio['age']}")
                if bio.get('birth_date'):
                    print(f"  Birth date: {bio['birth_date']}")
                if bio.get('education') and len(bio['education']) > 0:
                    print(f"  Education: {', '.join(bio['education'][:2])}")
                if bio.get('employment_history') and len(bio['employment_history']) > 0:
                    print(f"  Employment: {', '.join(bio['employment_history'][:2])}")
                if bio.get('languages') and len(bio['languages']) > 0:
                    print(f"  Languages: {', '.join(bio['languages'])}")
                if bio.get('skills') and len(bio['skills']) > 0:
                    print(f"  Skills: {', '.join(bio['skills'][:3])}")
        else:
            print("No HUMINT data found in the response")
    else:
        print(f"Error: {response.status_code} - {response.text}")

def test_simple_darkweb():
    """Test the simplified Dark Web analysis endpoint"""
    print("\n--- Testing Simple Dark Web Analysis ---")
    
    # Load the test data
    with open('attached_assets/combined_test_data.txt', 'r') as f:
        sample_text = f.read()
    
    # Time the request
    start_time = time.time()
    
    # Make the request to the simple endpoint
    response = requests.post(
        'http://localhost:5000/analyze/simple_darkweb',
        json={
            'text': sample_text,
            'threshold': 0.5
        }
    )
    
    end_time = time.time()
    
    # Print the time taken
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        
        # Print the results
        if 'dark_web_data' in data:
            dark_web_data = data['dark_web_data']
            
            # Print confidence
            print(f"Confidence: {dark_web_data.get('confidence', 0):.2f}")
            
            # Print onion services
            if 'onion_services' in dark_web_data and dark_web_data['onion_services']:
                print(f"Onion Services ({len(dark_web_data['onion_services'])}): {', '.join(dark_web_data['onion_services'][:3])}")
                
            # Print cryptocurrency addresses
            if 'cryptocurrency_addresses' in dark_web_data:
                for crypto_type, addresses in dark_web_data['cryptocurrency_addresses'].items():
                    if addresses:
                        print(f"{crypto_type.capitalize()} Addresses ({len(addresses)}): {', '.join(addresses[:2])}")
                
            # Print secure messaging
            if 'secure_messaging' in dark_web_data:
                for msg_type, items in dark_web_data['secure_messaging'].items():
                    if items:
                        print(f"{msg_type.capitalize()} Messaging ({len(items)}): {', '.join(items[:2])}")
                
            # Print security indicators
            if 'security_indicators' in dark_web_data and dark_web_data['security_indicators']:
                print(f"Security Indicators ({len(dark_web_data['security_indicators'])}): {', '.join(dark_web_data['security_indicators'][:3])}")
        else:
            print("No Dark Web data found in the response")
    else:
        print(f"Error: {response.status_code} - {response.text}")

def main():
    """Run both simplified endpoint tests"""
    print("Testing Simplified Endpoints")
    print("============================")
    
    test_simple_humint()
    test_simple_darkweb()

if __name__ == "__main__":
    main()