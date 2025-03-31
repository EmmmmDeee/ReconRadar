import logging
import trafilatura
from bs4 import BeautifulSoup
import re
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_website_text_content(url: str, timeout: int = 5) -> str:
    """
    This function takes a URL and returns the main text content of the website.
    The text content is extracted using trafilatura for better readability.
    
    Args:
        url (str): The URL to extract content from
        timeout (int): Request timeout in seconds
        
    Returns:
        str: The main text content of the website, or an error message
    """
    try:
        # Send a request to the website with a user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the URL content
        downloaded = trafilatura.fetch_url(url, headers=headers)
        if not downloaded:
            # Fallback to requests if trafilatura fails
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                downloaded = response.text
            else:
                return f"Error: Unable to fetch content (Status code: {response.status_code})"
        
        # Extract the main content
        text = trafilatura.extract(downloaded, include_comments=False, 
                                   include_tables=True, include_images=False, 
                                   include_links=False, no_fallback=False)
        
        # If trafilatura extraction fails, try BeautifulSoup as fallback
        if not text:
            logging.warning(f"Trafilatura extraction failed for {url}, trying BeautifulSoup fallback")
            soup = BeautifulSoup(downloaded, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            # Get all paragraphs
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
            else:
                # If no paragraphs, get the text from the body
                text = soup.get_text(separator="\n\n", strip=True)
        
        # Return the extracted text or an error message
        if text:
            return text
        else:
            return "Error: No content could be extracted from the provided URL"
    
    except requests.exceptions.Timeout:
        return "Error: Request timed out while fetching the website content"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error in get_website_text_content: {e}")
        return f"Error: An unexpected error occurred while extracting content: {str(e)}"

def extract_metadata_from_url(url: str) -> dict:
    """
    Extract basic metadata from a URL without visiting the page.
    
    Args:
        url (str): The URL to analyze
        
    Returns:
        dict: Dictionary containing metadata extracted from the URL
    """
    metadata = {
        "url": url,
        "domain": None,
        "path": None,
        "filename": None,
        "query_params": {}
    }
    
    try:
        # Parse the URL
        parsed_url = urlparse(url)
        
        # Extract domain
        metadata["domain"] = parsed_url.netloc
        
        # Extract path
        metadata["path"] = parsed_url.path
        
        # Extract filename if present
        if '/' in parsed_url.path:
            path_parts = parsed_url.path.split('/')
            if path_parts[-1] and '.' in path_parts[-1]:
                metadata["filename"] = path_parts[-1]
        
        # Extract query parameters
        if parsed_url.query:
            metadata["query_params"] = parse_qs(parsed_url.query)
        
        return metadata
    
    except Exception as e:
        logging.error(f"Error extracting metadata from URL: {e}")
        return metadata

def search_and_extract(query: str, max_results: int = 5) -> list:
    """
    Search for a query using a search engine and extract content from top results.
    This is a placeholder function that would require a search API integration.
    
    Args:
        query (str): The search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of dictionaries containing search results and extracted content
    """
    # Note: This is a placeholder that would require a search API integration
    logging.warning("search_and_extract is a placeholder function - actual search API integration required")
    return [{"url": "https://example.com", "title": "Example", "content": "This is a placeholder result."}]

def extract_geolocation_data(html_content: str, url: str = None) -> dict:
    """
    Extract geolocation data from HTML content using various methods including:
    - meta tags (especially OpenGraph)
    - schema.org structured data
    - inline geolocation references
    - embedded maps
    
    Args:
        html_content (str): HTML content to analyze
        url (str, optional): URL the content was fetched from (for context)
        
    Returns:
        dict: Dictionary containing extracted geolocation data
    """
    geolocation_data = {
        "latitude": None,
        "longitude": None,
        "address": None,
        "city": None,
        "region": None,
        "country": None,
        "place_name": None,
        "location_mentions": [],
        "confidence": 0.0,
        "source": None
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Extract from meta tags (especially OpenGraph)
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            if tag.get('property') == 'og:latitude' or tag.get('name') == 'geo.position' or tag.get('itemprop') == 'latitude':
                geolocation_data["latitude"] = tag.get('content')
                geolocation_data["confidence"] = 0.9
                geolocation_data["source"] = "meta_tags"
            
            if tag.get('property') == 'og:longitude' or tag.get('itemprop') == 'longitude':
                geolocation_data["longitude"] = tag.get('content')
                geolocation_data["confidence"] = 0.9
                geolocation_data["source"] = "meta_tags"
                
            # Combined position
            if tag.get('name') == 'geo.position':
                pos = tag.get('content', '').split(';')
                if len(pos) == 2:
                    geolocation_data["latitude"] = pos[0].strip()
                    geolocation_data["longitude"] = pos[1].strip()
                    geolocation_data["confidence"] = 0.9
                    geolocation_data["source"] = "meta_tags"
            
            # Location name/place
            if tag.get('property') == 'og:locality' or tag.get('name') == 'geo.placename':
                geolocation_data["place_name"] = tag.get('content')
                geolocation_data["city"] = tag.get('content')  # Assume locality is city
                geolocation_data["confidence"] = max(geolocation_data["confidence"], 0.7)
                geolocation_data["source"] = "meta_tags"
            
            # Region info
            if tag.get('property') == 'og:region' or tag.get('name') == 'geo.region':
                geolocation_data["region"] = tag.get('content')
                geolocation_data["confidence"] = max(geolocation_data["confidence"], 0.7)
                geolocation_data["source"] = "meta_tags"
                
            # Country info
            if tag.get('property') == 'og:country-name':
                geolocation_data["country"] = tag.get('content')
                geolocation_data["confidence"] = max(geolocation_data["confidence"], 0.7)
                geolocation_data["source"] = "meta_tags"
        
        # Method 2: Extract from Schema.org structured data
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                json_data = json.loads(script.string)
                # Handle both direct objects and arrays of objects
                json_objects = [json_data] if isinstance(json_data, dict) else json_data if isinstance(json_data, list) else []
                
                for obj in json_objects:
                    # Look for Place, LocalBusiness, Event, etc. that might have location data
                    if '@type' in obj and obj['@type'] in ['Place', 'LocalBusiness', 'Restaurant', 'Hotel', 'Event', 'Organization']:
                        # Extract address
                        if 'address' in obj:
                            address_obj = obj['address']
                            if isinstance(address_obj, dict):
                                address_parts = []
                                
                                # Build address from PostalAddress fields
                                if 'streetAddress' in address_obj:
                                    address_parts.append(address_obj['streetAddress'])
                                    
                                if 'addressLocality' in address_obj:
                                    address_parts.append(address_obj['addressLocality'])
                                    geolocation_data["city"] = address_obj['addressLocality']
                                    
                                if 'addressRegion' in address_obj:
                                    address_parts.append(address_obj['addressRegion'])
                                    geolocation_data["region"] = address_obj['addressRegion']
                                    
                                if 'postalCode' in address_obj:
                                    address_parts.append(address_obj['postalCode'])
                                    
                                if 'addressCountry' in address_obj:
                                    country = address_obj['addressCountry']
                                    if isinstance(country, dict) and 'name' in country:
                                        address_parts.append(country['name'])
                                        geolocation_data["country"] = country['name']
                                    else:
                                        address_parts.append(country)
                                        geolocation_data["country"] = country
                                
                                geolocation_data["address"] = ", ".join([p for p in address_parts if p])
                                geolocation_data["confidence"] = 0.95
                                geolocation_data["source"] = "schema_org"
                            elif isinstance(address_obj, str):
                                geolocation_data["address"] = address_obj
                                geolocation_data["confidence"] = 0.8
                                geolocation_data["source"] = "schema_org"
                        
                        # Extract geo coordinates
                        if 'geo' in obj and isinstance(obj['geo'], dict):
                            geo = obj['geo']
                            if 'latitude' in geo and 'longitude' in geo:
                                geolocation_data["latitude"] = geo['latitude']
                                geolocation_data["longitude"] = geo['longitude']
                                geolocation_data["confidence"] = 0.95
                                geolocation_data["source"] = "schema_org"
                                
                        # Extract name of place
                        if 'name' in obj and not geolocation_data["place_name"]:
                            geolocation_data["place_name"] = obj['name']
            except (json.JSONDecodeError, TypeError) as e:
                logging.warning(f"Error parsing Schema.org JSON: {e}")
        
        # Method 3: Look for embedded maps (Google Maps, etc.)
        iframe_tags = soup.find_all('iframe')
        for iframe in iframe_tags:
            src = iframe.get('src', '')
            
            # Google Maps
            if 'google.com/maps' in src or 'maps.google.com' in src:
                # Try to extract coordinates from the URL
                coords_match = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', src)
                if coords_match:
                    geolocation_data["latitude"] = coords_match.group(1)
                    geolocation_data["longitude"] = coords_match.group(2)
                    geolocation_data["confidence"] = 0.9
                    geolocation_data["source"] = "embedded_map"
                    
                # If no coordinates, try to extract the place name
                elif 'q=' in src:
                    place_part = src.split('q=')[1].split('&')[0]
                    if place_part and place_part != 'q=':
                        place = unquote(place_part)
                        geolocation_data["place_name"] = place
                        geolocation_data["location_mentions"].append(place)
                        geolocation_data["confidence"] = 0.7
                        geolocation_data["source"] = "embedded_map"
        
        # Method 4: Look for geolocation patterns in text
        text_content = soup.get_text()
        
        # Find location patterns
        # Look for country mentions
        countries = [
            "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", 
            "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", 
            "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia", "Botswana", 
            "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon", 
            "Canada", "Cape Verde", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", 
            "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", 
            "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", 
            "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", 
            "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", 
            "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", 
            "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", 
            "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea", "Kosovo", "Kuwait", "Kyrgyzstan", 
            "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", 
            "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", 
            "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", 
            "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", 
            "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", 
            "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Panama", "Papua New Guinea", 
            "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", 
            "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent", "Samoa", "San Marino", 
            "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", 
            "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", 
            "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", 
            "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", 
            "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", 
            "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", 
            "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
            "USA", "UK", "UAE"
        ]
        
        location_mentions = []
        for country in countries:
            if re.search(r'\\b' + re.escape(country) + r'\\b', text_content, re.IGNORECASE):
                location_mentions.append(country)
                if not geolocation_data["country"]:
                    geolocation_data["country"] = country
                    geolocation_data["confidence"] = max(geolocation_data["confidence"], 0.6)
                    geolocation_data["source"] = "text_analysis"
        
        # Look for GPS coordinate patterns
        gps_patterns = [
            # Decimal degrees (e.g., 40.7128, -74.0060)
            r'(-?\d{1,3}\.\d{4,})[,\s]+(-?\d{1,3}\.\d{4,})',
            # Degrees, minutes, seconds (e.g., 40° 42′ 46″ N, 74° 00′ 21″ W)
            r'(\d{1,3})°\s*(\d{1,2})′\s*(\d{1,2})″\s*([NS])[,\s]+(\d{1,3})°\s*(\d{1,2})′\s*(\d{1,2})″\s*([EW])'
        ]
        
        for pattern in gps_patterns:
            matches = re.findall(pattern, text_content)
            if matches:
                # Use the first match (most likely to be prominent)
                match = matches[0]
                if len(match) == 2:  # Decimal degrees
                    geolocation_data["latitude"] = match[0]
                    geolocation_data["longitude"] = match[1]
                    geolocation_data["confidence"] = 0.8
                    geolocation_data["source"] = "text_analysis"
                elif len(match) == 8:  # DMS
                    # Convert DMS to decimal degrees
                    lat_deg, lat_min, lat_sec, lat_dir = match[0:4]
                    lon_deg, lon_min, lon_sec, lon_dir = match[4:8]
                    
                    lat_decimal = float(lat_deg) + float(lat_min)/60 + float(lat_sec)/3600
                    if lat_dir.upper() == 'S':
                        lat_decimal = -lat_decimal
                        
                    lon_decimal = float(lon_deg) + float(lon_min)/60 + float(lon_sec)/3600
                    if lon_dir.upper() == 'W':
                        lon_decimal = -lon_decimal
                        
                    geolocation_data["latitude"] = str(lat_decimal)
                    geolocation_data["longitude"] = str(lon_decimal)
                    geolocation_data["confidence"] = 0.85
                    geolocation_data["source"] = "text_analysis"
        
        # Add all discovered location mentions
        geolocation_data["location_mentions"] = list(set(location_mentions + geolocation_data["location_mentions"]))
        
        return geolocation_data
    
    except Exception as e:
        logging.error(f"Error extracting geolocation data: {e}")
        return geolocation_data

def extract_dark_web_information(html_content: str, text_content: str = None) -> dict:
    """
    Extract dark web and cybersecurity-related information from HTML content.
    Detects onion services, cryptocurrency addresses, secure messaging IDs, and more.
    
    Args:
        html_content (str): HTML content to analyze
        text_content (str, optional): Preprocessed text content if available
        
    Returns:
        dict: Dictionary containing extracted dark web information
    """
    dark_web_info = {
        "onion_services": [],
        "cryptocurrency_addresses": {
            "bitcoin": [],
            "ethereum": [],
            "monero": [],
            "zcash": []
        },
        "secure_messaging": {
            "pgp_keys": [],
            "keybase": [],
            "session": [],
            "signal": [],
            "protonmail": []
        },
        "security_indicators": [],
        "confidence": 0.0,
        "source": None
    }
    
    try:
        # If text content isn't provided, extract it from the HTML
        if not text_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            text_content = soup.get_text(separator=" ", strip=True)
        
        # 1. Find onion services
        onion_patterns = [
            r'https?://([a-z2-7]{16,56}\.onion)(?:/\S*)?',  # .onion URLs
            r'([a-z2-7]{16,56}\.onion)(?:/\S*)?',  # .onion domains without http
            r'(?:tor hidden service|onion service|hidden service)(?:\s*(?:at|:)\s*)(?:https?://)?([a-z2-7]{16,56}\.onion)(?:/\S*)?'  # Descriptive context
        ]
        
        for pattern in onion_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                onion_service = match.group(1)
                if onion_service not in dark_web_info["onion_services"]:
                    dark_web_info["onion_services"].append(onion_service)
                    dark_web_info["confidence"] = max(dark_web_info["confidence"], 0.9)
                    dark_web_info["source"] = "text_analysis"
        
        # 2. Find cryptocurrency addresses
        crypto_patterns = {
            "bitcoin": [
                r'\b(bc1[a-zA-HJ-NP-Z0-9]{25,39})\b',  # Bech32 format
                r'\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b'  # Legacy format
            ],
            "ethereum": [
                r'\b(0x[a-fA-F0-9]{40})\b'  # Ethereum address format
            ],
            "monero": [
                r'\b([48][a-zA-Z0-9]{94,95})\b'  # Monero address format
            ],
            "zcash": [
                r'\b(z[a-zA-Z0-9]{77,78})\b',  # Shielded Zcash format
                r'\b(t[a-zA-Z0-9]{34,35})\b'  # Transparent Zcash format
            ]
        }
        
        for crypto_type, patterns in crypto_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_content)
                for match in matches:
                    address = match.group(1)
                    if address not in dark_web_info["cryptocurrency_addresses"][crypto_type]:
                        dark_web_info["cryptocurrency_addresses"][crypto_type].append(address)
                        dark_web_info["confidence"] = max(dark_web_info["confidence"], 0.85)
                        dark_web_info["source"] = "text_analysis"
        
        # 3. Find secure messaging identifiers
        secure_msg_patterns = {
            "pgp_keys": [
                r'(?:PGP|GPG)(?:\s+key)?(?:\s*ID|\s*fingerprint)?(?:\s*[:=])?\s*([A-F0-9]{8,40})',
                r'-----BEGIN PGP PUBLIC KEY BLOCK-----'
            ],
            "keybase": [
                r'(?:keybase|kb)(?:\.io)?(?:\s*[:=])?\s*([a-zA-Z0-9_]{2,25})',
                r'https?://keybase\.io/([a-zA-Z0-9_]{2,25})'
            ],
            "session": [
                r'(?:session|session id)(?:\s*[:=])?\s*([a-f0-9]{64,66})',
                r'05[a-f0-9]{61,63}'  # Session ID format
            ],
            "signal": [
                r'(?:signal|signal number|\+)(?:\s*[:=])?\s*(\+\d{10,15})'
            ],
            "protonmail": [
                r'(?:protonmail|proton mail|proton email)(?:\s*[:=])?\s*([a-zA-Z0-9._%+-]+@protonmail\.(?:com|ch))',
                r'\b([a-zA-Z0-9._%+-]+@protonmail\.(?:com|ch))\b'
            ]
        }
        
        for msg_type, patterns in secure_msg_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if len(match.groups()) >= 1:
                        identifier = match.group(1)
                        if identifier not in dark_web_info["secure_messaging"][msg_type]:
                            dark_web_info["secure_messaging"][msg_type].append(identifier)
                            dark_web_info["confidence"] = max(dark_web_info["confidence"], 0.8)
                            dark_web_info["source"] = "text_analysis"
                    elif msg_type == "pgp_keys" and "BEGIN PGP PUBLIC KEY BLOCK" in match.group(0):
                        # Special case for inline PGP blocks
                        dark_web_info["secure_messaging"]["pgp_keys"].append("PGP_BLOCK_FOUND")
                        dark_web_info["confidence"] = max(dark_web_info["confidence"], 0.95)
                        dark_web_info["source"] = "text_analysis"
        
        # 4. Find security indicators and specialized terms
        security_indicators = [
            r'(?:strong encryption|end-to-end encryption|e2ee)',
            r'(?:self-destruct messages|burn after reading)',
            r'(?:threat model|opsec|operational security)',
            r'(?:secure drop|anonymous upload|anonymous file sharing)',
            r'(?:tails os|whonix|qubes os|hardened os)',
            r'(?:mixnet|mix network|garlic routing|onion routing)',
            r'(?:zero knowledge|zero-knowledge|zk)',
            r'(?:secure chat|secure messaging|encrypted chat)',
            r'(?:anonymous remailer|i2p|freenet|zeronet)',
            r'(?:warrant canary|transparency report)',
            r'(?:dark web|dark net|darknet|hidden services)'
        ]
        
        for pattern in security_indicators:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                indicator = match.group(0).lower()
                if indicator not in dark_web_info["security_indicators"]:
                    dark_web_info["security_indicators"].append(indicator)
                    dark_web_info["confidence"] = max(dark_web_info["confidence"], 0.7)
                    dark_web_info["source"] = "text_analysis"
        
        # Clean up empty lists for cleaner output
        for crypto_type in list(dark_web_info["cryptocurrency_addresses"].keys()):
            if not dark_web_info["cryptocurrency_addresses"][crypto_type]:
                dark_web_info["cryptocurrency_addresses"].pop(crypto_type)
                
        for msg_type in list(dark_web_info["secure_messaging"].keys()):
            if not dark_web_info["secure_messaging"][msg_type]:
                dark_web_info["secure_messaging"].pop(msg_type)
                
        if not dark_web_info["security_indicators"]:
            dark_web_info.pop("security_indicators")
            
        return dark_web_info
            
    except Exception as e:
        logging.error(f"Error extracting dark web information: {e}")
        return dark_web_info

def extract_contact_information(html_content: str) -> dict:
    """
    Extract contact information from HTML content.
    
    Args:
        html_content (str): HTML content to analyze
        
    Returns:
        dict: Dictionary containing extracted contact information
    """
    contact_info = {
        "email_addresses": [],
        "phone_numbers": [],
        "social_profiles": [],
        "physical_addresses": []
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        # Extract email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        contact_info["email_addresses"] = list(set(re.findall(email_pattern, text_content)))
        
        # Extract phone numbers (various formats)
        phone_patterns = [
            r'\+\d{1,3}[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{1,4}',  # International format
            r'\(\d{3}\)[-\s]?\d{3}[-\s]?\d{4}',  # US format with parentheses
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # US format without parentheses
        ]
        
        phone_numbers = []
        for pattern in phone_patterns:
            phone_numbers.extend(re.findall(pattern, text_content))
        contact_info["phone_numbers"] = list(set(phone_numbers))
        
        # Extract physical addresses (simplified approach)
        address_markers = [
            'address', 'location', 'street', 'avenue', 'boulevard', 'road', 'lane',
            'drive', 'place', 'court', 'plaza', 'square', 'suite', 'apt', 'apartment',
            'floor', 'building', 'block', 'sector', 'zip', 'postal', 'code'
        ]
        
        paragraphs = soup.find_all(['p', 'div', 'address', 'span'])
        for p in paragraphs:
            p_text = p.get_text(strip=True)
            if any(marker in p_text.lower() for marker in address_markers):
                # Filter out very short text or generic menu items
                if len(p_text) > 15 and p_text not in contact_info["physical_addresses"]:
                    contact_info["physical_addresses"].append(p_text)
        
        return contact_info
    except Exception as e:
        logging.error(f"Error extracting contact information: {e}")
        return contact_info

# Example usage
if __name__ == "__main__":
    test_url = "https://en.wikipedia.org/wiki/Open-source_intelligence"
    content = get_website_text_content(test_url)
    print(f"Extracted {len(content)} characters of content")
    print(content[:500] + "...")  # Print first 500 characters
    
    # Test geolocation extraction with a sample HTML
    sample_html = """
    <html>
    <head>
        <meta property="og:latitude" content="40.7128" />
        <meta property="og:longitude" content="-74.0060" />
        <meta property="og:locality" content="New York City" />
        <meta property="og:country-name" content="USA" />
    </head>
    <body>
        <h1>Sample location page</h1>
        <p>Our office is located in New York City, USA.</p>
        <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d193595.15830869428!2d-74.11976397304605!3d40.69766374874431!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89c24fa5d33f083b%3A0xc80b8f06e177fe62!2sNew%20York%2C%20NY%2C%20USA!5e0!3m2!1sen!2sin!4v1606815826814!5m2!1sen!2sin" width="600" height="450" frameborder="0" style="border:0;" allowfullscreen="" aria-hidden="false" tabindex="0"></iframe>
    </body>
    </html>
    """
    
    geo_data = extract_geolocation_data(sample_html)
    print("\nExtracted geolocation data:")
    print(json.dumps(geo_data, indent=2))
    
    # Test contact information extraction
    sample_contact_html = """
    <html>
    <body>
        <h1>Contact Us</h1>
        <p>Email: contact@example.com, support@example.com</p>
        <p>Phone: +1 (555) 123-4567, 555-987-6543</p>
        <div class="address">
            123 Main Street, Suite 456<br>
            New York, NY 10001<br>
            United States
        </div>
    </body>
    </html>
    """
    
    contact_data = extract_contact_information(sample_contact_html)
    print("\nExtracted contact information:")
    print(json.dumps(contact_data, indent=2))