import os
import json
import logging
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

def get_openrouter_client():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def build_jql_tool_declaration() -> list:
    """
    Since we know the server provides 'search_jira_issues', we can explicitly
    define it for the LLM to use via standard OpenAI schema format.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_jira_issues",
                "description": "Search Jira for issues using a given JQL (Jira Query Language) string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "The Jira Query Language string to search issues with."
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of issues to return. Default is 100."
                        }
                    },
                    "required": ["jql"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_all_jira_tickets",
                "description": "Fetch all Jira tickets without any specific JQL filtering. Use this when the user just asks for 'all tickets', 'all issues', or a general dump without criteria.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of issues to return. Default is 100."
                        }
                    },
                    "required": []
                }
            }
        }
    ]

def analyze_prompt_and_get_tool_call(prompt: str) -> dict | None:
    """
    Submits the prompt to OpenRouter with the available tool.
    Returns a dictionary with the tool name and arguments if the model 
    decided to call a tool, otherwise None.
    """
    client = get_openrouter_client()
    
    # We default back to gemini-2.5-pro via openrouter mapping
    model_name = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-pro")
        
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a Jira expert assistant. Converts natural language queries into JQL (Jira Query Language) and calls the search function. Assume 'project' fields unless specified otherwise."},
                {"role": "user", "content": prompt}
            ],
            tools=build_jql_tool_declaration(),
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            function_call = message.tool_calls[0].function
            
            try:
                args_dict = json.loads(function_call.arguments)
            except json.JSONDecodeError:
                args_dict = {}
                
            return {
                "name": function_call.name,
                "args": args_dict
            }
            
        logging.info("Model did not choose to call a tool.")
        return None
        
    except Exception as e:
        logging.error(f"LLM Error: {e}")
        return None
