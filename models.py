"""
Pydantic models for the IDCrawl Username Checking functionality
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse

try:
    # For Pydantic v2
    from pydantic import BaseModel, field_validator, model_validator, HttpUrl, ValidationError
except ImportError:
    # Fallback for Pydantic v1
    from pydantic import BaseModel, validator as field_validator, root_validator as model_validator
    from pydantic import AnyHttpUrl as HttpUrl, ValidationError

logger = logging.getLogger(__name__)

# --- Configuration Models ---

class IdcrawlSettings(BaseModel):
    """Settings for the IDCrawl username checking functionality"""
    
    # Timeouts and concurrency
    IDCRAWL_TIMEOUT_SITE: float = 10.0
    IDCRAWL_CONCURRENCY_USER: int = 5  # Max concurrent site checks per username
    IDCRAWL_CONCURRENCY_GLOBAL: int = 20  # Max concurrent username checks
    IDCRAWL_RETRIES_SITE: int = 2  # Retries per site
    
    # User agent and proxy settings
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    PROXY: Optional[str] = None  # Optional proxy in format "http://user:pass@host:port"
    
    # Files and paths
    IDCRAWL_SITES_FILE: str = "sites.json"  # Path to the sites definition file
    
    # Browser automation settings
    IDCRAWL_HEADLESS: bool = True  # Run browser automation in headless mode
    
    @field_validator('IDCRAWL_TIMEOUT_SITE')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v
        
    @field_validator('IDCRAWL_CONCURRENCY_USER', 'IDCRAWL_CONCURRENCY_GLOBAL')
    def validate_concurrency(cls, v):
        if v <= 0:
            raise ValueError("Concurrency must be positive")
        if v > 100:
            logger.warning(f"High concurrency value: {v}")
        return v

class Config(BaseModel):
    """Main configuration model"""
    settings: IdcrawlSettings

# --- Result Models ---

class IdcrawlSiteResult(BaseModel):
    """Result of checking a username on a single site"""
    site_name: Optional[str] = None
    url_found: Optional[str] = None  # URL where the profile was found
    status: str  # "found", "not_found", or "error"
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    
    @field_validator('status')
    def validate_status(cls, v):
        if v not in ["found", "not_found", "error"]:
            raise ValueError(f"Invalid status: {v}")
        return v
        
    @field_validator('url_found')
    def validate_url(cls, v):
        if v is not None:
            try:
                # Check if it's a valid URL
                parsed = urlparse(v)
                if not all([parsed.scheme, parsed.netloc]):
                    raise ValueError(f"Invalid URL: {v}")
            except Exception as e:
                raise ValueError(f"Invalid URL ({str(e)}): {v}")
        return v

try:
    # For Pydantic v2
    from pydantic import RootModel
    
    class IdcrawlUserResult(RootModel):
        """Results of checking a username across multiple sites"""
        root: Dict[str, IdcrawlSiteResult]
except ImportError:
    # Fallback for Pydantic v1
    class IdcrawlUserResult(BaseModel):
        """Results of checking a username across multiple sites"""
        __root__: Dict[str, IdcrawlSiteResult]

# --- Helper Functions ---

def load_config(config_path: str = "config.json") -> Config:
    """Load configuration from a JSON file"""
    try:
        path_obj = Path(config_path)
        if not path_obj.exists():
            logger.warning(f"Config file not found: {config_path}")
            # Create default config
            default_config = Config(settings=IdcrawlSettings())
            with open(config_path, 'w') as f:
                if hasattr(default_config, 'model_dump'):
                    json.dump(default_config.model_dump(), f, indent=2)
                else:
                    json.dump(default_config.dict(), f, indent=2)
            logger.info(f"Created default config file: {config_path}")
            return default_config
            
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Validate and return config
        config = Config(**config_data)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}", exc_info=True)
        # Return default config
        return Config(settings=IdcrawlSettings())