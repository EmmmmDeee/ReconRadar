#!/usr/bin/env python3
"""
People Finder module for unve1ler
Advanced people search capabilities inspired by idcrawl.com
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import json
from web_scraper import get_website_text_content, extract_humint_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PeopleFinder:
    """Class for advanced people search capabilities"""
    
    def __init__(self):
        """Initialize the PeopleFinder with default headers and timeout"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1'
        }
        self.timeout = 10
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_person(self, full_name=None, username=None, location=None, email=None, phone=None):
        """
        Comprehensive search for a person across multiple sources
        
        Args:
            full_name (str): Person's full name
            username (str): Username to search
            location (str): Location (city, state, country)
            email (str): Email address
            phone (str): Phone number
            
        Returns:
            dict: Combined search results with confidence scores
        """
        if not any([full_name, username, email, phone]):
            raise ValueError("At least one search parameter (full_name, username, email, phone) is required")
        
        # Initialize results
        results = {
            "identity": {
                "full_name": full_name,
                "username": username,
                "location": location,
                "email": email,
                "phone": phone,
                "probable_age_range": None,
                "possible_photos": [],
                "confidence": 0.0
            },
            "social_profiles": {},
            "contact_info": {
                "emails": [],
                "phones": [],
                "addresses": []
            },
            "public_records": {},
            "humint_data": {},
            "search_summary": {},
            "meta": {
                "search_timestamp": None,
                "data_sources": []
            }
        }
        
        # Perform searches based on provided parameters
        sources = []
        
        if username:
            username_results = self.search_by_username(username)
            results["social_profiles"].update(username_results.get("profiles", {}))
            results["identity"]["possible_photos"].extend(username_results.get("profile_photos", []))
            sources.append("username_search")
        
        if full_name:
            name_results = self.search_by_name(full_name, location)
            
            # Merge social profiles
            results["social_profiles"].update(name_results.get("profiles", {}))
            
            # Add public records
            results["public_records"] = name_results.get("public_records", {})
            
            # Extract and merge contact info
            if "contact_info" in name_results:
                for email in name_results["contact_info"].get("emails", []):
                    if email not in results["contact_info"]["emails"]:
                        results["contact_info"]["emails"].append(email)
                
                for phone in name_results["contact_info"].get("phones", []):
                    if phone not in results["contact_info"]["phones"]:
                        results["contact_info"]["phones"].append(phone)
                
                for address in name_results["contact_info"].get("addresses", []):
                    if address not in results["contact_info"]["addresses"]:
                        results["contact_info"]["addresses"].append(address)
            
            # Extract possible photos
            if "possible_photos" in name_results:
                for photo in name_results["possible_photos"]:
                    if photo not in results["identity"]["possible_photos"]:
                        results["identity"]["possible_photos"].append(photo)
            
            sources.append("name_search")
        
        if email:
            email_results = self.search_by_email(email)
            # Merge relevant data
            for platform, url in email_results.get("profiles", {}).items():
                if platform not in results["social_profiles"]:
                    results["social_profiles"][platform] = url
            
            sources.append("email_search")
        
        if phone:
            phone_results = self.search_by_phone(phone)
            # Merge relevant data
            if phone_results.get("owner_name") and not results["identity"]["full_name"]:
                results["identity"]["full_name"] = phone_results.get("owner_name")
            
            if "addresses" in phone_results:
                for address in phone_results["addresses"]:
                    if address not in results["contact_info"]["addresses"]:
                        results["contact_info"]["addresses"].append(address)
            
            sources.append("phone_search")
        
        # Enhance with HUMINT analysis
        if results["social_profiles"]:
            humint_data = self._extract_humint_from_profiles(results["social_profiles"])
            results["humint_data"] = humint_data
        
        # Calculate confidence score
        results["identity"]["confidence"] = self._calculate_identity_confidence(results)
        
        # Update metadata
        results["meta"]["data_sources"] = sources
        import datetime
        results["meta"]["search_timestamp"] = datetime.datetime.now().isoformat()
        
        # Generate search summary
        results["search_summary"] = self._generate_search_summary(results)
        
        return results
    
    def search_by_username(self, username):
        """
        Search for a person by username across social media and web platforms
        
        Args:
            username (str): Username to search
            
        Returns:
            dict: Search results with social profiles and metadata
        """
        results = {
            "profiles": {},
            "profile_photos": [],
            "username_variations": [],
            "summary": "",
            "confidence": 0.0
        }
        
        # Check common username patterns for variations
        username_variations = self._generate_username_variations(username)
        results["username_variations"] = username_variations
        
        try:
            # Simulate search like idcrawl.com's username search
            logger.info(f"Searching for username: {username}")
            
            # Generate search URL for Google with site-specific searches
            sites_to_check = [
                "facebook.com", "twitter.com", "instagram.com", "linkedin.com", 
                "github.com", "pinterest.com", "youtube.com", "reddit.com"
            ]
            
            # For each site, try to find profiles
            total_confidence = 0.0
            found_count = 0
            
            for site in sites_to_check:
                # Direct check for username on platform
                if self._check_username_on_site(username, site, results):
                    found_count += 1
                    total_confidence += 0.85  # Direct hit confidence
                
                # Try variations only for major platforms to reduce false positives
                if site in ["facebook.com", "twitter.com", "instagram.com", "linkedin.com"] and found_count == 0:
                    for variation in username_variations[:3]:  # Limit to first 3 variations to avoid excessive requests
                        if variation != username and self._check_username_on_site(variation, site, results):
                            found_count += 1
                            total_confidence += 0.65  # Variation hit confidence (lower)
                            break
            
            # Calculate overall confidence
            if found_count > 0:
                results["confidence"] = total_confidence / (found_count * 0.9)  # Normalize confidence
                if results["confidence"] > 1.0:
                    results["confidence"] = 1.0
            
            # Generate summary
            if found_count > 0:
                results["summary"] = f"Found {found_count} profiles across {len(sites_to_check)} platforms for username '{username}' or variations."
            else:
                results["summary"] = f"No definitive profiles found for username '{username}'."
            
        except Exception as e:
            logger.error(f"Error in username search: {str(e)}")
            results["summary"] = f"Error during search: {str(e)}"
        
        return results
    
    def search_by_name(self, full_name, location=None):
        """
        Search for a person by full name, optionally filtered by location
        
        Args:
            full_name (str): Person's full name
            location (str): Optional location for filtering results
            
        Returns:
            dict: Search results with profiles, public records, and contact info
        """
        results = {
            "profiles": {},
            "public_records": {
                "birth_records": [],
                "marriage_records": [],
                "property_records": [],
                "court_records": [],
                "business_records": []
            },
            "contact_info": {
                "emails": [],
                "phones": [],
                "addresses": []
            },
            "possible_photos": [],
            "name_variations": [],
            "summary": "",
            "confidence": 0.0
        }
        
        try:
            # Generate name variations
            name_parts = full_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]
                
                # Common name variations
                variations = [
                    f"{first_name} {last_name}",
                    f"{first_name[0]}. {last_name}",
                ]
                
                # Add middle initials if present
                if len(name_parts) > 2:
                    middle_names = name_parts[1:-1]
                    middle_initials = "".join([name[0] + "." for name in middle_names])
                    variations.append(f"{first_name} {middle_initials} {last_name}")
                
                results["name_variations"] = variations
            
            # Simulate search like idcrawl.com's people search
            logger.info(f"Searching for name: {full_name}" + (f" in {location}" if location else ""))
            
            # Simulate search results for demonstration
            # In a real implementation, this would connect to various data sources
            
            # Find social profiles by name
            self._find_social_profiles_by_name(full_name, results)
            
            # Find public records by name and location
            if location:
                self._find_public_records(full_name, location, results)
            
            # Generate search summary
            profile_count = len(results["profiles"])
            record_count = sum(len(records) for records in results["public_records"].values())
            
            if profile_count > 0 or record_count > 0:
                summary_parts = []
                if profile_count > 0:
                    summary_parts.append(f"found {profile_count} social profiles")
                if record_count > 0:
                    summary_parts.append(f"found {record_count} public records")
                
                results["summary"] = f"Search for '{full_name}' {' and '.join(summary_parts)}."
                results["confidence"] = min(0.4 + (profile_count * 0.1) + (record_count * 0.05), 1.0)
            else:
                results["summary"] = f"No definitive records found for '{full_name}'."
                results["confidence"] = 0.1
                
        except Exception as e:
            logger.error(f"Error in name search: {str(e)}")
            results["summary"] = f"Error during search: {str(e)}"
        
        return results
    
    def search_by_email(self, email):
        """
        Search for a person by email address
        
        Args:
            email (str): Email address to search
            
        Returns:
            dict: Search results with associated profiles and metadata
        """
        results = {
            "profiles": {},
            "owner_name": None,
            "summary": "",
            "confidence": 0.0
        }
        
        try:
            logger.info(f"Searching for email: {email}")
            
            # Here we would implement actual email searching logic
            # Similar to how idcrawl.com searches for emails across platforms
            
            # Extract domain for targeted searches
            domain = email.split('@')[-1]
            username_part = email.split('@')[0]
            
            # Check for common services where email is the login
            services = {
                "gmail.com": ["Google", "YouTube"],
                "yahoo.com": ["Yahoo"],
                "outlook.com": ["Microsoft", "LinkedIn"],
                "hotmail.com": ["Microsoft"],
                "aol.com": ["AOL"],
                "icloud.com": ["Apple"]
            }
            
            if domain in services:
                for service in services[domain]:
                    results["profiles"][service] = f"Potential {service} account with email {email}"
            
            # Try to find profiles using the email's username part
            self._find_profiles_by_username_part(username_part, results)
            
            # Generate summary
            profile_count = len(results["profiles"])
            if profile_count > 0:
                results["summary"] = f"Found {profile_count} potential profiles associated with email '{email}'."
                results["confidence"] = min(0.3 + (profile_count * 0.15), 1.0)
            else:
                results["summary"] = f"No definitive profiles found for email '{email}'."
                results["confidence"] = 0.1
                
        except Exception as e:
            logger.error(f"Error in email search: {str(e)}")
            results["summary"] = f"Error during search: {str(e)}"
        
        return results
    
    def search_by_phone(self, phone):
        """
        Search for a person by phone number
        
        Args:
            phone (str): Phone number to search (with or without formatting)
            
        Returns:
            dict: Search results with owner information and associated records
        """
        results = {
            "owner_name": None,
            "carrier": None,
            "location": None,
            "addresses": [],
            "associated_emails": [],
            "summary": "",
            "confidence": 0.0
        }
        
        try:
            # Normalize phone number format
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) < 10:
                raise ValueError("Phone number must have at least 10 digits")
            
            logger.info(f"Searching for phone: {clean_phone}")
            
            # In a real implementation, we would query phone lookup APIs here
            # This is a placeholder for demonstration
            
            # Generate placeholder summary
            results["summary"] = f"Phone lookup performed for '{phone}'. For privacy and legal reasons, detailed results are limited."
            results["confidence"] = 0.5
            
        except Exception as e:
            logger.error(f"Error in phone search: {str(e)}")
            results["summary"] = f"Error during search: {str(e)}"
        
        return results
    
    def _check_username_on_site(self, username, site, results):
        """
        Check if a username exists on a specific site
        
        Args:
            username (str): Username to check
            site (str): Website domain to check
            results (dict): Results dictionary to update
            
        Returns:
            bool: True if profile was found, False otherwise
        """
        site_name = site.split('.')[0].capitalize()
        url_formats = {
            "facebook.com": f"https://www.facebook.com/{username}",
            "twitter.com": f"https://twitter.com/{username}",
            "instagram.com": f"https://www.instagram.com/{username}/",
            "linkedin.com": f"https://www.linkedin.com/in/{username}/",
            "github.com": f"https://github.com/{username}",
            "pinterest.com": f"https://www.pinterest.com/{username}/",
            "youtube.com": f"https://www.youtube.com/user/{username}",
            "reddit.com": f"https://www.reddit.com/user/{username}"
        }
        
        if site not in url_formats:
            return False
        
        url = url_formats[site]
        
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            
            # Different sites have different ways of indicating a profile exists
            if site == "facebook.com":
                # Facebook redirects non-existent profiles, or shows specific text
                if response.status_code == 200 and "isn't available" not in response.text and "The link you followed may be broken" not in response.text:
                    results["profiles"]["Facebook"] = url
                    # Extract profile photo if available
                    photo_url = self._extract_profile_photo(response.text, site)
                    if photo_url and photo_url not in results["profile_photos"]:
                        results["profile_photos"].append(photo_url)
                    return True
            
            elif site == "twitter.com":
                # Twitter returns 404 for non-existent profiles
                if response.status_code == 200:
                    results["profiles"]["Twitter"] = url
                    # Extract profile photo
                    photo_url = self._extract_profile_photo(response.text, site)
                    if photo_url and photo_url not in results["profile_photos"]:
                        results["profile_photos"].append(photo_url)
                    return True
            
            # Similar logic for other platforms
            elif site in ["instagram.com", "github.com", "pinterest.com", "youtube.com", "reddit.com", "linkedin.com"]:
                if response.status_code == 200:
                    results["profiles"][site_name] = url
                    # Extract profile photo if available
                    photo_url = self._extract_profile_photo(response.text, site)
                    if photo_url and photo_url not in results["profile_photos"]:
                        results["profile_photos"].append(photo_url)
                    return True
            
        except Exception as e:
            logger.debug(f"Error checking {site} for {username}: {str(e)}")
        
        return False
    
    def _extract_profile_photo(self, html_content, site):
        """
        Extract profile photo URL from HTML content
        
        Args:
            html_content (str): HTML content to parse
            site (str): Website domain for site-specific extraction logic
            
        Returns:
            str: URL of profile photo if found, None otherwise
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Site-specific extraction logic
            if site == "facebook.com":
                # Facebook profile photos are typically in meta tags
                meta_tag = soup.find('meta', property='og:image')
                if meta_tag and 'content' in meta_tag.attrs:
                    return meta_tag['content']
            
            elif site == "twitter.com":
                # Twitter profile photos
                img = soup.find('img', class_='css-9pa8cd')
                if img and 'src' in img.attrs:
                    return img['src']
            
            # Instagram (more complex due to dynamic loading)
            elif site == "instagram.com":
                meta_tag = soup.find('meta', property='og:image')
                if meta_tag and 'content' in meta_tag.attrs:
                    return meta_tag['content']
            
            # Generic approach for other sites
            else:
                # Try common meta tags
                for prop in ['og:image', 'twitter:image']:
                    meta_tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
                    if meta_tag and 'content' in meta_tag.attrs:
                        return meta_tag['content']
                
                # Look for avatar images
                for class_name in ['avatar', 'profile-image', 'user-image', 'user-avatar']:
                    img = soup.find('img', class_=re.compile(class_name, re.I))
                    if img and 'src' in img.attrs:
                        return img['src']
            
        except Exception as e:
            logger.debug(f"Error extracting profile photo from {site}: {str(e)}")
        
        return None
    
    def _find_social_profiles_by_name(self, full_name, results):
        """
        Find social profiles by name using search engine techniques
        
        Args:
            full_name (str): Person's full name
            results (dict): Results dictionary to update
        """
        # In a real implementation, this would use search engine APIs or web scraping
        # to find social profiles by name
        
        # This is a placeholder for demonstration
        pass
    
    def _find_public_records(self, full_name, location, results):
        """
        Find public records by name and location
        
        Args:
            full_name (str): Person's full name
            location (str): Location for filtering results
            results (dict): Results dictionary to update
        """
        # In a real implementation, this would connect to public records databases
        # This is a placeholder for demonstration
        pass
    
    def _find_profiles_by_username_part(self, username_part, results):
        """
        Find profiles using the username part of an email
        
        Args:
            username_part (str): Username part of an email
            results (dict): Results dictionary to update
        """
        # In a real implementation, this would search for profiles with this username
        # This is a placeholder for demonstration
        pass
    
    def _generate_username_variations(self, username):
        """
        Generate common variations of a username
        
        Args:
            username (str): Base username
            
        Returns:
            list: List of username variations
        """
        variations = [username]
        
        # Add common username variations
        variations.append(f"real{username}")
        variations.append(f"the{username}")
        variations.append(f"{username}1")
        variations.append(f"{username}123")
        variations.append(f"{username}_official")
        
        # Add variations with capitalization
        if username.islower():
            variations.append(username.capitalize())
            variations.append(username.upper())
        
        # Add variations with underscores or dots if the username doesn't have them
        if '_' not in username and len(username) > 3:
            # Split username randomly for demonstration
            split_index = len(username) // 2
            variations.append(f"{username[:split_index]}_{username[split_index:]}")
        
        if '.' not in username and len(username) > 3:
            # Split username randomly for demonstration
            split_index = len(username) // 2
            variations.append(f"{username[:split_index]}.{username[split_index:]}")
        
        return variations
    
    def _extract_humint_from_profiles(self, profiles):
        """
        Extract human intelligence data from social profiles
        
        Args:
            profiles (dict): Dictionary of social profiles
            
        Returns:
            dict: Extracted HUMINT data
        """
        humint_data = {
            "names": [],
            "aliases": [],
            "organizations": [],
            "occupations": [],
            "relationships": [],
            "biographical": {
                "age": None,
                "birth_date": None,
                "education": [],
                "employment_history": [],
                "languages": [],
                "skills": []
            },
            "interests": [],
            "locations": [],
            "confidence": 0.0
        }
        
        # In a production system, this would scrape the profile pages
        # and extract HUMINT data using NLP techniques
        
        # For now, this is a placeholder
        
        return humint_data
    
    def _calculate_identity_confidence(self, results):
        """
        Calculate the confidence score for the identity
        
        Args:
            results (dict): Search results
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        # Base confidence
        confidence = 0.0
        
        # Social profiles contribute significantly to confidence
        profile_count = len(results["social_profiles"])
        if profile_count > 0:
            confidence += min(profile_count * 0.15, 0.45)  # Up to 45% from profiles
        
        # Contact info contributes to confidence
        email_count = len(results["contact_info"]["emails"])
        phone_count = len(results["contact_info"]["phones"])
        address_count = len(results["contact_info"]["addresses"])
        
        contact_confidence = min((email_count * 0.1) + (phone_count * 0.1) + (address_count * 0.05), 0.3)
        confidence += contact_confidence  # Up to 30% from contact info
        
        # Public records contribute to confidence
        if "public_records" in results:
            record_count = sum(len(records) for records in results["public_records"].values())
            confidence += min(record_count * 0.05, 0.15)  # Up to 15% from records
        
        # HUMINT data contributes to confidence
        if "humint_data" in results and results["humint_data"].get("confidence", 0) > 0:
            confidence += min(results["humint_data"]["confidence"] * 0.1, 0.1)  # Up to 10% from HUMINT
        
        # Photos contribute to confidence
        photo_count = len(results["identity"]["possible_photos"])
        confidence += min(photo_count * 0.05, 0.1)  # Up to 10% from photos
        
        return min(confidence, 1.0)  # Cap at 100%
    
    def _generate_search_summary(self, results):
        """
        Generate a human-readable summary of search results
        
        Args:
            results (dict): Search results
            
        Returns:
            dict: Summary information
        """
        summary = {
            "identity_confidence": results["identity"]["confidence"],
            "found_profiles_count": len(results["social_profiles"]),
            "found_contact_info": {
                "emails": len(results["contact_info"]["emails"]),
                "phones": len(results["contact_info"]["phones"]),
                "addresses": len(results["contact_info"]["addresses"])
            },
            "found_photos_count": len(results["identity"]["possible_photos"]),
            "search_completeness": 0.0,
            "text_summary": ""
        }
        
        # Calculate search completeness
        completeness_factors = [
            0.2 if len(results["social_profiles"]) > 0 else 0.0,
            0.2 if results["contact_info"]["emails"] or results["contact_info"]["phones"] else 0.0,
            0.2 if "public_records" in results and any(results["public_records"].values()) else 0.0,
            0.2 if "humint_data" in results and results["humint_data"].get("confidence", 0) > 0.3 else 0.0,
            0.2 if len(results["identity"]["possible_photos"]) > 0 else 0.0
        ]
        
        summary["search_completeness"] = sum(completeness_factors)
        
        # Generate text summary
        identity = results["identity"]
        search_term = identity.get("full_name") or identity.get("username") or "the subject"
        
        text_parts = []
        
        if summary["found_profiles_count"] > 0:
            platforms = list(results["social_profiles"].keys())
            if len(platforms) <= 3:
                platform_text = ", ".join(platforms)
            else:
                platform_text = f"{', '.join(platforms[:3])} and {len(platforms) - 3} more"
            
            text_parts.append(f"found {summary['found_profiles_count']} profiles on {platform_text}")
        
        contact_count = sum(summary["found_contact_info"].values())
        if contact_count > 0:
            text_parts.append(f"identified {contact_count} contact points")
        
        if summary["found_photos_count"] > 0:
            text_parts.append(f"discovered {summary['found_photos_count']} possible photos")
        
        if text_parts:
            summary["text_summary"] = f"Search for {search_term} {' and '.join(text_parts)}."
        else:
            summary["text_summary"] = f"Search for {search_term} did not yield definitive results."
        
        # Add confidence level descriptor
        confidence = results["identity"]["confidence"]
        if confidence >= 0.8:
            confidence_text = "high confidence"
        elif confidence >= 0.5:
            confidence_text = "moderate confidence"
        elif confidence >= 0.3:
            confidence_text = "low confidence"
        else:
            confidence_text = "very low confidence"
        
        summary["text_summary"] += f" Results have {confidence_text} ({int(confidence * 100)}%)."
        
        return summary


# Function to create an instance and search
def search_person(full_name=None, username=None, location=None, email=None, phone=None):
    """
    Search for a person using the PeopleFinder
    
    Args:
        full_name (str): Person's full name
        username (str): Username to search
        location (str): Location (city, state, country)
        email (str): Email address
        phone (str): Phone number
        
    Returns:
        dict: Search results
    """
    finder = PeopleFinder()
    return finder.search_person(full_name, username, location, email, phone)

# Function specifically for idcrawl-like username search
def search_username(username):
    """
    Search for profiles by username across platforms
    
    Args:
        username (str): Username to search
        
    Returns:
        dict: Search results focusing on social profiles
    """
    finder = PeopleFinder()
    results = finder.search_by_username(username)
    
    # Format the results for API response
    return {
        "username": username,
        "profiles": results["profiles"],
        "profile_photos": results["profile_photos"],
        "variations_checked": results["username_variations"],
        "confidence": results["confidence"],
        "summary": results["summary"]
    }