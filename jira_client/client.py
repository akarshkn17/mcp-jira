import sys
import asyncio
import json
import logging
import os
from argparse import ArgumentParser

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

from .llm_orchestrator import analyze_prompt_and_get_tool_call
from .csv_exporter import export_to_csv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv()

async def main():
    parser = ArgumentParser(description="Jira MCP Client via Gemini")
    parser.add_argument("query", type=str, help="Natural language query for Jira")
    parser.add_argument("--output", type=str, default="export.csv", help="Output CSV path")
    args = parser.parse_args()

    # 1. LLM identifies intent and extracts JQL tool call
    logging.info("Analyzing query with Gemini...")
    tool_call = analyze_prompt_and_get_tool_call(args.query)

    if not tool_call or tool_call["name"] not in ["search_jira_issues", "fetch_all_jira_tickets"]:
        logging.error("Gemini failed to generate a recognized Jira query tool call.")
        return

    selected_tool = tool_call["name"]
    jql = tool_call["args"].get("jql", "") if selected_tool == "search_jira_issues" else "ORDER BY created DESC"
    logging.info(f"Selected Tool: {selected_tool}")
    if selected_tool == "search_jira_issues":
        logging.info(f"Generated JQL: {jql}")

    # 2. Setup MCP Client communicating via stdio to the local server
    # We pass the full path to the server module since we are running as a package
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jira_server.server"],
        env=os.environ.copy() # important: inherit env so server has API keys
    )

    env_copy = os.environ.copy()
    env_copy["PYTHONPATH"] = app_dir

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jira_server.server"],
        env=env_copy
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 3. Execute MCP Tool
                logging.info(f"Executing MCP Tool '{selected_tool}' on Server...")
                # The MCP sdk requires arguments as dict mapping strings to any
                result = await session.call_tool(selected_tool, arguments=tool_call["args"])
                
                if not result.content or len(result.content) == 0:
                    logging.error("MCP Server returned an empty response.")
                    return
                    
                server_response_text = result.content[0].text
                try:
                    server_data = json.loads(server_response_text)
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse server JSON response: {server_response_text}")
                    return
                    
                if "error" in server_data:
                    logging.error(f"Server Error: {server_data['error']}")
                    return
                    
                issues = server_data.get("issues", [])
                total_found = server_data.get("total_found", 0)
                
                logging.info(f"Jira query successful: {len(issues)} returned out of {total_found} total.")
                
                # 4. Export to CSV
                if export_to_csv(issues, args.output):
                    logging.info("\n--- Success ---")
                    logging.info(f"Query    : '{args.query}'")
                    logging.info(f"JQL      : {jql}")
                    logging.info(f"Exported : {len(issues)} issues to {args.output}")
                else:
                    logging.error("Failed to export to CSV.")
    except Exception as e:
        logging.error(f"MCP Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
