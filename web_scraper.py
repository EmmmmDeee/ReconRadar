import logging
import trafilatura
from bs4 import BeautifulSoup
import re
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
import string

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
        # Send a request to the website
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the URL content (trafilatura doesn't accept headers parameter)
        downloaded = trafilatura.fetch_url(url)
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

def extract_dark_web_information(html_content = None, text_content = None) -> dict:
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

def extract_humint_data(text_content = None, html_content = None) -> dict:
    """
    Extract human intelligence (HUMINT) data from content, focusing on personal information.
    This function identifies names, occupations, biographical details, relationships, and other
    personal attributes that are valuable for human intelligence gathering.
    
    Args:
        text_content (str): Text content to analyze for HUMINT data
        html_content (str, optional): HTML content for additional extraction from structured data
        
    Returns:
        dict: Dictionary containing comprehensive HUMINT data
    """
    # Initialize the results structure
    humint_data = {
        "names": [],              # Full names detected
        "aliases": [],            # Nicknames, handles, aliases
        "organizations": [],      # Organizations and affiliations
        "occupations": [],        # Job titles and professional roles
        "biographical": {         # Biographical information
            "age": None,
            "birth_date": None,
            "education": [],
            "employment_history": [],
            "languages": [],
            "skills": []
        },
        "relationships": [],      # Personal and professional relationships
        "interests": [],          # Hobbies, interests, activities
        "personal_attributes": {  # Identifying personal characteristics
            "gender": None,
            "nationality": None,
            "appearance": [],
            "personality_traits": []
        },
        "timestamps": {           # Digital activity timestamps
            "last_seen": None,
            "registration_date": None,
            "activity_pattern": None
        },
        "confidence": 0.0,        # Overall confidence score
        "source": None            # Source of extracted data
    }
    
    try:
        # Process text content for HUMINT data
        if not text_content:
            return humint_data
            
        # 1. Extract names using refined patterns
        # Look for formal name patterns with titles
        name_patterns = [
            # Formal name patterns with titles
            (r'(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Sir|Madam|Lady|Lord)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', 0.9),
            
            # Full name patterns (First Last)
            (r'\b(?!(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|AM|PM|UTC|GMT|EST|PST|CST|MST|EDT|PDT|CDT|MDT)(?:\s|\.|,|$))'
             r'([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{0,3})?\s+[A-Z][a-z]{2,20})\b', 0.8),
            
            # Name patterns with middle initial
            (r'\b([A-Z][a-z]{2,20}\s+[A-Z]\.\s+[A-Z][a-z]{2,20})\b', 0.85),
            
            # Authored by or written by patterns
            (r'(?:authored|written|prepared|compiled|edited|reported)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', 0.85),
            
            # Contact person patterns
            (r'(?:contact|reach out to|speak with|talk to|email|call)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', 0.75),
            
            # Name followed by title or role
            (r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}),?\s+(?:the|our|senior|chief|head|lead|principal|director of|manager of|professor of)', 0.8),
            
            # "I am" or "My name is" patterns for self-identification
            (r'(?:I am|my name is|I\'m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', 0.9)
        ]
        
        # Extract names
        for pattern, confidence in name_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # Extract from group
                name = match.strip()
                # Validate the name (basic check for reasonable length and format)
                if len(name.split()) >= 2 and all(part[0].isupper() for part in name.split()):
                    if name not in humint_data["names"]:
                        humint_data["names"].append(name)
                        if confidence > humint_data["confidence"]:
                            humint_data["confidence"] = confidence
                            humint_data["source"] = "name_pattern"
        
        # 2. Extract aliases and nicknames
        alias_patterns = [
            # Known by or goes by patterns
            (r'(?:known as|goes by|aka|a\.k\.a\.|alias|called|nicknamed|nickname)\s+["\']?([A-Za-z][A-Za-z0-9_\.\-]{2,30})["\']?', 0.9),
            
            # Handle patterns for social media
            (r'(?:handle|username|user name|screen name|tag)\s+(?:is|:)\s+["\']?(@?)([A-Za-z][A-Za-z0-9_\.\-]{2,30})["\']?', 0.85),
            
            # Online identity patterns
            (r'(?:online|on the internet|on social media|on twitter|on instagram|on facebook|on linkedin)\s+(?:as|using)\s+["\']?(@?)([A-Za-z][A-Za-z0-9_\.\-]{2,30})["\']?', 0.8)
        ]
        
        for pattern, confidence in alias_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) > 1:
                        alias = (match[0] + match[1]).strip()
                    else:
                        alias = match[0].strip()
                else:
                    alias = match.strip()
                
                # Check for minimum length and avoid common words
                if len(alias) >= 3 and alias.lower() not in ["the", "and", "but", "for", "not", "with"]:
                    if alias not in humint_data["aliases"]:
                        humint_data["aliases"].append(alias)
                        if confidence > humint_data["confidence"]:
                            humint_data["confidence"] = confidence
                            humint_data["source"] = "alias_pattern"
        
        # 3. Extract organizations and affiliations
        org_patterns = [
            # Works for / employed by patterns
            (r'(?:works for|employed by|employed at|works at|affiliated with|member of|associated with)\s+([A-Z][A-Za-z0-9\'\s&\.]{2,50})\b', 0.85),
            
            # Organizational roles
            (r'(?:CEO|CFO|CTO|COO|President|Director|Manager|Head|Lead|Chief|Officer)\s+(?:of|at)\s+([A-Z][A-Za-z0-9\'\s&\.]{2,50})\b', 0.9),
            
            # Former affiliation patterns
            (r'(?:former|ex-|previously|once)\s+(?:\w+\s+){0,2}(?:at|with|for)\s+([A-Z][A-Za-z0-9\'\s&\.]{2,50})\b', 0.75)
        ]
        
        for pattern, confidence in org_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    org = match[0].strip()
                else:
                    org = match.strip()
                
                # Validate organization name (basic checks)
                if len(org) >= 3 and org[0].isupper():
                    if org not in humint_data["organizations"]:
                        humint_data["organizations"].append(org)
                        if confidence > humint_data["confidence"]:
                            humint_data["confidence"] = confidence
                            humint_data["source"] = "organization_pattern"
        
        # 4. Extract occupations and job titles
        occupation_patterns = [
            # Standard job title patterns
            (r'\b((?:Senior|Junior|Chief|Lead|Head|Principal|Executive|Assistant|Associate|Director of|Manager of|VP of|Vice President of)?\s*'
             r'(?:Software Engineer|Data Scientist|Security Researcher|Analyst|Developer|Architect|Designer|Consultant|'
             r'Investigator|Researcher|Professor|Doctor|Lawyer|Accountant|Marketer|Journalist|Writer|Editor|'
             r'Specialist|Coordinator|Administrator|Supervisor|Officer|Agent|Expert|Technician|Engineer|Scientist))\b', 0.85),
            
            # Role/position patterns
            (r'(?:role|position|job|title|occupation|profession)\s+(?:is|as|of|:)\s+([A-Za-z][A-Za-z\s\-]{2,40}?)\b', 0.8),
            
            # Self-identification of profession
            (r'(?:I am|I\'m)\s+(?:a|an)\s+([A-Za-z][A-Za-z\s\-]{2,40}?)\b', 0.7)
        ]
        
        for pattern, confidence in occupation_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    occupation = match[0].strip()
                else:
                    occupation = match.strip()
                
                # Validate occupation (basic check for reasonable length)
                if len(occupation) >= 3 and occupation.lower() not in ["the", "and", "but", "for", "not", "with"]:
                    if occupation not in humint_data["occupations"]:
                        humint_data["occupations"].append(occupation)
                        if confidence > humint_data["confidence"]:
                            humint_data["confidence"] = confidence
                            humint_data["source"] = "occupation_pattern"
        
        # 5. Extract biographical information
        # Age patterns
        age_patterns = [
            r'\b(?:aged?|is|am|turned)\s+(\d{1,2})\s+(?:years\s+old|year[s]?\s+old|years|year[s]?)\b',
            r'\b(\d{1,2})[- ]years?[- ]old\b'
        ]
        
        for pattern in age_patterns:
            matches = re.findall(pattern, text_content)
            if matches:
                try:
                    age = int(matches[0])
                    if 1 <= age <= 120:  # Basic age validation
                        humint_data["biographical"]["age"] = age
                        if humint_data["confidence"] < 0.85:
                            humint_data["confidence"] = 0.85
                            humint_data["source"] = "age_pattern"
                        break
                except (ValueError, IndexError):
                    pass
        
        # Birth date patterns
        birth_date_patterns = [
            # Various date formats (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.)
            r'\b(?:born|birth(?:day|date)?|dob)\s+(?:on|:)?\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'\b(?:born|birth(?:day|date)?|dob)\s+(?:on|:)?\s+(\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',
            # Word format dates
            r'\b(?:born|birth(?:day|date)?|dob)\s+(?:on|:)?\s+([A-Z][a-z]{2,8}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',
            r'\b(?:born|birth(?:day|date)?|dob)\s+(?:on|:)?\s+(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?[A-Z][a-z]{2,8},?\s+\d{4})'
        ]
        
        for pattern in birth_date_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                birth_date = matches[0]
                humint_data["biographical"]["birth_date"] = birth_date
                if humint_data["confidence"] < 0.9:
                    humint_data["confidence"] = 0.9
                    humint_data["source"] = "birth_date_pattern"
                break
        
        # Education patterns
        education_patterns = [
            # Degrees, schools, and education history
            (r'(?:graduated|studied|degree|education|alumni|alumnus|alumna|student)\s+(?:from|at|in|with)\s+([A-Z][A-Za-z\'\s&\.]{2,60})\b', 0.85),
            (r'\b(?:B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|M\.?B\.?A\.?|J\.?D\.?|M\.?D\.?)\s+(?:in|from|degree)?\s+([A-Za-z\'\s&\.]{2,60})\b', 0.9),
            (r'\b(?:Bachelor[\'s]?|Master[\'s]?|Doctorate|Doctoral|Undergraduate|Graduate|Postgraduate)\s+(?:degree|program|education|studies)?\s+(?:in|from|at)?\s+([A-Za-z\'\s&\.]{2,60})\b', 0.85)
        ]
        
        for pattern, confidence in education_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    education = match[0].strip()
                else:
                    education = match.strip()
                
                # Validate education information
                if len(education) >= 3:
                    if education not in humint_data["biographical"]["education"]:
                        humint_data["biographical"]["education"].append(education)
                        if confidence > humint_data["confidence"]:
                            humint_data["confidence"] = confidence
                            humint_data["source"] = "education_pattern"
        
        # 6. Extract relationships
        relationship_patterns = [
            # Family relationships
            (r'(?:father|mother|husband|wife|spouse|partner|brother|sister|sibling|son|daughter|child|parent|grandfather|grandmother|grandparent|grandchild|uncle|aunt|cousin|nephew|niece|in-law)\s+(?:is|was|of|to)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', 0.9),
            
            # Professional relationships
            (r'(?:colleague|coworker|co-worker|associate|boss|supervisor|manager|assistant|secretary|mentor|mentee|advisor|advisee|team member)\s+(?:is|was|of|to|at)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', 0.85),
            
            # Social relationships
            (r'(?:friend|roommate|classmate|neighbor|neighbor|acquaintance|contact|partner|significant other)\s+(?:is|was|named)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', 0.8)
        ]
        
        for pattern, confidence in relationship_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    relationship = match[0].strip()
                else:
                    relationship = match.strip()
                
                # Validate relationship information (basic check)
                if len(relationship) >= 3:
                    if relationship not in humint_data["relationships"]:
                        humint_data["relationships"].append(relationship)
                        if confidence > humint_data["confidence"]:
                            humint_data["confidence"] = confidence
                            humint_data["source"] = "relationship_pattern"
        
        # 7. Process HTML content if available for structured HUMINT data
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for social media profile metadata in HTML
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                # Profile information from meta tags
                if tag.get('property') == 'profile:first_name' or tag.get('name') == 'profile:first_name':
                    first_name = tag.get('content')
                    if first_name and len(first_name) >= 2:
                        if 'last_name' in humint_data:
                            full_name = f"{first_name} {humint_data['last_name']}"
                            if full_name not in humint_data["names"]:
                                humint_data["names"].append(full_name)
                                humint_data["confidence"] = max(humint_data["confidence"], 0.9)
                                humint_data["source"] = "meta_tags"
                
                if tag.get('property') == 'profile:last_name' or tag.get('name') == 'profile:last_name':
                    last_name = tag.get('content')
                    if last_name and len(last_name) >= 2:
                        humint_data['last_name'] = last_name
                        if 'first_name' in humint_data:
                            full_name = f"{humint_data['first_name']} {last_name}"
                            if full_name not in humint_data["names"]:
                                humint_data["names"].append(full_name)
                                humint_data["confidence"] = max(humint_data["confidence"], 0.9)
                                humint_data["source"] = "meta_tags"
                
                # Timestamp information
                if tag.get('property') == 'profile:last_active' or tag.get('name') == 'last-modified':
                    humint_data["timestamps"]["last_seen"] = tag.get('content')
                    humint_data["confidence"] = max(humint_data["confidence"], 0.8)
                    humint_data["source"] = "meta_tags"
                
                # Gender information
                if tag.get('property') == 'profile:gender' or tag.get('name') == 'gender':
                    humint_data["personal_attributes"]["gender"] = tag.get('content')
                    humint_data["confidence"] = max(humint_data["confidence"], 0.85)
                    humint_data["source"] = "meta_tags"
            
            # Extract from Schema.org structured data
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    json_data = json.loads(script.string)
                    # Handle both direct objects and arrays of objects
                    json_objects = [json_data] if isinstance(json_data, dict) else json_data if isinstance(json_data, list) else []
                    
                    for obj in json_objects:
                        # Look for Person schema
                        if '@type' in obj and obj['@type'] == 'Person':
                            # Extract name
                            if 'name' in obj and obj['name'] not in humint_data["names"]:
                                humint_data["names"].append(obj['name'])
                                humint_data["confidence"] = max(humint_data["confidence"], 0.95)
                                humint_data["source"] = "schema_org"
                            
                            # Extract job title
                            if 'jobTitle' in obj and obj['jobTitle'] not in humint_data["occupations"]:
                                humint_data["occupations"].append(obj['jobTitle'])
                                humint_data["confidence"] = max(humint_data["confidence"], 0.95)
                                humint_data["source"] = "schema_org"
                            
                            # Extract organization
                            if 'worksFor' in obj:
                                org = obj['worksFor']
                                if isinstance(org, dict) and 'name' in org:
                                    if org['name'] not in humint_data["organizations"]:
                                        humint_data["organizations"].append(org['name'])
                                        humint_data["confidence"] = max(humint_data["confidence"], 0.95)
                                        humint_data["source"] = "schema_org"
                                elif isinstance(org, str) and org not in humint_data["organizations"]:
                                    humint_data["organizations"].append(org)
                                    humint_data["confidence"] = max(humint_data["confidence"], 0.9)
                                    humint_data["source"] = "schema_org"
                            
                            # Extract nationality
                            if 'nationality' in obj:
                                nationality = obj['nationality']
                                if isinstance(nationality, dict) and 'name' in nationality:
                                    humint_data["personal_attributes"]["nationality"] = nationality['name']
                                elif isinstance(nationality, str):
                                    humint_data["personal_attributes"]["nationality"] = nationality
                                humint_data["confidence"] = max(humint_data["confidence"], 0.95)
                                humint_data["source"] = "schema_org"
                                
                            # Extract birth date
                            if 'birthDate' in obj and not humint_data["biographical"]["birth_date"]:
                                humint_data["biographical"]["birth_date"] = obj['birthDate']
                                humint_data["confidence"] = max(humint_data["confidence"], 0.95)
                                humint_data["source"] = "schema_org"
                                
                                # Calculate age if birth date is available
                                try:
                                    birth_year = int(obj['birthDate'].split('-')[0])
                                    current_year = datetime.now().year
                                    if 1900 <= birth_year <= current_year:
                                        humint_data["biographical"]["age"] = current_year - birth_year
                                except (ValueError, IndexError, AttributeError):
                                    pass
                
                except (json.JSONDecodeError, TypeError) as e:
                    logging.warning(f"Error parsing Schema.org JSON for HUMINT data: {e}")
        
        # Return the filled HUMINT data structure
        return humint_data
    
    except Exception as e:
        logging.error(f"Error in HUMINT data extraction: {e}")
        return humint_data

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