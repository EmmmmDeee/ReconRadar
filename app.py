import os
from flask import Flask, render_template, request, jsonify
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "unve1ler_default_secret")

from unve1ler import check_social_media, VERSION

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

@app.route('/api/info', methods=['GET'])
def api_info():
    """Provide information about the API"""
    return jsonify({
        'name': 'unve1ler',
        'description': 'OSINT tool for discovering online profiles by username and performing reverse image searches',
        'version': VERSION,
        'endpoints': {
            '/': 'Web interface for the tool',
            '/search': 'POST endpoint for searching profiles',
            '/api/info': 'GET information about the API'
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
