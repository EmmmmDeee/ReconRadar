#!/usr/bin/env python3
"""
Test script for unve1ler's HUMINT and Dark Web analysis capabilities
"""

import requests
import json
from pprint import pprint

API_URL = "http://0.0.0.0:5000"

def test_humint_analysis():
    """Test HUMINT data extraction functionality"""
    print("\n=== Testing HUMINT Analysis ===\n")
    
    # Sample text with HUMINT data
    humint_test_data = """
# HUMINT Test Data

## Personal Information
My name is James Wilson and I am a Cybersecurity Researcher at DigitalDefense Inc.
Born on February 15, 1985, I have been working in the security field for over 12 years.
I graduated from MIT with a degree in Computer Science in 2007.
You can reach me at james.wilson@example.com or call my office at (555) 123-4567.

## Professional Background
I currently work with Dr. Sarah Johnson, the Chief Security Officer at our company.
My previous employer was CyberGuard Technologies, where I worked as a Senior Security Analyst.
My colleague Robert Chen and I co-authored the paper "Advanced Threat Detection Methods" in 2019.
I am also an adjunct professor at Stanford University teaching cybersecurity courses.

## Personal Relationships
My wife, Emily Wilson, is a software engineer at Google.
We have two children, Michael (10) and Sophia (7).
My brother David Wilson works in finance at JP Morgan.
I regularly collaborate with my mentor Dr. Richard Thompson from the University of Washington.
    """
    
    # Send POST request to the HUMINT analysis endpoint
    response = requests.post(
        f"{API_URL}/analyze/humint",
        json={"text": humint_test_data, "threshold": 0.5}
    )
    
    if response.status_code == 200:
        data = response.json()
        
        # Display HUMINT analysis results
        print("HUMINT Analysis Results:")
        print(f"Confidence: {data['results']['humint_data']['confidence']}")
        print(f"Completeness score: {data['results']['completeness']}")
        
        # Display names found
        if data['results']['humint_data'].get('names'):
            print("\nNames identified:")
            for name in data['results']['humint_data']['names'][:5]:  # Display top 5
                print(f"- {name}")
        
        # Display occupations found
        if data['results']['humint_data'].get('occupations'):
            print("\nOccupations identified:")
            for occupation in data['results']['humint_data']['occupations'][:5]:  # Display top 5
                print(f"- {occupation}")
        
        # Display biographical information
        bio = data['results']['humint_data'].get('biographical', {})
        if bio.get('birth_date') or bio.get('age') or bio.get('education'):
            print("\nBiographical information:")
            if bio.get('birth_date'):
                print(f"- Birth date: {bio['birth_date']}")
            if bio.get('age'):
                print(f"- Age: {bio['age']}")
            if bio.get('education'):
                for edu in bio['education'][:3]:  # Display top 3
                    print(f"- Education: {edu}")
        
        # Display relationships found
        if data['results']['humint_data'].get('relationships'):
            print("\nRelationships identified:")
            for relationship in data['results']['humint_data']['relationships'][:5]:  # Display top 5
                print(f"- {relationship}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_darkweb_analysis():
    """Test Dark Web detection functionality"""
    print("\n=== Testing Dark Web Analysis ===\n")
    
    # Sample text with dark web indicators
    darkweb_test_data = """
# Dark Web Test Data

## Cryptocurrency Addresses
Bitcoin: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Ethereum: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

## Dark Web References
Onion Service: https://expyuzz4wqqyqhjn.onion
Alternate Service: http://explorerzydxu5ecjrkwceayqybizmpjjznk5izmitf2modhcusuqlid.onion
Secure Email: john.doe@protonmail.com
Secure Contact: @john_secure on Keybase

## Security Terminology
I use end-to-end encryption for all my communications.
Air-gapped systems are preferred for sensitive data processing.
Multi-factor authentication is enabled on all my accounts.
I regularly rotate my PGP keys for enhanced security.
    """
    
    # Send POST request to the Dark Web analysis endpoint
    response = requests.post(
        f"{API_URL}/analyze/darkweb",
        json={"text": darkweb_test_data, "threshold": 0.5}
    )
    
    if response.status_code == 200:
        data = response.json()
        
        # Display Dark Web analysis results
        print("Dark Web Analysis Results:")
        if 'analysis' in data['results'] and 'confidence' in data['results']['analysis']:
            print(f"Confidence: {data['results']['analysis']['confidence']}")
        
        # Display indicators
        if data['results'].get('indicators'):
            print("\nDark Web Indicators:")
            for indicator in data['results']['indicators']:
                print(f"- {indicator['description']} (Confidence: {indicator['confidence']})")
        
        # Display cryptocurrency addresses
        crypto = data['results']['analysis'].get('cryptocurrency_addresses', {})
        if crypto:
            print("\nCryptocurrency Addresses:")
            for crypto_type, addresses in crypto.items():
                for address in addresses:
                    print(f"- {crypto_type.capitalize()}: {address}")
        
        # Display onion services
        if data['results']['analysis'].get('onion_services'):
            print("\nOnion Services:")
            for service in data['results']['analysis']['onion_services']:
                print(f"- {service}")
        
        # Display secure messaging
        secure_msg = data['results']['analysis'].get('secure_messaging', {})
        if secure_msg:
            print("\nSecure Messaging:")
            for msg_type, identifiers in secure_msg.items():
                for identifier in identifiers:
                    print(f"- {msg_type.capitalize()}: {identifier}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def main():
    """Run both tests"""
    test_humint_analysis()
    test_darkweb_analysis()

if __name__ == "__main__":
    main()