import json
import logging
import os
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .jira_api import search_issues

# Load environment variables
load_dotenv()

# Setup explicit file logger for the server to track calls without breaking MCP stdio
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_path = os.path.join(app_dir, "jira_mcp_api.log")

file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger("jira_mcp")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(file_handler)

# Initialize FastMCP Server
mcp = FastMCP("jira-mcp-server")

@mcp.tool()
def search_jira_issues(jql: str, max_results: int = 100) -> str:
    """
    Search Jira for issues using a given JQL (Jira Query Language) string.
    Returns a JSON string containing a list of simplified issue objects.
    
    Args:
        jql: The Jira Query Language string to search issues with.
        max_results: The maximum number of issues to return (default 100).
    """
    try:
        logging.info(f"Received request to search Jira with JQL: {jql}")
        raw_result = search_issues(jql=jql, max_results=max_results)
        
        issues = raw_result.get("issues", [])
        
        # Flatten and filter the needed fields for easier consumption
        processed_issues = []
        for issue in issues:
            fields = issue.get("fields", {})
            
            # Safe extraction of nested fields
            assignee = fields.get("assignee")
            assignee_name = assignee.get("displayName") if assignee else "Unassigned"
            
            reporter = fields.get("reporter")
            reporter_name = reporter.get("displayName") if reporter else "Unknown"
            
            status = fields.get("status")
            status_name = status.get("name") if status else "Unknown"
            
            priority = fields.get("priority")
            priority_name = priority.get("name") if priority else "None"
            
            issuetype = fields.get("issuetype")
            issuetype_name = issuetype.get("name") if issuetype else "Unknown"
            
            resolution = fields.get("resolution")
            resolution_name = resolution.get("name") if resolution else "Unresolved"
            
            processed_issues.append({
                "key": issue.get("key"),
                "url": f"{raw_result.get('expand', '')}", # not easily available directly without domain, but we have it via env
                "summary": fields.get("summary", ""),
                "status": status_name,
                "priority": priority_name,
                "assignee": assignee_name,
                "reporter": reporter_name,
                "type": issuetype_name,
                "resolution": resolution_name,
                "created": fields.get("created", "")
            })
            
        return json.dumps({
            "total_found": raw_result.get("total", 0),
            "returned_count": len(processed_issues),
            "jql": jql,
            "issues": processed_issues
        }, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to search Jira: {str(e)}"
        logging.error(error_msg)
        return json.dumps({"error": error_msg})

@mcp.tool()
def fetch_all_jira_tickets(max_results: int = 100) -> str:
    """
    Fetch all Jira tickets without any specific JQL filtering.
    Returns a JSON string containing a list of simplified issue objects.
    
    Args:
        max_results: The maximum number of issues to return (default 100).
    """
    logging.info(f"Received request to fetch all Jira tickets")
    # Jira Cloud requires a bounding clause. 'project IS NOT EMPTY' effectively gathers all accessible tickets.
    return search_jira_issues(jql="project IS NOT EMPTY ORDER BY created DESC", max_results=max_results)

if __name__ == "__main__":
    mcp.run()
