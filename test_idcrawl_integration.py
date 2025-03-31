"""
Integration test for the enhanced IDCrawl username checking functionality
"""

import asyncio
import aiohttp
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("idcrawl_integration_test")

# Import our modules (these should be in the correct location)
try:
    from models import load_config, IdcrawlUserResult
    from osint_modules import run_username_checks_async
    CONFIG = load_config()
    logger.info("Successfully imported config and models")
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure models.py, osint_modules.py, and config.json are in the correct location")
    sys.exit(1)

async def test_username_checks(
    usernames: List[str], 
    output_file: Optional[str] = None,
    verbose: bool = False
):
    """Run username checks and display results"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    print(f"Starting username checks for: {', '.join(usernames)}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Call the function from osint_modules.py
            results = await run_username_checks_async(usernames, session)
            
            # Process and display results
            if results:
                print("\nRESULTS SUMMARY:")
                print("-" * 60)
                
                for username, user_result in results.items():
                    if not isinstance(user_result, IdcrawlUserResult):
                        print(f"Error: Invalid result type for {username}")
                        continue
                    
                    # Extract results data - handle both Pydantic v1 and v2
                    try:
                        # For Pydantic v2
                        sites_data = user_result.root
                    except AttributeError:
                        # For Pydantic v1
                        sites_data = user_result.__root__
                        
                    # Find sites with profiles and errors
                    found_sites = []
                    error_sites = []
                    for site, data in sites_data.items():
                        if hasattr(data, 'status'):
                            if data.status == "found":
                                found_sites.append(site)
                            elif data.status == "error":
                                error_sites.append(site)
                        elif isinstance(data, dict) and 'status' in data:
                            if data['status'] == "found":
                                found_sites.append(site)
                            elif data['status'] == "error":
                                error_sites.append(site)
                    
                    print(f"\nUsername: {username}")
                    print(f"Total sites checked: {len(sites_data)}")
                    print(f"Profiles found: {len(found_sites)}")
                    print(f"Sites with errors: {len(error_sites)}")
                    
                    if found_sites:
                        print("\nProfiles found on:")
                        for site in found_sites:
                            site_data = sites_data[site]
                            print(f"- {site}: {site_data.url_found}")
                    
                    if verbose and error_sites:
                        print("\nSites with errors:")
                        for site in error_sites:
                            site_data = sites_data[site]
                            print(f"- {site}: {site_data.error_message}")
                
                # Save results to file if specified
                if output_file:
                    output_path = Path(output_file)
                    # Convert Pydantic models to dictionaries
                    serializable_results = {}
                    for username, user_result in results.items():
                        if isinstance(user_result, IdcrawlUserResult):
                            user_dict = {}
                            try:
                                # For Pydantic v2
                                for site, data in user_result.root.items():
                                    user_dict[site] = data.model_dump() if hasattr(data, 'model_dump') else data.dict() if hasattr(data, 'dict') else data
                            except AttributeError:
                                # For Pydantic v1
                                for site, data in user_result.__root__.items():
                                    user_dict[site] = data.model_dump() if hasattr(data, 'model_dump') else data.dict() if hasattr(data, 'dict') else data
                            serializable_results[username] = user_dict
                    
                    with open(output_path, 'w') as f:
                        json.dump(serializable_results, f, indent=2)
                    print(f"\nResults saved to {output_path}")
            else:
                print("No results returned.")
        
        except Exception as e:
            logger.error(f"Error during username checks: {e}", exc_info=True)
            print(f"Error: {str(e)}")

def main():
    """Parse arguments and run the test"""
    parser = argparse.ArgumentParser(description="Test IDCrawl username checking integration")
    parser.add_argument("usernames", nargs="+", help="Usernames to check")
    parser.add_argument("-o", "--output", help="Output file for results (JSON)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    asyncio.run(test_username_checks(args.usernames, args.output, args.verbose))

if __name__ == "__main__":
    main()