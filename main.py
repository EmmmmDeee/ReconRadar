from app import app

# Import IDCrawl test endpoint
try:
    from test_idcrawl_endpoint import register_test_blueprint
    register_test_blueprint(app)
except ImportError as e:
    print(f"Could not import test_idcrawl_endpoint: {e}")
    print("The IDCrawl test endpoint will not be available.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
