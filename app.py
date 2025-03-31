import os
import requests
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
import logging
import json
import html
from datetime import datetime
import time
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "unve1ler_default_secret")

from unve1ler import check_social_media, VERSION
from web_scraper import (
    get_website_text_content, 
    extract_metadata_from_url, 
    extract_geolocation_data, 
    extract_contact_information,
    extract_dark_web_information,
    extract_humint_data
)
from assets import process_attached_file, extract_social_profiles_from_text, extract_usernames_from_text, extract_image_urls_from_text
from people_finder import search_username, search_person
# Import IdCrawl scraper for advanced search capabilities
from idcrawl_scraper import search_username_on_idcrawl, search_person_on_idcrawl, AUTOMATION_AVAILABLE, AUTOMATION_SCRIPT_AVAILABLE

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

@app.route('/')
def index():
    """Render the main search page"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """
    Perform social media username search and optional reverse image search
    
    Expected JSON request body:
    {
        "username": "target_username",
        "image_url": "optional_image_url"
    }
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    image_url = data.get('image_url', None)
    
    if not username:
        return jsonify({
            'error': 'Username is required',
            'status': 'error'
        }), 400
    
    try:
        # Use the check_social_media function to get results
        # The new function returns 5 values: profiles, stats, reverse_image_urls, platform_metadata, image_metadata
        results, stats, reverse_image_urls, platform_metadata, image_metadata = check_social_media(username, image_url)
        
        # Log information about the search
        logging.info(f"Search completed for '{username}'. Found {stats['profiles_found']} profiles across {stats['platforms_checked']} platforms.")
        
        return jsonify({
            'results': results,
            'stats': stats,
            'reverse_image_urls': reverse_image_urls,
            'platform_metadata': platform_metadata,
            'image_metadata': image_metadata,
            'status': 'success'
        })
    except Exception as e:
        logging.error(f"Error during search: {str(e)}")
        return jsonify({
            'error': f"An error occurred during the search: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/extract', methods=['POST'])
def extract_web_content():
    """
    Extract readable text content from a URL
    
    Expected JSON request body:
    {
        "url": "website_url"
    }
    """
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({
            'error': 'URL is required',
            'status': 'error'
        }), 400
    
    try:
        # Track processing time
        start_time = time.time()
        
        # Get a proper User-Agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # First fetch the raw HTML for advanced analysis 
        response = None
        try:
            response = requests.get(url, headers=headers, timeout=10)
            html_content = response.text if response.status_code == 200 else None
        except Exception as e:
            logging.warning(f"Failed to fetch HTML content for advanced analysis: {str(e)}")
            html_content = None
        
        # Extract content from URL
        extracted_text = get_website_text_content(url)
        url_metadata = extract_metadata_from_url(url)
        
        # Additional analysis if we have the HTML content
        geolocation_data = {}
        contact_data = {}
        dark_web_data = {}
        
        if html_content:
            try:
                # Extract geolocation data
                geolocation_data = extract_geolocation_data(html_content, url)
                
                # Extract contact information
                contact_data = extract_contact_information(html_content)
                
                # Extract dark web information
                dark_web_data = extract_dark_web_information(html_content=html_content, text_content=extracted_text)
            except Exception as analysis_error:
                logging.warning(f"Error during advanced content analysis: {str(analysis_error)}")
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        # Sanitize output for safety
        if isinstance(extracted_text, str):
            # Escape HTML entities
            extracted_text = html.escape(extracted_text)
        
        # Prepare result
        result = {
            'url': url,
            'content': extracted_text,
            'content_length': len(extracted_text) if isinstance(extracted_text, str) else 0,
            'processing_time_seconds': processing_time,
            'metadata': url_metadata,
            'geolocation': geolocation_data,
            'contact_information': contact_data,
            'dark_web_information': dark_web_data,
            'timestamp': datetime.now(),
            'status': 'success'
        }
        
        # Check if content contains error message
        if isinstance(extracted_text, str) and extracted_text.startswith('Error:'):
            result['status'] = 'partial'
            result['error'] = extracted_text
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error extracting content: {str(e)}")
        return jsonify({
            'error': f"Failed to extract content: {str(e)}",
            'url': url,
            'status': 'error'
        }), 500

@app.route('/analyze/text', methods=['POST'])
def analyze_text():
    """
    Analyze text content to extract social media profiles, usernames, and image URLs
    
    Expected JSON request body:
    {
        "text": "text content to analyze"
    }
    """
    data = request.get_json()
    text_content = data.get('text', '').strip()
    
    if not text_content:
        return jsonify({
            'error': 'Text content is required',
            'status': 'error'
        }), 400
    
    try:
        # Extract information from text
        social_profiles = extract_social_profiles_from_text(text_content)
        usernames = extract_usernames_from_text(text_content)
        image_urls = extract_image_urls_from_text(text_content)
        
        # Return the analysis results
        return jsonify({
            'social_profiles': social_profiles,
            'potential_usernames': usernames,
            'potential_image_urls': image_urls,
            'text_length': len(text_content),
            'timestamp': datetime.now(),
            'status': 'success'
        })
    
    except Exception as e:
        logging.error(f"Error analyzing text: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Failed to analyze text: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/analyze/file', methods=['POST'])
def analyze_file():
    """
    Analyze file content to extract social media profiles, usernames, and image URLs
    
    Expected POST form data:
    - file: The file to analyze
    """
    if 'file' not in request.files:
        return jsonify({
            'error': 'No file provided',
            'status': 'error'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'error': 'No selected file',
            'status': 'error'
        }), 400
    
    try:
        # Save the file temporarily
        file_path = os.path.join('/tmp', 'unve1ler_' + str(int(time.time())) + '.txt')
        file.save(file_path)
        
        # Process the file
        result = process_attached_file(file_path)
        
        # Clean up the temporary file
        try:
            os.remove(file_path)
        except:
            logging.warning(f"Failed to remove temporary file: {file_path}")
        
        # Check for errors in the result
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'status': 'error'
            }), 500
        
        # Return the analysis results
        return jsonify({
            'filename': file.filename,
            'analysis': result,
            'status': 'success'
        })
    
    except Exception as e:
        logging.error(f"Error analyzing file: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Failed to analyze file: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/analyze/humint', methods=['POST'])
def analyze_humint():
    """
    Analyze text or URL content for human intelligence (HUMINT) data 
    such as names, occupations, biographical details, and relationships.
    
    Expected JSON request body:
    {
        "text": "text content to analyze (optional)",
        "url": "website URL to analyze (optional)",
        "threshold": 0.6  # Optional confidence threshold (0.0-1.0)
    }
    
    At least one of 'text' or 'url' must be provided.
    """
    data = request.get_json()
    text_content = data.get('text', '').strip()
    url = data.get('url', '').strip()
    threshold = float(data.get('threshold', 0.6))
    
    if not text_content and not url:
        return jsonify({
            'error': 'Either text content or URL is required',
            'status': 'error'
        }), 400
    
    try:
        results = {'humint_data': {}}
        
        # If a URL is provided, fetch its content
        html_content = None
        if url:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    html_content = response.text
                    # If no text was explicitly provided, extract it from the HTML
                    if not text_content:
                        text_content = get_website_text_content(url)
            except Exception as url_error:
                logging.warning(f"Error fetching URL content: {str(url_error)}")
                results['url_error'] = str(url_error)
        
        # Analyze for HUMINT data
        if text_content:
            humint_data = extract_humint_data(text_content=text_content, html_content=html_content)
            
            # Apply confidence threshold
            if humint_data.get('confidence', 0) >= threshold:
                results['humint_data'] = humint_data
                
                # Generate summary of key findings
                summary = []
                
                # Names found
                if humint_data.get('names'):
                    summary.append({
                        'type': 'names',
                        'description': 'Personal names identified',
                        'count': len(humint_data['names']),
                        'items': humint_data['names'][:5],  # Limit to top 5
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                # Aliases found
                if humint_data.get('aliases'):
                    summary.append({
                        'type': 'aliases',
                        'description': 'Aliases or handles identified',
                        'count': len(humint_data['aliases']),
                        'items': humint_data['aliases'][:5],  # Limit to top 5
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                # Organizations
                if humint_data.get('organizations'):
                    summary.append({
                        'type': 'organizations',
                        'description': 'Organizational affiliations',
                        'count': len(humint_data['organizations']),
                        'items': humint_data['organizations'][:5],  # Limit to top 5
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                # Occupations
                if humint_data.get('occupations'):
                    summary.append({
                        'type': 'occupations',
                        'description': 'Professional roles or occupations',
                        'count': len(humint_data['occupations']),
                        'items': humint_data['occupations'][:5],  # Limit to top 5
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                # Relationships
                if humint_data.get('relationships'):
                    summary.append({
                        'type': 'relationships',
                        'description': 'Personal or professional relationships',
                        'count': len(humint_data['relationships']),
                        'items': humint_data['relationships'][:5],  # Limit to top 5
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                # Biographical highlights
                bio_highlights = {}
                if humint_data.get('biographical', {}).get('age'):
                    bio_highlights['age'] = humint_data['biographical']['age']
                
                if humint_data.get('biographical', {}).get('birth_date'):
                    bio_highlights['birth_date'] = humint_data['biographical']['birth_date']
                
                if humint_data.get('biographical', {}).get('education'):
                    bio_highlights['education'] = humint_data['biographical']['education'][:3]
                
                if bio_highlights:
                    summary.append({
                        'type': 'biographical',
                        'description': 'Biographical information',
                        'items': bio_highlights,
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                # Personal attributes
                personal_attributes = {}
                if humint_data.get('personal_attributes', {}).get('gender'):
                    personal_attributes['gender'] = humint_data['personal_attributes']['gender']
                
                if humint_data.get('personal_attributes', {}).get('nationality'):
                    personal_attributes['nationality'] = humint_data['personal_attributes']['nationality']
                
                if personal_attributes:
                    summary.append({
                        'type': 'personal_attributes',
                        'description': 'Personal characteristics',
                        'items': personal_attributes,
                        'confidence': humint_data.get('confidence', 0)
                    })
                
                results['summary'] = summary
                
                # Calculate completeness score based on how many HUMINT categories have data
                filled_categories = 0
                total_categories = 7  # names, aliases, orgs, occupations, bio, relationships, personal attributes
                
                if humint_data.get('names'):
                    filled_categories += 1
                if humint_data.get('aliases'):
                    filled_categories += 1
                if humint_data.get('organizations'):
                    filled_categories += 1
                if humint_data.get('occupations'):
                    filled_categories += 1
                if any(humint_data.get('biographical', {}).values()):
                    filled_categories += 1
                if humint_data.get('relationships'):
                    filled_categories += 1
                if any(humint_data.get('personal_attributes', {}).values()):
                    filled_categories += 1
                
                results['completeness'] = round(filled_categories / total_categories, 2)
            else:
                # If below threshold, return minimal data
                results['humint_data'] = {
                    'confidence': humint_data.get('confidence', 0),
                    'source': humint_data.get('source')
                }
                results['summary'] = []
                results['completeness'] = 0.0
        
        return jsonify({
            'results': results,
            'source': url if url else 'text_input',
            'threshold': threshold,
            'timestamp': datetime.now(),
            'status': 'success'
        })
    except Exception as e:
        logging.error(f"Error analyzing HUMINT data: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Failed to analyze HUMINT data: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/analyze/darkweb', methods=['POST'])
def analyze_darkweb():
    """
    Analyze text or URL content specifically for dark web indicators
    
    Expected JSON request body:
    {
        "text": "text content to analyze (optional)",
        "url": "website URL to analyze (optional)",
        "threshold": 0.7  # Optional confidence threshold (0.0-1.0)
    }
    
    At least one of 'text' or 'url' must be provided.
    """
    data = request.get_json()
    text_content = data.get('text', '').strip()
    url = data.get('url', '').strip()
    threshold = float(data.get('threshold', 0.7))
    
    if not text_content and not url:
        return jsonify({
            'error': 'Either text content or URL is required',
            'status': 'error'
        }), 400
    
    try:
        results = {'indicators': [], 'analysis': {}}
        
        # If a URL is provided, fetch its content
        html_content = None
        if url:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    html_content = response.text
                    # If no text was explicitly provided, extract it from the HTML
                    if not text_content:
                        text_content = get_website_text_content(url)
            except Exception as url_error:
                logging.warning(f"Error fetching URL content: {str(url_error)}")
                results['url_error'] = str(url_error)
        
        # Analyze for dark web indicators
        if html_content:
            dark_web_data = extract_dark_web_information(html_content=html_content, text_content=text_content)
            results['analysis'] = dark_web_data
            
            # Apply confidence threshold
            if dark_web_data.get('confidence', 0) >= threshold:
                # Extract high-confidence indicators
                if 'onion_services' in dark_web_data and dark_web_data['onion_services']:
                    results['indicators'].append({
                        'type': 'onion_services',
                        'description': 'Tor hidden services detected',
                        'confidence': 0.95,
                        'count': len(dark_web_data['onion_services'])
                    })
                
                if 'cryptocurrency_addresses' in dark_web_data:
                    for crypto_type, addresses in dark_web_data['cryptocurrency_addresses'].items():
                        if addresses:
                            results['indicators'].append({
                                'type': f'{crypto_type}_addresses',
                                'description': f'{crypto_type.capitalize()} cryptocurrency addresses found',
                                'confidence': 0.85,
                                'count': len(addresses)
                            })
                
                if 'secure_messaging' in dark_web_data:
                    for msg_type, identifiers in dark_web_data['secure_messaging'].items():
                        if identifiers:
                            results['indicators'].append({
                                'type': f'{msg_type}_messaging',
                                'description': f'Secure messaging ({msg_type}) identifiers detected',
                                'confidence': 0.8,
                                'count': len(identifiers)
                            })
                
                if 'security_indicators' in dark_web_data and dark_web_data['security_indicators']:
                    results['indicators'].append({
                        'type': 'security_terminology',
                        'description': 'Advanced security terminology detected',
                        'confidence': 0.7,
                        'terms': dark_web_data['security_indicators'][:5]  # Limit to top 5 terms
                    })
        
        # If we have text content but no HTML, do a simplified analysis
        elif text_content:
            # Create a mock HTML string just to reuse the extraction function
            mock_html = f"<html><body>{html.escape(text_content)}</body></html>"
            dark_web_data = extract_dark_web_information(html_content=mock_html, text_content=text_content)
            results['analysis'] = dark_web_data
            
            # Apply the same threshold logic as above
            if dark_web_data.get('confidence', 0) >= threshold:
                # Add the same indicator processing as above
                if 'onion_services' in dark_web_data and dark_web_data['onion_services']:
                    results['indicators'].append({
                        'type': 'onion_services',
                        'description': 'Tor hidden services detected',
                        'confidence': 0.95,
                        'count': len(dark_web_data['onion_services'])
                    })
                
                # Same for cryptocurrency, secure messaging and security indicators
                # (Simplified - in real code we'd avoid this duplication)
                if 'cryptocurrency_addresses' in dark_web_data:
                    for crypto_type, addresses in dark_web_data['cryptocurrency_addresses'].items():
                        if addresses:
                            results['indicators'].append({
                                'type': f'{crypto_type}_addresses',
                                'description': f'{crypto_type.capitalize()} cryptocurrency addresses found',
                                'confidence': 0.85,
                                'count': len(addresses)
                            })
        
        return jsonify({
            'results': results,
            'source': url if url else 'text_input',
            'threshold': threshold,
            'timestamp': datetime.now(),
            'status': 'success'
        })
    except Exception as e:
        logging.error(f"Error analyzing dark web indicators: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Failed to analyze dark web indicators: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/analyze/file/<filename>', methods=['GET'])
def analyze_existing_file(filename):
    """
    Analyze an existing file in the attached_assets directory
    """
    try:
        # Get the file path
        file_path = os.path.join('attached_assets', filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'error': f"File not found: {filename}",
                'status': 'error'
            }), 404
        
        # Process the file
        result = process_attached_file(file_path)
        
        # Check for errors in the result
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'status': 'error'
            }), 500
        
        # Return the analysis results
        return jsonify({
            'filename': filename,
            'analysis': result,
            'status': 'success'
        })
    
    except Exception as e:
        logging.error(f"Error analyzing existing file: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Failed to analyze file: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/api/info', methods=['GET'])
def api_info():
    """Provide information about the API"""
    # New endpoints added:
    # - /search/username - Enhanced username search with improved variation detection
    # - /search/advanced - Advanced people search using multiple identifiers (idcrawl.com-inspired)
    return jsonify({
        'name': 'unve1ler',
        'description': 'Advanced OSINT tool for discovering online profiles, geolocation data, contact information, and performing reverse image searches',
        'version': VERSION,
        'capabilities': {
            'username_search': 'Search for profiles across social media platforms',
            'people_finder': 'Advanced search for individuals using multiple identifiers (name, email, phone, username)',
            'identity_verification': 'Verify and cross-check identity information across platforms',
            'reverse_image_search': 'Generate reverse image search links for popular search engines',
            'metadata_extraction': 'Extract metadata from profiles including avatar, bio, followers, etc.',
            'content_extraction': 'Extract readable content from web pages',
            'geolocation_detection': 'Extract geolocation data from websites using various methods',
            'contact_information': 'Extract email addresses, phone numbers and physical addresses',
            'dark_web_detection': 'Identify potential dark web services and cryptocurrency addresses',
            'humint_extraction': 'Extract human intelligence data like personal names, occupations, relationships, and biographical details',
            'username_intelligence': 'Advanced pattern recognition for potential usernames',
            'profile_photo_extraction': 'Advanced extraction of profile photos from social media accounts'
        },
        'endpoints': {
            '/': 'Web interface for the tool',
            '/search': 'POST endpoint for searching profiles and generating reverse image search links',
            '/search/username': 'POST endpoint for enhanced username search with improved variation detection',
            '/search/advanced': 'POST endpoint for advanced people search using multiple identifiers (idcrawl.com-inspired)',
            '/extract': 'POST endpoint for extracting readable content, geolocation and contact information from websites',
            '/analyze/text': 'POST endpoint for analyzing text content to find social profiles, usernames, and image URLs',
            '/analyze/humint': 'POST endpoint for analyzing content to extract human intelligence data',
            '/analyze/darkweb': 'POST endpoint for analyzing content specifically for dark web indicators',
            '/analyze/simple_humint': 'POST endpoint for faster HUMINT analysis of text content only',
            '/analyze/simple_darkweb': 'POST endpoint for faster dark web analysis of text content only',
            '/analyze/file': 'POST endpoint for analyzing file content to find profiles and other indicators',
            '/analyze/file/<filename>': 'GET endpoint for analyzing an existing file in the attached_assets directory',
            '/api/info': 'GET information about the API capabilities and endpoints'
        }
    })

@app.route('/analyze/simple_humint', methods=['POST'])
def simple_humint():
    """
    A simpler, faster version of the HUMINT analysis endpoint.
    Analyzes text content directly without URL fetching or complex processing.
    
    Expected JSON request body:
    {
        "text": "text content to analyze",
        "threshold": 0.5  # Optional confidence threshold (0.0-1.0)
    }
    """
    data = request.get_json()
    text_content = data.get('text', '').strip()
    threshold = float(data.get('threshold', 0.5))
    
    if not text_content:
        return jsonify({
            'error': 'Text content is required',
            'status': 'error'
        }), 400
    
    try:
        # Directly call the extract_humint_data function with text only
        humint_data = extract_humint_data(text_content=text_content)
        
        # Apply threshold filtering
        if humint_data.get('confidence', 0) < threshold:
            return jsonify({
                'message': 'No HUMINT data found above the confidence threshold',
                'threshold': threshold,
                'confidence': humint_data.get('confidence', 0),
                'status': 'success_empty'
            })
        
        # Return the simplified results
        return jsonify({
            'humint_data': humint_data,
            'status': 'success'
        })
        
    except Exception as e:
        logging.error(f"Error in simple HUMINT analysis: {str(e)}")
        return jsonify({
            'error': f"Analysis failed: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/analyze/simple_darkweb', methods=['POST'])
def simple_darkweb():
    """
    A simpler, faster version of the dark web analysis endpoint.
    Analyzes text content directly without URL fetching or complex processing.
    
    Expected JSON request body:
    {
        "text": "text content to analyze",
        "threshold": 0.5  # Optional confidence threshold (0.0-1.0)
    }
    """
    data = request.get_json()
    text_content = data.get('text', '').strip()
    threshold = float(data.get('threshold', 0.5))
    
    if not text_content:
        return jsonify({
            'error': 'Text content is required',
            'status': 'error'
        }), 400
    
    try:
        # Directly call the extract_dark_web_information function with text only
        dark_web_data = extract_dark_web_information(html_content=None, text_content=text_content)
        
        # Apply threshold filtering
        if dark_web_data.get('confidence', 0) < threshold:
            return jsonify({
                'message': 'No dark web indicators found above the confidence threshold',
                'threshold': threshold,
                'confidence': dark_web_data.get('confidence', 0),
                'status': 'success_empty'
            })
        
        # Return the simplified results
        return jsonify({
            'dark_web_data': dark_web_data,
            'status': 'success'
        })
        
    except Exception as e:
        logging.error(f"Error in simple dark web analysis: {str(e)}")
        return jsonify({
            'error': f"Analysis failed: {str(e)}",
            'status': 'error'
        }), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors by returning to the main page"""
    return render_template('index.html'), 404

@app.route('/search/advanced', methods=['POST'])
def search_advanced():
    """
    Advanced people search using multiple identifiers and comprehensive techniques.
    This endpoint integrates idcrawl.com-inspired capabilities to find people across platforms.
    
    Expected JSON request body:
    {
        "username": "username to search (optional)",
        "full_name": "person's full name (optional)",
        "location": "location to filter results (optional)",
        "email": "email address to search (optional)",
        "phone": "phone number to search (optional)"
    }
    
    At least one of username, full_name, email, or phone must be provided.
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    full_name = data.get('full_name', '').strip()
    location = data.get('location', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    
    if not any([username, full_name, email, phone]):
        return jsonify({
            'error': 'At least one search parameter (username, full_name, email, phone) is required',
            'status': 'error'
        }), 400
    
    try:
        # Track processing time
        start_time = time.time()
        
        # Use the PeopleFinder module to search across multiple sources
        results = search_person(
            full_name=full_name if full_name else None,
            username=username if username else None,
            location=location if location else None,
            email=email if email else None,
            phone=phone if phone else None
        )
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        # Enhance response with additional metadata
        response = {
            'identity': results['identity'],
            'social_profiles': results['social_profiles'],
            'contact_info': results['contact_info'],
            'humint_data': results['humint_data'],
            'search_summary': results['search_summary'],
            'processing_time_seconds': processing_time,
            'timestamp': datetime.now(),
            'status': 'success'
        }
        
        # Add completeness metrics
        completeness = results['search_summary'].get('search_completeness', 0)
        confidence = results['identity'].get('confidence', 0)
        
        if completeness < 0.2:
            response['completeness_status'] = 'very_low'
        elif completeness < 0.4:
            response['completeness_status'] = 'low'
        elif completeness < 0.6:
            response['completeness_status'] = 'medium'
        elif completeness < 0.8:
            response['completeness_status'] = 'high'
        else:
            response['completeness_status'] = 'very_high'
            
        # Add a text summary for the user
        response['summary_text'] = results['search_summary'].get('text_summary', 
            f"Search completed in {processing_time} seconds with {int(confidence * 100)}% confidence.")
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error in advanced search: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Advanced search failed: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/search/username', methods=['POST'])
def search_username_api():
    """
    Search for a username across multiple platforms and find associated profiles.
    This endpoint specifically focuses on username searches with enhanced variation detection.
    
    Expected JSON request body:
    {
        "username": "username to search"
    }
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({
            'error': 'Username is required',
            'status': 'error'
        }), 400
    
    try:
        # Track processing time
        start_time = time.time()
        
        # Use the specialized username search function
        results = search_username(username)
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        # Prepare response
        response = {
            'username': results['username'],
            'profiles': results['profiles'],
            'profile_photos': results['profile_photos'],
            'variations_checked': results['variations_checked'],
            'confidence': results['confidence'],
            'summary': results['summary'],
            'processing_time_seconds': processing_time,
            'timestamp': datetime.now(),
            'status': 'success'
        }
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error in username search: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"Username search failed: {str(e)}",
            'status': 'error'
        }), 500

@app.route('/test/idcrawl-automation', methods=['POST'])
def test_idcrawl_automation():
    """
    Test endpoint for the new IDCrawl automation feature.
    
    Expected JSON request body:
    {
        "type": "username" or "person",
        "query": "search term",
        "location": "optional location for person searches",
        "use_automation": true/false (default: true)
    }
    """
    data = request.get_json()
    search_type = data.get('type', 'username')
    query = data.get('query', '').strip()
    location = data.get('location', None)
    use_automation = data.get('use_automation', True)
    
    if not query:
        return jsonify({
            'error': 'Query parameter is required',
            'status': 'error'
        }), 400
    
    try:
        # Start timer
        start_time = time.time()
        
        # Check if automation dependencies are available
        automation_status = {
            'playwright_available': AUTOMATION_AVAILABLE,
            'automation_script_available': AUTOMATION_SCRIPT_AVAILABLE,
            'automation_enabled': use_automation,
            'using_automation': use_automation and AUTOMATION_AVAILABLE and AUTOMATION_SCRIPT_AVAILABLE
        }
        
        # Execute search based on type
        if search_type == 'username':
            results = search_username_on_idcrawl(query, use_automation=use_automation)
        elif search_type == 'person':
            results = search_person_on_idcrawl(query, location, use_automation=use_automation)
        else:
            return jsonify({
                'error': f"Invalid search type: {search_type}. Must be 'username' or 'person'",
                'status': 'error'
            }), 400
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        # Add metadata to response
        response = {
            'query': query,
            'search_type': search_type,
            'results': results,
            'automation_status': automation_status,
            'processing_time_seconds': processing_time,
            'timestamp': datetime.now(),
            'status': 'success' if results.get('success', False) else 'error'
        }
        
        if location:
            response['location'] = location
            
        if results.get('requires_captcha', False):
            response['status'] = 'captcha_required'
            response['message'] = 'CAPTCHA verification required. Automation may have been detected.'
        elif results.get('requires_system_deps', False):
            response['status'] = 'system_deps_required'
            response['message'] = 'Missing system dependencies for browser automation.'
            response['missing_deps_error'] = results.get('missing_deps_error', 'Unknown dependency error')
            response['solution'] = 'Install browser dependencies or use direct method (use_automation=false)'
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error in IDCrawl automation test: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': f"IDCrawl automation test failed: {str(e)}",
            'automation_status': {
                'playwright_available': AUTOMATION_AVAILABLE,
                'automation_script_available': AUTOMATION_SCRIPT_AVAILABLE,
                'automation_enabled': use_automation
            },
            'status': 'error'
        }), 500

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors with a JSON response"""
    logging.error(f"Server error: {str(e)}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500
