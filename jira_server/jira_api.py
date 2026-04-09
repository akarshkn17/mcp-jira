import os
import requests
import logging
from requests.auth import HTTPBasicAuth
from typing import Dict, Any

logger = logging.getLogger("jira_mcp")

def search_issues(jql: str, start_at: int = 0, max_results: int = 100) -> Dict[str, Any]:
    """
    Searches Jira issues using the provided JQL query.
    Requires JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables.
    """
    base_url = os.environ.get("JIRA_BASE_URL")
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")

    if not all([base_url, email, token]):
        raise ValueError("Missing Jira configurations. Ensure JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN are set in your environment.")

    base_url = base_url.rstrip("/")
    url = f"{base_url}/rest/api/3/search/jql"
    auth = HTTPBasicAuth(email, token)
    
    headers = {
        "Accept": "application/json"
    }
    
    query = {
        "jql": jql,
        "maxResults": max_results,
        "fields": ["summary", "status", "assignee", "priority", "created", "reporter", "issuetype", "resolution"]
    }

    logger.info(f"--- API CALL INITIATED ---")
    logger.info(f"Target URL: {url}")
    logger.info(f"JQL Query: {jql}")

    try:
        response = requests.post(
            url,
            headers=headers,
            auth=auth,
            json=query,
            timeout=15
        )
        response.raise_for_status()
        
        logger.info(f"API CALL SUCCESS: status={response.status_code}")
        # Be careful not to log the entire response body if it's too big, but we log the first 500 chars to see what happened.
        logger.info(f"API Response Extract: {response.text[:500]}...")
        
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_msg = response.text if (response is not None and response.text) else str(e)
        logger.error(f"API ERROR ({response.status_code if response is not None else 'Unknown'}): {error_msg}")
        raise RuntimeError(f"Jira API error ({response.status_code if response is not None else 'Unknown'}): {error_msg}")
    except Exception as e:
        logger.error(f"UNEXPECTED COMMUNICATION ERROR: {str(e)}")
        raise RuntimeError(f"Failed to communicate with Jira: {str(e)}")
