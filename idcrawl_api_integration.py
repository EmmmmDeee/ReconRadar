"""
Sample code to integrate IDCrawl username checking with the app.py Flask API
"""

from flask import Blueprint, request, jsonify, current_app
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import logging
import re
import json
from typing import List, Dict, Any, Optional

# Import our modules
from models import load_config
from osint_modules import run_username_checks_async

# Create a Flask Blueprint
idcrawl_blueprint = Blueprint('idcrawl', __name__)

# Configure logging
logger = logging.getLogger("idcrawl_api")

# Regex pattern for username validation
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{2,30}$')

# Thread pool for running async code in Flask
executor = ThreadPoolExecutor(max_workers=4)

# Async wrapper to run in Flask
def async_wrapper(async_func):
    """Wrapper to run async functions in Flask"""
    async def run_async(*args, **kwargs):
        async with aiohttp.ClientSession() as session:
            kwargs['session'] = session  # Add session to kwargs
            return await async_func(*args, **kwargs)
            
    def wrapper(*args, **kwargs):
        return asyncio.run(run_async(*args, **kwargs))
        
    return wrapper

@idcrawl_blueprint.route('/api/username-check', methods=['POST'])
def username_check_endpoint():
    """API endpoint for checking usernames"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400
            
        # Extract usernames
        usernames = data.get('usernames', [])
        if not usernames:
            return jsonify({"status": "error", "message": "No usernames provided"}), 400
            
        # Validate usernames
        if isinstance(usernames, str):
            usernames = [usernames]  # Convert single username to list
            
        if not isinstance(usernames, list):
            return jsonify({"status": "error", "message": "Invalid usernames format"}), 400
            
        # Filter valid usernames
        valid_usernames = []
        for username in usernames[:10]:  # Limit to 10 usernames
            if isinstance(username, str) and USERNAME_PATTERN.match(username):
                valid_usernames.append(username)
        
        if not valid_usernames:
            return jsonify({"status": "error", "message": "No valid usernames provided"}), 400
            
        # Run username checks
        logger.info(f"Starting username checks for: {valid_usernames}")
        results = run_username_checks_wrapper(valid_usernames)
        
        # Convert Pydantic models to dictionaries for JSON response
        serializable_results = {}
        for username, user_result in results.items():
            serializable_results[username] = {
                site: {
                    "site_name": data.site_name,
                    "url_found": data.url_found,
                    "status": data.status,
                    "error_message": data.error_message,
                    "http_status": data.http_status
                } for site, data in user_result.__root__.items()
            }
        
        return jsonify({
            "status": "success",
            "message": f"Checked {len(valid_usernames)} usernames",
            "data": serializable_results
        })
            
    except Exception as e:
        logger.error(f"Error in username check endpoint: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

# Async wrapper for run_username_checks_async
@async_wrapper
async def run_username_checks_wrapper(usernames: List[str], session=None) -> Dict[str, Any]:
    """Wrapper for run_username_checks_async"""
    try:
        return await run_username_checks_async(usernames, session)
    except Exception as e:
        logger.error(f"Error in username checks: {e}", exc_info=True)
        return {}

# Function to integrate this blueprint with the main Flask app
def register_idcrawl_blueprint(app):
    """Register the IDCrawl blueprint with the Flask app"""
    app.register_blueprint(idcrawl_blueprint)
    logger.info("Registered IDCrawl API blueprint")


"""
# Sample code to add to your main app.py

from idcrawl_api_integration import register_idcrawl_blueprint

# After creating your Flask app:
register_idcrawl_blueprint(app)

# Now you can access the API at /api/username-check
"""