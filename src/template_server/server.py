"""MCP Server Template."""

import os
from typing import Any
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP server
# Change "MCP Template Server" to your server name
mcp = FastMCP("MCP Template Server")

@mcp.tool()
def hello_world(name: str = "World") -> str:
    """
    A simple example tool that greets the user.
    
    Args:
        name: The name to greet
        
    Returns:
        A greeting message
    """
    return f"Hello, {name}!"

@mcp.tool()
def echo(message: str) -> str:
    """
    Echo back the message.
    
    Args:
        message: The message to echo
        
    Returns:
        The same message
    """
    return f"Echo: {message}"

def main():
    """Run the MCP server."""
    # Run the server with SSE transport for HTTP access
    # You can configure the port here or via environment variables if you implement that logic
    mcp.run(transport="sse", port=9001)

if __name__ == "__main__":
    main()
