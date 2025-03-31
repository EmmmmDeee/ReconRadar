from app import app

# Note: IDCrawl test endpoint is registered in app.py

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
