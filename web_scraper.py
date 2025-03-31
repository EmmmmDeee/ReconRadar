import logging
import trafilatura
import requests
from bs4 import BeautifulSoup

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
        from urllib.parse import urlparse, parse_qs
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

# Example usage
if __name__ == "__main__":
    test_url = "https://en.wikipedia.org/wiki/Open-source_intelligence"
    content = get_website_text_content(test_url)
    print(f"Extracted {len(content)} characters of content")
    print(content[:500] + "...")  # Print first 500 characters