#!/usr/bin/env python3
"""
Test script for directly testing the Dark Web analysis function
"""

from web_scraper import extract_dark_web_information

def main():
    """Test Dark Web analysis directly"""
    print("\n=== Direct Testing of Dark Web Analysis ===\n")
    
    # Simple test text
    test_text = """
    Here are some potential dark web indicators:
    Bitcoin address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
    Ethereum address: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
    Onion service: expyuzz4wqqyqhjn.onion
    PGP key fingerprint: 2BD5 1FB3 FCF4 6964 7FCF 8738 9C5D 93C3 DA27 D992
    Telegram: @darkwebuser123
    Signal: +12025551234
    """
    
    try:
        # Process the test text
        results = extract_dark_web_information(None, test_text)
        
        # Display results
        print("Dark Web Analysis Results:")
        print(f"Cryptocurrency Addresses: {results.get('cryptocurrency_addresses', [])}")
        print(f"Onion Services: {results.get('onion_services', [])}")
        print(f"Secure Messaging: {results.get('secure_messaging', [])}")
        
        print("\nConfidence Score:", results.get('confidence', 0))
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()