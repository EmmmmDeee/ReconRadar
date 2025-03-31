# osint_modules.py - Refined Orchestrator for Idcrawl/Sherlock

import asyncio
import json
import logging
import random
import re
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse  # Needed for Sherlock helper

# --- Import Scraper / Fallback Logic ---
CHECK_FUNCTION = None
CHECK_TYPE = "None"
USERNAME_CHECK_ENABLED = False
logger = logging.getLogger(__name__)

try:
    # Try importing your custom scraper first
    from idcrawl_scraper import check_username_on_sites_async, load_sites_from_file
    CHECK_FUNCTION = check_username_on_sites_async
    CHECK_TYPE = "Idcrawl"
    USERNAME_CHECK_ENABLED = True
    logger.info("Using custom 'idcrawl_scraper' for username checks.")
except ImportError:
    logger.warning("Could not import from idcrawl_scraper.py. Attempting Sherlock fallback...")
    # Fallback to Sherlock if idcrawl_scraper not found
    try:
        # Check if sherlock command exists? Assume installed if package listed.
        async def _execute_sherlock_for_user(username: str, timeout: float, **kwargs) -> Dict[str, Any]:
             """Helper to execute sherlock and return structured dict matching IdcrawlUserResult.__root__."""
             # Ensure username is safe for shell command (basic check)
             if not re.match(r'^[a-zA-Z0-9._-]+$', username): return {"error": {"status": "error", "error_message": "Invalid username format for Sherlock"}}

             command_parts = ["sherlock", "--timeout", str(round(timeout, 1)), "--print-found", "--no-color", username]
             logger.debug(f"Executing Sherlock command: {' '.join(command_parts)}")
             proc = await asyncio.create_subprocess_exec(*command_parts, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
             try: stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5.0)
             except asyncio.TimeoutError:
                 logger.warning(f"Sherlock process timed out externally for username '{username}'")
                 try: proc.terminate(); await asyncio.wait_for(proc.wait(), 1.0)
                 except: proc.kill(); await proc.wait()
                 return {"sherlock_timeout": {"status": "error", "error_message": "Sherlock process timed out"}}

             stdout_str = stdout.decode('utf-8', 'replace').strip()
             stderr_str = stderr.decode('utf-8', 'replace').strip()
             results_dict: Dict[str, Dict] = {}  # Stores site_name -> IdcrawlSiteResult compatible dict

             if proc.returncode != 0: logger.warning(f"Sherlock for '{username}' exited {proc.returncode}. Stderr: {stderr_str}")
             elif stderr_str: logger.warning(f"Sherlock stderr for '{username}': {stderr_str}")

             found_urls = [line.strip() for line in stdout_str.splitlines() if line.strip().startswith('http')]

             if not found_urls:
                 status = "error" if proc.returncode != 0 else "not_found"
                 err_msg = f"Sherlock failed (code {proc.returncode})" if proc.returncode != 0 else None
                 # Use Pydantic model to create the dict for consistency
                 results_dict["sherlock_status"] = {"site_name": "Sherlock Status", "status": status, "error_message": err_msg}
             else:
                 for url in found_urls:
                     try: site_name = urlparse(url).netloc.replace('www.', '').split('.')[0]
                     except: site_name = url  # fallback
                     results_dict[site_name] = {"site_name": site_name, "status": "found", "url_found": url}
             return results_dict  # Return dict matching structure

        CHECK_FUNCTION = _execute_sherlock_for_user
        CHECK_TYPE = "Sherlock"
        USERNAME_CHECK_ENABLED = True
        logger.info("Using 'sherlock-project' fallback for username checks.")

    except Exception as sherlock_err:
         logger.error(f"Sherlock fallback setup failed: {sherlock_err}. Username checks disabled.")
         USERNAME_CHECK_ENABLED = False
         # Define dummy CHECK_FUNCTION if everything fails
         async def check_username_on_sites_async_dummy(*args, **kwargs): return {"error": {"status": "error", "error_message": "Username checking unavailable"}}
         CHECK_FUNCTION = check_username_on_sites_async_dummy
         CHECK_TYPE = "None"


# Import shared config
try:
    from models import load_config, IdcrawlSiteResult, IdcrawlUserResult, ValidationError
    CONFIG = load_config()
    if CONFIG is None: raise ImportError("CONFIG is None")
except ImportError:
    logging.getLogger(__name__).critical("Could not import CONFIG from models.")
    CONFIG = None

# --- Username Validation Pattern ---
USERNAME_VALIDATION_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,30}[a-zA-Z0-9]$")

# --- Username Checking Orchestration ---

async def run_username_checks_async(
    usernames: List[str],
    session: 'aiohttp.ClientSession'  # Session might be needed by custom scraper
    ) -> Dict[str, Any]:  # Return type uses Pydantic model
    """
    Orchestrates asynchronous username checks using the configured method.
    """
    start_time = time.time()
    # Create error result structure based on Pydantic model
    error_site_result = {"status": "error", "error_message": "Username checking feature disabled"}
    
    try:
        # Create error user result
        try:
            # Pydantic v2
            error_user_result = {"root": {"error": error_site_result}}
        except:
            # Pydantic v1
            error_user_result = {"__root__": {"error": error_site_result}}
    except:
        # Fallback to simple dict if Pydantic fails
        error_user_result = {"error": error_site_result}

    if not USERNAME_CHECK_ENABLED:
        return {u: error_user_result for u in usernames}
    if not usernames: return {}
    if CONFIG is None or not CONFIG.settings:
        logger.error("Username check cannot run: Configuration not loaded.")
        error_site_result["error_message"] = "Configuration error"
        return {u: error_user_result for u in usernames}

    check_results: Dict[str, Any] = {}
    settings = CONFIG.settings
    timeout = float(settings.IDCRAWL_TIMEOUT_SITE)
    concurrency_user = int(settings.IDCRAWL_CONCURRENCY_USER)
    global_concurrency = int(settings.IDCRAWL_CONCURRENCY_GLOBAL)
    sites_file = settings.IDCRAWL_SITES_FILE

    # --- Filter and validate usernames ---
    valid_usernames = set()
    for u in usernames:
        if isinstance(u, str) and USERNAME_VALIDATION_PATTERN.match(u): valid_usernames.add(u)
        else: logger.debug(f"Skipping invalid username for {CHECK_TYPE}: '{u}'")
    if not valid_usernames: return {}
    unique_usernames = sorted(list(valid_usernames))

    logger.info(f"Starting {CHECK_TYPE} checks for {len(unique_usernames)} usernames (Global Concurrency: {global_concurrency})...")

    # --- Create Semaphore & Tasks ---
    semaphore = asyncio.Semaphore(global_concurrency)
    tasks = [
        asyncio.create_task(
            _run_single_user_check_with_semaphore(
                semaphore=semaphore,
                username=username,
                session=session,
                timeout=timeout,
                concurrency_limit=concurrency_user,  # Pass relevant args
                sites_file=sites_file  # Pass relevant args
            ),
            name=f"{CHECK_TYPE}-{username}"
        ) for username in unique_usernames
    ]

    # --- Gather and Process Results ---
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    total_sites_found_overall = 0
    total_errors = 0

    for i, result_data in enumerate(results_list):
        username = unique_usernames[i]
        user_result_dict = {}  # This will become the data for the Pydantic model
        
        if isinstance(result_data, Exception):
            logger.error(f"{CHECK_TYPE} check task failed unexpectedly for '{username}': {result_data}", exc_info=result_data)
            # Set up error data
            user_result_dict = {"task_error": {"status": "error", "error_message": f"Task execution failed: {type(result_data).__name__}"}}
            total_errors += 1
        elif isinstance(result_data, dict):
            user_result_dict = result_data
            # Calculate stats based on the returned dict structure
            if "error" in user_result_dict:  # Check for top-level error key
                 error_val = user_result_dict["error"]
                 # Check if the error value itself indicates an error status
                 if isinstance(error_val, dict) and error_val.get("status") == "error":
                     total_errors += 1
            else:
                 # Count found sites only if no top-level error
                 found_count = len([site for site, data in user_result_dict.items() 
                                   if isinstance(data, dict) and data.get('status') == 'found'])
                 total_sites_found_overall += found_count
                 logger.info(f"{CHECK_TYPE} check for '{username}' completed. Found on ~{found_count} sites.")
        else:  # Unexpected type
            logger.error(f"Unexpected result type for {CHECK_TYPE} check on '{username}': {type(result_data)}")
            user_result_dict = {"internal_error": {"status": "error", "error_message": "Unexpected result format"}}
            total_errors += 1

        # --- Validate and store using Pydantic model ---
        try:
            # Ensure the structure matches the expected model format
            validated_site_results = {}
            for site_name, site_data in user_result_dict.items():
                if isinstance(site_data, dict):
                    try:  # Validate each site result individually
                        validated_site_results[site_name] = site_data  # Simply store valid dicts
                    except Exception as site_val_err:
                        logger.warning(f"Site result validation failed for {username}/{site_name}: {site_val_err}")
                        validated_site_results[site_name] = {"status": "error", "error_message": "Invalid site result format"}
                else:  # Handle cases where a value isn't a dict
                    validated_site_results[site_name] = {"status": "error", "error_message": "Invalid site data type"}

            # Store results for this username
            # Try both v1 and v2 Pydantic formats
            try:
                # Pydantic v2
                check_results[username] = {"root": validated_site_results}
            except:
                # Pydantic v1
                check_results[username] = {"__root__": validated_site_results}

        except Exception as e:  # Catch any validation error
            logger.warning(f"Overall result validation failed for '{username}': {e}. Storing raw result with error.")
            # Store minimal error structure compliant with the model
            check_results[username] = {"root": {"validation_error": {"status": "error", "error_message": "Result format invalid"}}}
            total_errors += 1

    elapsed = time.time() - start_time
    logger.info(f"{CHECK_TYPE} checks finished for {len(unique_usernames)} usernames in {elapsed:.2f}s. "
                f"Total sites found: {total_sites_found_overall}. Total errors/issues: {total_errors}.")

    return check_results


async def _run_single_user_check_with_semaphore(semaphore: asyncio.Semaphore, **kwargs) -> Dict[str, Any]:
    """Acquires semaphore, runs the check for one user, releases semaphore."""
    username = kwargs.get("username", "unknown")
    logger.debug(f"Waiting for semaphore for {CHECK_TYPE} check on '{username}'...")
    async with semaphore:
        logger.debug(f"Acquired semaphore for '{username}'. Running {CHECK_TYPE} check...")
        try:
            # Call the selected CHECK_FUNCTION
            # Prepare args based on CHECK_TYPE to avoid passing unnecessary ones
            func_kwargs = {"username": username, "timeout": kwargs.get("timeout")}
            if CHECK_TYPE == "Idcrawl":
                 func_kwargs["session"] = kwargs.get("session")
                 func_kwargs["concurrency_limit"] = kwargs.get("concurrency_limit")
                 func_kwargs["user_agents"] = CONFIG.settings.USER_AGENTS if CONFIG and CONFIG.settings else None
                 func_kwargs["proxy"] = str(CONFIG.settings.PROXY) if CONFIG and CONFIG.settings and CONFIG.settings.PROXY else None
                 func_kwargs["sites_file"] = kwargs.get("sites_file")
            # Sherlock fallback (_execute_sherlock_for_user) only needs username and timeout

            result_dict = await CHECK_FUNCTION(**func_kwargs)
            # Ensure return is always a dict
            return result_dict if isinstance(result_dict, dict) else {"error": {"status": "error", "error_message": "Check function returned non-dict"}}
        except Exception as e:
             logger.error(f"Exception during {CHECK_TYPE} check for '{username}': {e}", exc_info=True)
             # Return structure matching IdcrawlUserResult.__root__
             return {"error": {"status": "error", "error_message": f"Check function failed: {type(e).__name__}"}}
        finally:
             logger.debug(f"Released semaphore for '{username}'.")