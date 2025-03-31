"""
Pydantic models for the unve1ler OSINT tool
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, HttpUrl, validator
import json
import os
from pathlib import Path


class UsernameCheckConfig(BaseModel):
    """Configuration for username checking"""
    timeout: int = Field(10, ge=1, le=60, description="Request timeout in seconds")
    max_concurrent_checks: int = Field(20, ge=1, le=100, description="Maximum number of concurrent checks")
    error_delay: int = Field(2, ge=0, le=10, description="Delay between retries in seconds")
    retry_attempts: int = Field(2, ge=0, le=5, description="Number of retry attempts")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    user_agent: str = Field(..., description="User-Agent string to use for requests")
    allowed_http_codes: List[int] = Field([200, 201, 202], description="HTTP codes that indicate success")
    log_level: str = Field("INFO", description="Logging level")


class IDCrawlIntegrationConfig(BaseModel):
    """Configuration for IDCrawl integration"""
    use_automation: bool = Field(True, description="Use browser automation for IDCrawl")
    headless: bool = Field(True, description="Run browser in headless mode")
    browser_type: str = Field("chromium", description="Browser type to use")
    block_resources: bool = Field(True, description="Block unnecessary resources")
    use_stealth: bool = Field(True, description="Use stealth techniques")
    timeout: int = Field(60, ge=10, le=300, description="Browser timeout in seconds")
    max_retry: int = Field(3, ge=0, le=5, description="Maximum number of retries")


class Config(BaseModel):
    """Main configuration model"""
    username_check: UsernameCheckConfig
    idcrawl_integration: IDCrawlIntegrationConfig


class IdcrawlSiteResult(BaseModel):
    """Result of a single site check"""
    site_name: str = Field(..., description="Name of the site checked")
    url_checked: HttpUrl = Field(..., description="URL that was checked")
    found: bool = Field(False, description="Whether the profile was found")
    status_code: Optional[int] = Field(None, description="HTTP status code received")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error: Optional[str] = Field(None, description="Error message if check failed")
    profile_url: Optional[str] = Field(None, description="URL of the found profile")
    username_used: str = Field(..., description="Username used for the check")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")

    @validator('confidence')
    def check_confidence(cls, v):
        """Ensure confidence is between 0 and 1"""
        return max(0.0, min(1.0, v))


class IdcrawlUserResult(BaseModel):
    """Results of username checks across multiple sites"""
    username: str = Field(..., description="Username that was checked")
    variations_checked: List[str] = Field([], description="Username variations that were checked")
    sites_checked: int = Field(0, description="Number of sites checked")
    sites_with_profiles: int = Field(0, description="Number of sites where profiles were found")
    execution_time: float = Field(0.0, description="Total execution time in seconds")
    results: List[IdcrawlSiteResult] = Field([], description="Results for each site")
    sites_with_errors: int = Field(0, description="Number of sites with errors")
    highest_confidence: float = Field(0.0, description="Highest confidence score")
    target_category: Optional[str] = Field(None, description="Target category if identified")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")
    additional_urls: List[str] = Field([], description="Additional URLs discovered")

    def calculate_summary_stats(self):
        """Calculate summary statistics based on results"""
        self.sites_checked = len(self.results)
        self.sites_with_profiles = sum(1 for r in self.results if r.found)
        self.sites_with_errors = sum(1 for r in self.results if r.error is not None)
        confidence_scores = [r.confidence for r in self.results if r.found]
        self.highest_confidence = max(confidence_scores) if confidence_scores else 0.0


def load_config() -> Config:
    """Load configuration from config.json file"""
    config_path = Path("config.json")
    if not config_path.exists():
        # Use default config if file doesn't exist
        return Config(
            username_check=UsernameCheckConfig(
                timeout=10,
                max_concurrent_checks=20,
                error_delay=2,
                retry_attempts=2,
                verify_ssl=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                allowed_http_codes=[200, 201, 202, 301, 302, 308],
                log_level="INFO"
            ),
            idcrawl_integration=IDCrawlIntegrationConfig(
                use_automation=True,
                headless=True,
                browser_type="chromium",
                block_resources=True,
                use_stealth=True,
                timeout=60,
                max_retry=3
            )
        )
    
    with open(config_path, "r") as f:
        config_data = json.load(f)
    
    return Config(**config_data)