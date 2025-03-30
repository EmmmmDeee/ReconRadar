import os
from flask import Flask, render_template, request, jsonify
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "unve1ler_default_secret")

from unve1ler import check_social_media

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    username = data.get('username', '')
    image_url = data.get('image_url', None)
    
    if not username:
        return jsonify({
            'error': 'Username is required',
            'status': 'error'
        }), 400
    
    # Use the check_social_media function to get results
    results, stats, reverse_image_urls = check_social_media(username, image_url)
    
    return jsonify({
        'results': results,
        'stats': stats,
        'reverse_image_urls': reverse_image_urls if image_url else None,
        'status': 'success'
    })

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500
