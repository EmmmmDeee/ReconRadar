"""
Test script to check if the IDCrawl username checking functionality is working.
This script adds a simple endpoint to your Flask app to test the functionality.
"""

import logging
import argparse
from flask import Blueprint, request, jsonify, current_app
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("idcrawl_endpoint_test")

# Import our modules
try:
    from models import load_config
    from osint_modules import run_username_checks_async, USERNAME_CHECK_ENABLED, CHECK_TYPE
    CONFIG = load_config()
    logger.info(f"Successfully imported config and modules. Username check is {'' if USERNAME_CHECK_ENABLED else 'NOT '}enabled. Using {CHECK_TYPE} for checks.")
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure models.py, osint_modules.py, and config.json are in the correct location")

# Thread pool for running async code in Flask
executor = ThreadPoolExecutor(max_workers=4)

# Async wrapper to run in Flask
def async_wrapper(async_func):
    """Wrapper to run async functions in Flask"""
    async def run_async(*args, **kwargs):
        try:
            async with aiohttp.ClientSession() as session:
                kwargs['session'] = session  # Add session to kwargs
                return await async_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in async_wrapper: {e}", exc_info=True)
            return {"error": str(e)}
            
    def wrapper(*args, **kwargs):
        try:
            return asyncio.run(run_async(*args, **kwargs))
        except Exception as e:
            logger.error(f"Error running async function: {e}", exc_info=True)
            return {"error": str(e)}
        
    return wrapper

# Blueprint creation function
def create_test_blueprint():
    """Create a blueprint for testing the IDCrawl username checking functionality"""
    bp = Blueprint('idcrawl_test', __name__)
    
    @bp.route('/test/username-check', methods=['GET', 'POST'])
    def test_username_check():
        """Test endpoint for the IDCrawl username checking functionality"""
        # Default username if none provided
        default_username = "johnsmith"
        
        if request.method == 'POST':
            try:
                data = request.json
                if not data:
                    return jsonify({"status": "error", "message": "No JSON data provided"}), 400
                    
                # Extract usernames
                usernames = data.get('usernames', [default_username])
                if isinstance(usernames, str):
                    usernames = [usernames]  # Convert single username to list
                    
                if not isinstance(usernames, list):
                    return jsonify({"status": "error", "message": "Invalid usernames format"}), 400
                    
                # Run username checks with a timeout limit
                logger.info(f"Starting username checks for: {usernames}")
                # Use a shorter timeout for testing
                max_check_time = 10  # seconds
                import threading
                import time
                
                # Create a dictionary to store results
                result_dict = {"status": "timeout", "message": "Check took too long"}
                
                def run_check():
                    nonlocal result_dict
                    try:
                        result_dict = run_username_checks_wrapper(usernames)
                    except Exception as e:
                        logger.error(f"Error in check thread: {e}")
                        result_dict = {"error": str(e)}
                
                # Start the check in a separate thread
                check_thread = threading.Thread(target=run_check)
                check_thread.daemon = True
                check_thread.start()
                
                # Wait for the thread to complete or timeout
                start_time = time.time()
                check_thread.join(timeout=max_check_time)
                
                # Check if we timed out
                if check_thread.is_alive():
                    logger.warning(f"Username check timed out after {max_check_time} seconds")
                    results = {"status": "timeout", "message": f"Check timed out after {max_check_time} seconds"}
                else:
                    results = result_dict
                    logger.info(f"Check completed in {time.time() - start_time:.2f} seconds")
                
                # Return results
                return jsonify({
                    "status": "success",
                    "message": f"Checked {len(usernames)} usernames",
                    "data": results
                })
                
            except Exception as e:
                logger.error(f"Error in test_username_check: {e}", exc_info=True)
                return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
        
        # If GET request, show a simple form
        return """
        <html>
            <head>
                <title>Test IDCrawl Username Checking</title>
                <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
                <style>
                    body {
                        padding: 20px;
                    }
                    #results {
                        margin-top: 20px;
                        white-space: pre-wrap;
                        background-color: #222;
                        padding: 15px;
                        border-radius: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="mt-4 mb-4">Test IDCrawl Username Checking</h1>
                    <div class="card">
                        <div class="card-body">
                            <form id="usernameForm">
                                <div class="mb-3">
                                    <label for="usernames" class="form-label">Usernames (comma-separated)</label>
                                    <input type="text" class="form-control" id="usernames" value="johnsmith">
                                </div>
                                <button type="submit" class="btn btn-primary">Check Usernames</button>
                            </form>
                        </div>
                    </div>
                    
                    <div class="card mt-4">
                        <div class="card-header">Results</div>
                        <div class="card-body">
                            <div id="loading" style="display: none;">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <span class="ms-2">Checking usernames, please wait...</span>
                            </div>
                            <pre id="results">No results yet.</pre>
                        </div>
                    </div>
                </div>
                
                <script>
                    document.getElementById('usernameForm').addEventListener('submit', async function(e) {
                        e.preventDefault();
                        
                        const usernamesInput = document.getElementById('usernames').value;
                        const usernames = usernamesInput.split(',').map(u => u.trim()).filter(u => u);
                        
                        if (!usernames.length) {
                            alert('Please enter at least one username');
                            return;
                        }
                        
                        // Show loading indicator
                        document.getElementById('loading').style.display = 'block';
                        document.getElementById('results').textContent = 'Checking usernames...';
                        
                        try {
                            const response = await fetch('/api/test/username-check', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    usernames: usernames
                                })
                            });
                            
                            const data = await response.json();
                            
                            // Format results
                            document.getElementById('results').textContent = JSON.stringify(data, null, 2);
                        } catch (error) {
                            document.getElementById('results').textContent = `Error: ${error.message}`;
                        } finally {
                            // Hide loading indicator
                            document.getElementById('loading').style.display = 'none';
                        }
                    });
                </script>
            </body>
        </html>
        """
    
    @bp.route('/test/status', methods=['GET'])
    def test_status():
        """Test endpoint to check if the IDCrawl username checking functionality is enabled"""
        # This is a simplified version that doesn't depend on potentially unbound variables
        try:
            # Get status from osint_modules without accessing possibly unbound variables
            from osint_modules import USERNAME_CHECK_ENABLED, CHECK_TYPE
            enabled = USERNAME_CHECK_ENABLED
            check_type = CHECK_TYPE
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing check status: {e}")
            enabled = False
            check_type = "unknown"
            
        return jsonify({
            "status": "success",
            "username_check_enabled": enabled,
            "check_type": check_type,
            "message": f"Username check is {'' if enabled else 'NOT '}enabled. Using {check_type} for checks."
        })
        
    return bp

# Async wrapper for run_username_checks_async
@async_wrapper
async def run_username_checks_wrapper(usernames, session=None):
    """Wrapper for run_username_checks_async"""
    try:
        results = await run_username_checks_async(usernames, session)
        
        # Convert Pydantic models to dictionaries
        serializable_results = {}
        for username, user_result in results.items():
            # If user_result is already a dictionary, use it directly
            if isinstance(user_result, dict):
                serializable_results[username] = user_result
            else:
                # Handle Pydantic model cases
                user_dict = {}
                try:
                    # For Pydantic v2
                    for site, data in user_result.root.items():
                        user_dict[site] = data.model_dump()
                except AttributeError:
                    try:
                        # For Pydantic v1
                        for site, data in user_result.__root__.items():
                            user_dict[site] = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
                    except AttributeError:
                        # Default fallback if neither attribute exists
                        logger.warning(f"Could not convert result for {username} to dictionary using Pydantic methods")
                        user_dict = {"error": "Failed to convert result to JSON-serializable format"}
                
                serializable_results[username] = user_dict
            
        return serializable_results
    except Exception as e:
        logger.error(f"Error in run_username_checks_wrapper: {e}", exc_info=True)
        return {"error": str(e)}
        
# Function to register the blueprint with a Flask app
def register_test_blueprint(app):
    """Register the test blueprint with a Flask app"""
    bp = create_test_blueprint()
    app.register_blueprint(bp, url_prefix='/api')
    logger.info("Registered IDCrawl test blueprint")
    
    
if __name__ == "__main__":
    print("This script is meant to be imported by your Flask app.")
    print("Add the following to your app.py:")
    print("from test_idcrawl_endpoint import register_test_blueprint")
    print("register_test_blueprint(app)")
    print("Then you can test the username checking at /api/test/username-check")