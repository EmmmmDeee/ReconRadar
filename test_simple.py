#!/usr/bin/env python3
"""
Simple test script for unve1ler's HUMINT and Dark Web analysis capabilities
"""

import requests
import json

API_URL = "http://0.0.0.0:5000"

def test_humint_simple():
    """Test HUMINT data extraction with a simple example"""
    print("\n=== Testing Simple HUMINT Analysis ===\n")
    
    # Simple text with HUMINT data
    sample_text = """
My name is James Wilson and I work as a Cybersecurity Researcher.
I was born on February 15, 1985.
My email is james.wilson@example.com.
    """
    
    # Send POST request to the HUMINT analysis endpoint
    response = requests.post(
        f"{API_URL}/analyze/humint",
        json={"text": sample_text, "threshold": 0.5}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("HUMINT Analysis Results:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_darkweb_simple():
    """Test Dark Web detection with a simple example"""
    print("\n=== Testing Simple Dark Web Analysis ===\n")
    
    # Simple text with dark web indicators
    sample_text = """
Bitcoin: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Onion Service: https://expyuzz4wqqyqhjn.onion
    """
    
    # Send POST request to the Dark Web analysis endpoint
    response = requests.post(
        f"{API_URL}/analyze/darkweb",
        json={"text": sample_text, "threshold": 0.5}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("Dark Web Analysis Results:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_humint_simple()
    test_darkweb_simple()