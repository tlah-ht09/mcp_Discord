"""Discord Auto-Response MCP Server."""

import os
import asyncio
import threading
from typing import Optional
from dataclasses import asdict

from dotenv import load_dotenv
from fastmcp import FastMCP
import discord

from .auto_response import AutoResponseManager

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Discord Auto-Response Server")

# Initialize the auto-response manager
response_manager = AutoResponseManager()

# Discord client state
discord_client: Optional[discord.Client] = None
discord_thread: Optional[threading.Thread] = None
discord_loop: Optional[asyncio.AbstractEventLoop] = None
bot_running = False


def create_discord_client() -> discord.Client:
    """Create and configure the Discord client."""
    client = discord.Client()
    
    @client.event
    async def on_ready():
        """Called when the Discord client is ready."""
        print(f"Discord bot logged in as {client.user}")
    
    @client.event
    async def on_message(message: discord.Message):
        """Handle incoming messages."""
        # Ignore messages from ourselves
        if message.author == client.user:
            return
        
        # Only respond to DMs (Direct Messages)
        if not isinstance(message.channel, discord.DMChannel):
            return
        
        # Check if the author is in our rules
        author_id = str(message.author.id)
        response = response_manager.find_matching_response(author_id, message.content)
        
        if response:
            try:
                await message.channel.send(response)
                print(f"Auto-responded to {message.author}: {response}")
            except Exception as e:
                print(f"Failed to send auto-response: {e}")
    
    return client


def run_discord_bot_in_thread(token: str):
    """Run the Discord bot in a separate thread."""
    global discord_client, discord_loop, bot_running
    
    discord_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(discord_loop)
    
    discord_client = create_discord_client()
    
    try:
        bot_running = True
        discord_loop.run_until_complete(discord_client.start(token))
    except Exception as e:
        print(f"Discord bot error: {e}")
    finally:
        bot_running = False
        if discord_client:
            discord_loop.run_until_complete(discord_client.close())


# ============== MCP Tools ==============

@mcp.tool()
def start_discord_bot(token: Optional[str] = None) -> str:
    """
    Start the Discord bot for auto-responses.
    
    Args:
        token: Discord user token. If not provided, uses DISCORD_TOKEN from .env
        
    Returns:
        Status message
    """
    global discord_thread, bot_running
    
    if bot_running:
        return "Discord bot is already running."
    
    # Get token from parameter or environment
    bot_token = token or os.getenv("DISCORD_TOKEN")
    
    if not bot_token or bot_token == "your_discord_user_token_here":
        return "Error: Discord token not provided. Set DISCORD_TOKEN in .env or provide token parameter."
    
    # Start bot in a separate thread
    discord_thread = threading.Thread(
        target=run_discord_bot_in_thread,
        args=(bot_token,),
        daemon=True
    )
    discord_thread.start()
    
    # Wait a bit for the bot to start
    import time
    time.sleep(2)
    
    if bot_running:
        return "Discord bot started successfully!"
    return "Discord bot is starting... Check logs for status."


@mcp.tool()
def stop_discord_bot() -> str:
    """
    Stop the Discord bot.
    
    Returns:
        Status message
    """
    global discord_client, discord_loop, bot_running
    
    if not bot_running:
        return "Discord bot is not running."
    
    if discord_client and discord_loop:
        # Schedule the client to close
        future = asyncio.run_coroutine_threadsafe(
            discord_client.close(),
            discord_loop
        )
        try:
            future.result(timeout=5)
        except Exception as e:
            return f"Error stopping bot: {e}"
    
    bot_running = False
    return "Discord bot stopped."


@mcp.tool()
def get_bot_status() -> str:
    """
    Get the current status of the Discord bot.
    
    Returns:
        Bot status information
    """
    if not bot_running:
        return "Bot is not running."
    
    if discord_client and discord_client.user:
        return f"Bot is running as: {discord_client.user} (ID: {discord_client.user.id})"
    
    return "Bot is starting or not fully connected."


@mcp.tool()
def add_auto_response_rule(
    friend_id: str,
    trigger: str,
    response: str,
    friend_name: str = "",
    match_type: str = "contains"
) -> str:
    """
    Add a new auto-response rule.
    
    Args:
        friend_id: Discord user ID of the friend
        trigger: Message trigger (what to look for)
        response: Auto-response message to send
        friend_name: Optional friendly name for the friend
        match_type: How to match the trigger - "exact", "contains", "startswith", or "regex"
        
    Returns:
        Confirmation message with rule ID
    """
    if match_type not in ["exact", "contains", "startswith", "regex"]:
        return f"Error: Invalid match_type '{match_type}'. Use: exact, contains, startswith, or regex"
    
    rule = response_manager.add_rule(
        friend_id=friend_id,
        trigger=trigger,
        response=response,
        friend_name=friend_name,
        match_type=match_type
    )
    
    return f"Rule added successfully! ID: {rule.id}"


@mcp.tool()
def remove_auto_response_rule(rule_id: str) -> str:
    """
    Remove an auto-response rule by its ID.
    
    Args:
        rule_id: The unique ID of the rule to remove
        
    Returns:
        Confirmation message
    """
    if response_manager.remove_rule(rule_id):
        return f"Rule {rule_id} removed successfully."
    return f"Error: Rule with ID {rule_id} not found."


@mcp.tool()
def list_auto_response_rules(friend_id: Optional[str] = None) -> str:
    """
    List all auto-response rules.
    
    Args:
        friend_id: Optional - filter rules by friend ID
        
    Returns:
        List of rules as formatted string
    """
    rules = response_manager.get_rules(friend_id)
    
    if not rules:
        if friend_id:
            return f"No rules found for friend ID: {friend_id}"
        return "No auto-response rules configured."
    
    result = []
    for rule in rules:
        status = "✓" if rule.enabled else "✗"
        name_str = f" ({rule.friend_name})" if rule.friend_name else ""
        result.append(
            f"[{status}] ID: {rule.id}\n"
            f"    Friend: {rule.friend_id}{name_str}\n"
            f"    Trigger ({rule.match_type}): \"{rule.trigger}\"\n"
            f"    Response: \"{rule.response}\""
        )
    
    return "\n\n".join(result)


@mcp.tool()
def toggle_auto_response_rule(rule_id: str) -> str:
    """
    Toggle a rule's enabled/disabled status.
    
    Args:
        rule_id: The unique ID of the rule to toggle
        
    Returns:
        New status of the rule
    """
    new_status = response_manager.toggle_rule(rule_id)
    
    if new_status is None:
        return f"Error: Rule with ID {rule_id} not found."
    
    status_str = "enabled" if new_status else "disabled"
    return f"Rule {rule_id} is now {status_str}."


@mcp.tool()  
def clear_all_rules() -> str:
    """
    Clear all auto-response rules. Use with caution!
    
    Returns:
        Confirmation message
    """
    count = response_manager.clear_all_rules()
    return f"Cleared {count} rule(s)."


@mcp.tool()
def get_friend_list() -> str:
    """
    Get the list of Discord friends (requires bot to be running).
    
    Returns:
        List of friends with their IDs
    """
    if not bot_running or not discord_client:
        return "Error: Discord bot is not running. Start it with start_discord_bot first."
    
    if not discord_client.user:
        return "Error: Bot is not fully connected yet."
    
    try:
        friends = discord_client.user.friends if hasattr(discord_client.user, 'friends') else []
        
        if not friends:
            return "No friends found or friends list is not accessible."
        
        result = []
        for friend in friends:
            result.append(f"{friend.name}#{friend.discriminator} (ID: {friend.id})")
        
        return "Friends:\n" + "\n".join(result)
    except Exception as e:
        return f"Error getting friends list: {e}"


def main():
    """Run the MCP server."""
    # Run the server with SSE transport for HTTP access
    mcp.run(transport="sse", port=9001)


if __name__ == "__main__":
    main()
