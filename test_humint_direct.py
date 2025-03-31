#!/usr/bin/env python3
"""
Test script for directly testing the HUMINT data extraction function
"""

from web_scraper import extract_humint_data

def main():
    """Test HUMINT data extraction directly"""
    print("\n=== Direct Testing of HUMINT Data Extraction ===\n")
    
    # Simple test text
    test_text = """
    My name is James Wilson and I work as a Cybersecurity Researcher.
    I was born on February 15, 1985 in Chicago, Illinois.
    You can reach me at james.wilson@example.com or call my office at +1-555-123-4567.
    I graduated from MIT with a degree in Computer Science in 2007.
    """
    
    try:
        # Process the test text
        results = extract_humint_data(test_text)
        
        # Display results
        print("Extraction Results:")
        print(f"Names: {results.get('names', [])}")
        print(f"Occupations: {results.get('occupations', [])}")
        
        # Biographical info
        bio = results.get('biographical', {})
        print("\nBiographical Data:")
        if bio.get('birth_date'):
            print(f"Birth Date: {bio['birth_date']}")
        if bio.get('education'):
            print(f"Education: {bio['education']}")
        
        # Contact info - might be in a different structure
        print("\nConfidence Score:", results.get('confidence', 0))
        
    except Exception as e:
        print(f"Error during extraction: {str(e)}")

if __name__ == "__main__":
    main()