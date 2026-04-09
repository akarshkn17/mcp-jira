# Jira MCP Project Context

This file serves as the definitive reference context for the **Jira Model Context Protocol (MCP)** integration codebase. Provide this file to any LLM, AI Agent, or developer to instantly give them full architectural context of how the project is built, the reasoning behind existing design choices, and how to extend it.

---

## 1. Project Goal
The goal of this project is to allow a user to ask for Jira tickets in **Natural Language** (e.g., "Fetch all open bugs assigned to me"), translate that intent into Atlassian's **Jira Query Language (JQL)**, execute the query securely through a formal MCP Server, and seamlessly export the flattened results to a local CSV file.

## 2. Global Architecture
The tool uses the official **Model Context Protocol (MCP)** standard to separate capability logic from the client orchestration. By using MCP, the server can be reused independently by *any* compatible agent, while the client dictates the CLI interface logic. Communication happens over entirely local Standard Input / Output (`stdio`) streams.

### A. The Client (`jira_client/`)
- **`client.py`**: The CLI entry point. It orchestrates the flow:
  1. Captures the user's Natural Language prompt.
  2. Passes the prompt to the `llm_orchestrator` to generate a tool-call request mapping to defined capabilities.
  3. Spins up the background Python process targeting `jira_server.server` over MCP `stdio`.
  4. Triggers the returned tool command.
  5. Offloads the returned JSON string array to the `csv_exporter`.
- **`llm_orchestrator.py`**: Handles cognitive translation. **We are using OpenRouter (OpenAI SDK wrapper)** instead of the raw Gemini payload schema. It forces the external AI model via function calling to return strict arguments (like `max_results` or specific `jql`).
- **`csv_exporter.py`**: Iterates over the heavily-flattened server response to dynamically map generic strings to CSV headers.

### B. The Server (`jira_server/`)
- **`server.py`**: Binds the capabilities using `FastMCP`. Exposes tools via the `@mcp.tool()` decorator:
  - `search_jira_issues(jql, max_results)`
  - `fetch_all_jira_tickets(max_results)`
- **`jira_api.py`**: The dedicated Provider module executing HTTP workflows. Handles authentication parsing and error handling against generic `requests.exceptions.HTTPError`.

---

## 3. Important Design Decisions & Quirks (MUST READ)

When extending or modifying this project, keep the following context in mind to avoid regressions:

1. **Jira API Endpoints (`POST` vs `GET`)**:
   - The Atlassian `GET /rest/api/3/search` path is generally deprecated or strictly punishes JQL passing over URL encoding.
   - **We strictly use `POST /rest/api/3/search`** or `POST /rest/api/3/search/jql`. By sending variables as a strict JSON `{"jql": "...", "fields": [...]}` payload body, we solve catastrophic parsing errors.
   - `fields` in a POST array MUST be a python List (e.g. `["summary", "status"]`), *not* a comma-separated string like the legacy GET path.

2. **Jira "Unbounded JQL" Protection**:
   - Modern Jira Cloud immediately rejects broad tool requests that look like `ORDER BY created DESC` or `""` empty queries with a HTTP 400 error (`Unbounded JQL queries are not allowed`). 
   - To bypass this generically, generic tool queries (like `fetch_all_jira_tickets`) secretly inject `project IS NOT EMPTY ORDER BY created DESC` which forces Jira to execute the query without kicking back safety bounds.

3. **HTTP Error Truncation**:
   - Without explicit handling, `response.raise_for_status()` will swallow Jira JSON error responses. In `jira_api.py`, we explicitly grab `response.text` before returning so the server securely outputs Jira's *actual* restriction warnings (e.g. 403 Forbidden payload vs generic `requests` error string).

4. **Environment Variables**:
   - Dependencies rely on `python-dotenv`.
   - `JIRA_API_TOKEN` is a Personal Access Token created by the user, **not OAuth**.
   - Current LLM key acts under `OPENROUTER_API_KEY`.
   - Ensure the server process inherits the parent directory in `env_copy` inside `client.py` or MCP stdio will silently strip authentication limits.

## 4. How to Extend / Add Features

1. **Adding a New Jira Tool** (e.g., `create_jira_ticket`):
   - Open `jira_server/server.py` and write a new function `@mcp.tool() def create_ticket(...)`.
   - Add the relative HTTP request into `jira_api.py`.
   - Open `jira_client/llm_orchestrator.py` and manually append the new tool schema array inside `build_jql_tool_declaration()`.
   - Add explicit logic in `client.py` parsing if `selected_tool == "create_ticket"`.

2. **Adding a New System (e.g., GitHub)**:
   - Create a `github_server/` package mimicking the `FastMCP` architecture.
   - Inside `client.py`, you must update the LLM Orchestrator to see GitHub tool schemas and intelligently spawn whichever MCP process server binary solves that distinct domain.
