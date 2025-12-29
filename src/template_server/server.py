"""Discord Auto-Response MCP Server."""

import os
import ssl
import certifi
import asyncio
import threading
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
import discord
from discord import Intents

from .auto_response import AutoResponseManager

# Fix SSL certificate issues on macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Load environment variables
env_loaded = load_dotenv()
print(f"DEBUG: .env file loaded: {env_loaded}")
print(f"DEBUG: DISCORD_TOKEN present: {bool(os.getenv('DISCORD_TOKEN'))}")

# Initialize FastMCP server
mcp = FastMCP("Discord Auto-Response Server")

# Initialize the auto-response manager
response_manager = AutoResponseManager()

# Discord client state
discord_client: Optional[discord.Client] = None
discord_thread: Optional[threading.Thread] = None
discord_loop: Optional[asyncio.AbstractEventLoop] = None
bot_running = False


async def start_bot_async(token: str):
    """Async wrapper to create client and start bot."""
    global discord_client, bot_running
    import aiohttp
    
    print("DEBUG: Starting bot_async inside thread loop")
    
    # Create SSL context and connector inside the running loop
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    intents = Intents.default()
    intents.message_content = True
    
    # Create client with the connector
    client = discord.Client(intents=intents, connector=connector)
    discord_client = client
    
    @client.event
    async def on_ready():
        """Called when the Discord client is ready."""
        print(f"Discord bot logged in as {client.user}")
        print(f"Bot is in {len(client.guilds)} server(s)")
        print("Mention me to chat!")
    
    @client.event
    async def on_message(message: discord.Message):
        """Handle incoming messages."""
        # Log all messages received (debugging)
        print(f"DEBUG: Message received from {message.author} in {message.channel}: '{message.content}'")
        
        if message.author == client.user:
            return
        
        if client.user not in message.mentions:
            return
        
        # Remove the mention from the message content
        content = message.content.replace(f'<@{client.user.id}>', '').strip()
        content = content.replace(f'<@!{client.user.id}>', '').strip()
        
        # Also handle nicknames mention format
        if client.user.display_name in content:
            content = content.replace(f'@{client.user.display_name}', '').strip()
        
        if not content:
            await message.channel.send("안녕하세요! 무엇을 도와드릴까요?")
            return
        
        response = response_manager.find_matching_response(content)
        
        if response:
            await message.channel.send(response)
            print(f"Auto-responded to {message.author}: {response}")
        else:
            await message.channel.send(f"'{content}'에 대한 응답 규칙이 없습니다.")
            print(f"No rule matched: {content}")

    try:
        bot_running = True
        print("DEBUG: Calling client.start()...")
        await client.start(token)
    except Exception as e:
        print(f"Discord bot error: {e}")
    finally:
        bot_running = False
        if not client.is_closed():
            await client.close()


def run_discord_bot_in_thread(token: str):
    """Run the Discord bot in a separate thread."""
    global discord_loop
    
    print("DEBUG: Discord thread function started")
    discord_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(discord_loop)
    
    try:
        discord_loop.run_until_complete(start_bot_async(token))
    except Exception as e:
        print(f"Event loop error: {e}")
    finally:
        print("DEBUG: Closing discord event loop")
        discord_loop.close()


# ============== MCP Tools ==============

@mcp.tool()
async def start_discord_bot(token: Optional[str] = None) -> str:
    """
    Start the Discord bot.
    
    Args:
        token: Discord bot token. If not provided, uses DISCORD_TOKEN from .env
        
    Returns:
        Status message
    """
    global discord_thread, bot_running
    env_val = os.getenv("DISCORD_TOKEN")
    print(f"DEBUG: start_discord_bot tool called. Argument token: '{token}', Env DISCORD_TOKEN: '{env_val[:5] if env_val else 'None'}...' (len={len(env_val) if env_val else 0})")
    
    if bot_running:
        return "Discord bot is already running."
    
    bot_token = token or env_val
    
    if bot_token:
        # Step-by-step cleaning and logging
        token_clean = bot_token.strip().strip('"').strip("'")
        prefix = token_clean[:10] if len(token_clean) > 20 else "INVALID"
        print(f"DEBUG: Processing token. Cleaned length: {len(token_clean)}, Prefix: {prefix}...")
        bot_token = token_clean
    
    if not bot_token or bot_token == "your_discord_bot_token_here" or len(bot_token) < 20:
        err_msg = f"Error: Invalid/Missing Discord token in .env (Length: {len(bot_token) if bot_token else 0})"
        print(f"DEBUG: {err_msg}")
        return err_msg
    
    discord_thread = threading.Thread(
        target=run_discord_bot_in_thread,
        args=(bot_token,),
        daemon=True
    )
    discord_thread.start()
    print("DEBUG: Thread started for Discord bot")
    
    # Wait asynchronously to give the bot time to connect
    await asyncio.sleep(2)
    
    if bot_running:
        return "Discord bot started successfully!"
    return "Discord bot is starting in the background. Check MCP server logs for status."


@mcp.tool()
def stop_discord_bot() -> str:
    """Stop the Discord bot."""
    global discord_client, discord_loop, bot_running
    
    if not bot_running:
        return "Discord bot is not running."
    
    if discord_client and discord_loop:
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
    """Get the current status of the Discord bot."""
    if not bot_running:
        return "Bot is not running."
    
    if discord_client and discord_client.user:
        return f"Bot is running as: {discord_client.user} (ID: {discord_client.user.id})"
    
    return "Bot is starting or not fully connected."


@mcp.tool()
def add_auto_response_rule(
    trigger: str,
    response: str,
    match_type: str = "contains"
) -> str:
    """
    Add a new auto-response rule.
    """
    if match_type not in ["exact", "contains", "startswith", "regex"]:
        return f"Error: Invalid match_type '{match_type}'. Use: exact, contains, startswith, or regex"
    
    rule = response_manager.add_rule(
        trigger=trigger,
        response=response,
        match_type=match_type
    )
    
    return f"Rule added! ID: {rule.id}"


@mcp.tool()
def remove_auto_response_rule(rule_id: str) -> str:
    """Remove a rule by ID."""
    if response_manager.remove_rule(rule_id):
        return f"Rule {rule_id} removed."
    return f"Error: Rule {rule_id} not found."


@mcp.tool()
def list_auto_response_rules() -> str:
    """List all rules."""
    rules = response_manager.get_rules()
    if not rules:
        return "No auto-response rules configured."
    
    result = []
    for rule in rules:
        status = "✓" if rule.enabled else "✗"
        result.append(
            f"[{status}] ID: {rule.id}\n"
            f"    Trigger ({rule.match_type}): \"{rule.trigger}\"\n"
            f"    Response: \"{rule.response}\""
        )
    return "\n\n".join(result)


@mcp.tool()
def toggle_auto_response_rule(rule_id: str) -> str:
    """Toggle a rule's status."""
    new_status = response_manager.toggle_rule(rule_id)
    if new_status is None:
        return f"Error: Rule {rule_id} not found."
    return f"Rule {rule_id} is now {'enabled' if new_status else 'disabled'}."


@mcp.tool()  
def clear_all_rules() -> str:
    """Clear all rules."""
    count = response_manager.clear_all_rules()
    return f"Cleared {count} rule(s)."


def main():
    """Run the MCP server."""
    mcp.run(transport="sse", port=9002)


if __name__ == "__main__":
    main()
