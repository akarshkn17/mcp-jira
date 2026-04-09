# Jira MCP Integration Complete

I've successfully finished putting together the Jira Model Context Protocol (MCP) server and client exactly as outlined in the requirements. 

## Project Architecture & Structure

The codebase is broken down cleanly into two separate logical halves, communicating as standard MCP components.

### 1. Jira MCP Server
- **Provider (`jira_server/jira_api.py`)**: Responsible for securely calling Jira's Cloud API (`/rest/api/3/search`). Handles basic authentication and extracts fields cleanly.
- **FastMCP Endpoint (`jira_server/server.py`)**: Starts a FastMCP server over `.stdio` locally which listens for calls. It automatically exposes the `search_jira_issues` tool to connected clients. It cleans up the Jira JSON schemas, catching edge cases where names might be unassigned.

### 2. Jira MCP Client
- **LLM Orchestrator (`jira_client/llm_orchestrator.py`)**: Uses the `google-genai` SDK and the `gemini-2.5-pro` model to dynamically form the target JQL. It translates requests like _"Fetch all open bugs assigned to me"_ directly into a tool execution (`search_jira_issues`) with valid Jira fields.
- **MCP Client (`jira_client/client.py`)**: Connects to the server over standard standard-input/output (`sys.executable`). It dispatches the LLM's requested JQL parameter as an MCP Tool Call and then forwards the payload down to the CSV Exporter.
- **CSV Exporter (`jira_client/csv_exporter.py`)**: Takes the clean JSON dictionary array mapped by the API Provider and dynamically writes out the `csv` object mapped with headers for `key`, `summary`, `status`, `assignee`, etc.

## Setup Instructions

1. Ensure the generated `.venv` virtual environment is used given dependencies were sourced using `uv` (as per the prompt requirements).
2. Inside `.env.example` in your main directory, you will find template variables. Rename this copy to `.env` and configure with your specific tokens:
   - `JIRA_BASE_URL` (E.g. `https://mybusiness.atlassian.net`)
   - `JIRA_EMAIL` & `JIRA_API_TOKEN`
   - `GEMINI_API_KEY`

## Example Usage

Run the client script from your workspace using the virtual Python:

```powershell
# Default run
.venv\Scripts\python -m jira_client.client "Fetch all the offboarding tickets from the last 7 days"

# Custom Export Name
.venv\Scripts\python -m jira_client.client "Fetch all open bugs in project APPSEC assigned to me" --output open_bugs.csv
```

> [!TIP]
> The Gemeni API uses function calling to automatically format fields. If a query acts unpredictably, refine it such as saying "Search using project key X" to ensure accuracy!
