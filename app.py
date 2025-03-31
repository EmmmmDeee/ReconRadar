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
    extract_contact_information
)
from assets import process_attached_file, extract_social_profiles_from_text, extract_usernames_from_text, extract_image_urls_from_text

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
        
        if html_content:
            try:
                # Extract geolocation data
                geolocation_data = extract_geolocation_data(html_content, url)
                
                # Extract contact information
                contact_data = extract_contact_information(html_content)
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
    return jsonify({
        'name': 'unve1ler',
        'description': 'Advanced OSINT tool for discovering online profiles, geolocation data, contact information, and performing reverse image searches',
        'version': VERSION,
        'capabilities': {
            'username_search': 'Search for profiles across social media platforms',
            'reverse_image_search': 'Generate reverse image search links for popular search engines',
            'metadata_extraction': 'Extract metadata from profiles including avatar, bio, followers, etc.',
            'content_extraction': 'Extract readable content from web pages',
            'geolocation_detection': 'Extract geolocation data from websites using various methods',
            'contact_information': 'Extract email addresses, phone numbers and physical addresses',
            'dark_web_detection': 'Identify potential dark web services and cryptocurrency addresses',
            'username_intelligence': 'Advanced pattern recognition for potential usernames'
        },
        'endpoints': {
            '/': 'Web interface for the tool',
            '/search': 'POST endpoint for searching profiles and generating reverse image search links',
            '/extract': 'POST endpoint for extracting readable content, geolocation and contact information from websites',
            '/analyze/text': 'POST endpoint for analyzing text content to find social profiles, usernames, and image URLs',
            '/analyze/file': 'POST endpoint for analyzing file content to find profiles and other indicators',
            '/analyze/file/<filename>': 'GET endpoint for analyzing an existing file in the attached_assets directory',
            '/api/info': 'GET information about the API capabilities and endpoints'
        }
    })

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors by returning to the main page"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors with a JSON response"""
    logging.error(f"Server error: {str(e)}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500
