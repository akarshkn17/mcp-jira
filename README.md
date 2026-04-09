# Jira MCP Client and Server

A complete Model Context Protocol (MCP) integration that allows users to fetch Jira tickets using natural language. It translates user intents into JQL using GenAI (Gemini), calls a local MCP Jira server to execute the search, flattens the result, and exports it to CSV.

## Features
- **MCP Server (`jira_server/`)**: Built using `FastMCP`. Exposes the `search_jira_issues` tool.
- **MCP Client (`jira_client/`)**: Evaluates natural language queries using `google-genai` (Gemini API) to formulate JQL and uses the official `mcp` Python client to query the MCP server over standard Python stdio.
- **CSV Exporter**: Flattens nested Jira JSON responses into an easy-to-use CSV.

## Prerequisites
- Python 3.10+
- The `uv` package manager

## Setup

1. **Install Dependencies**
   The project was configured with `uv`. To ensure everything is set up:
   ```bash
   uv sync
   ```
   Or if you install dynamically via local python:
   ```bash
   python -m uv add mcp requests google-genai python-dotenv
   ```

2. **Configure Environment Variables**
   Rename `.env.example` to `.env` and fill in your details:
   ```env
   JIRA_BASE_URL=https://<your-domain>.atlassian.net
   JIRA_EMAIL=<your-atlassian-email>
   JIRA_API_TOKEN=<your-jira-api-token>
   OPENROUTER_API_KEY=<your-openrouter-key>
   OPENROUTER_MODEL=google/gemini-2.5-pro
   ```

## Usage

You can run the natural language CLI client. Since we are using an isolated virtual environment (`.venv`), be sure to activate it or use the python interpreter directly from it:

```bash
.venv/Scripts/python -m jira_client.client "Fetch all open bugs assigned to me"
```

To export to a custom CSV file:
```bash
.venv/Scripts/python -m jira_client.client "Fetch all the offboarding tickets from the last 7 days" --output offboarding.csv
```

## Architecture

1. **User Input** -> CLI argument.
2. **LLM Orchestrator** -> Sends system instructions and `search_jira_issues` Tool definition to Gemini.
3. **MCP Client** -> Connects to `jira_server.server` over stdio if Gemini requested a Jira search.
4. **MCP Server** -> Processes the JQL against Jira API `/rest/api/3/search` via requests.
5. **CSV Exporter** -> Receives structured data from Client and saves it.
