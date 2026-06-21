# needs    pip install discord.py

import discord
import asyncio
import threading
from typing import Optional
import os
import queue # Added for thread-safe message handling

# ==========================================
# 1. Global State & Functions
# ==========================================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0)) # Note: Discord channel IDs are integers, not strings!

# Using a Queue to ensure no messages are lost during race conditions
_msg_queue = queue.Queue()

_lastSent = None

def _set_last(msg):
    _msg_queue.put(msg)

def getLastMessage():
    # Drain all pending messages into a single string
    msgs = []
    while not _msg_queue.empty():
        msgs.append(_msg_queue.get())
    
    tmp = ' | '.join(msgs)
    
    # verbose debug
    if tmp != '':
        print(f"received   message={tmp}")
    
    return tmp

# Global variables to hold the Discord client and its event loop
_discord_client: Optional[discord.Client] = None
_bot_loop: Optional[asyncio.AbstractEventLoop] = None

def send_message(content: str):
    """Global function to send a message from the main thread."""
    
    global _lastSent
    
    # HACK to avoid double send
    if content == _lastSent:
        return # ignore the same message because messages are duplicated with the fix on MeTTa side
    
    _lastSent = content
    
    
    # rewrite from MeTTa to ususual string
    content = content.replace('_apostrophe_', "'")
    content = content.replace('\\n', "\n") # FIXED: Escaped backslash-n to actual newline
    
    # verbose debug
    print(f"send channel {CHANNEL_ID}  message={content}")
    
    if _discord_client is None or _bot_loop is None:
        print("[!] Discord client is not running yet.")
        return
    
    # Define the async send task
    async def _send():
        try:
            # We use fetch_channel to ensure we get the channel even if not in cache
            channel = _discord_client.get_channel(CHANNEL_ID) or await _discord_client.fetch_channel(CHANNEL_ID)
            if channel:
                await channel.send(content)
                print("[*] Message successfully sent to Discord!")
            else:
                print(f"[!] Failed to send: Could not find channel {CHANNEL_ID}")
        except Exception as e:
            print(f"[!!!] Discord API Error while sending: {e}") # THIS WILL REVEAL HIDDEN ERRORS

    # Safely schedule the send task on the background thread's event loop
    asyncio.run_coroutine_threadsafe(_send(), _bot_loop)

"""
# more debugging
def send_message(content: str):
#     if content == _lastSent:
#         return True # ignore the same message because messages are duplicated with the fix on MeTTa side
#     
#     _lastSent = content
    
    
    # rewrite from MeTTa to ususual string
    content = content.replace('_apostrophe_', "'")
    content = content.replace('\\n', "\n") # FIXED: Escaped backslash-n to actual newline
    
    
    
    print(f"Debug: Attempting to send to {CHANNEL_ID}")
    if _discord_client is None:
        print("Debug: Client is NONE!")
        return False
        
    async def _send():
        try:
            print("Debug: Fetching channel...")
            channel = await _discord_client.fetch_channel(CHANNEL_ID)
            print(f"Debug: Channel fetched: {channel}")
            await channel.send(content)
            print("Debug: Send successful!")
        except Exception as e:
            print(f"Debug: EXCEPTION! {type(e).__name__}: {e}")

    future = asyncio.run_coroutine_threadsafe(_send(), _bot_loop)
    # Block slightly to see if it finishes
    try:
        future.result(timeout=5)
    except Exception as e:
        print(f"Debug: Future failed with: {e}")
    
    return True
"""

"""
def send_message(content: str):
    # Sanitize content
    content = content.replace('_apostrophe_', "'").replace('\\n', "\n")
    
    if _discord_client is None or _bot_loop is None:
        print("[!] Bot not initialized.")
        return False

    async def _send():
        try:
            channel = _discord_client.get_channel(CHANNEL_ID)
            if not channel:
                channel = await _discord_client.fetch_channel(CHANNEL_ID)
            
            if channel:
                await channel.send(content)
            else:
                print(f"[!] Channel {CHANNEL_ID} not found.")
        except Exception as e:
            print(f"[!!!] Error sending: {e}")
"""

# ==========================================
# 2. Background Thread Logic (Receive)
# ==========================================
def _run_discord_bot():
    """
    This replaces your 'loop' function. It runs the discord.py 
    WebSocket client in the background thread.
    """
    global _discord_client, _bot_loop
    
    _bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_bot_loop)
    
    intents = discord.Intents.default()
    intents.message_content = True
    #intents.guilds = True
    
    _discord_client = discord.Client(intents=intents)
    
    @_discord_client.event
    async def on_ready():
        print(f"[*] Receive thread active. Listening for messages as {_discord_client.user}...")
        
    @_discord_client.event
    async def on_message(message: discord.Message):
        if message.author == _discord_client.user:
            return
            
        if message.channel.id == CHANNEL_ID:
            content = message.content or "[No text / Attachment only]"
            print(f'DISCORD: recv msg={content}') # DEBUG
            _set_last(f'{message.author} : {content}')
    
    # Run the client in a loop to handle disconnections
    async def start_and_reconnect():
        while True:
            try:
                await _discord_client.start(TOKEN)
            except Exception as e:
                print(f"[!] Discord thread error: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    _bot_loop.run_until_complete(start_and_reconnect())

# ==========================================
# 3. Execution / Main Thread
# ==========================================
def start_discord():
    """Starts the Discord bot in a background thread."""
    
    print(f"My Channel ID is: {CHANNEL_ID}") # DEBUG
    
    listener_thread = threading.Thread(
        target=_run_discord_bot,
        daemon=True
    )
    listener_thread.start()
    return listener_thread

if __name__ == "__main__":
    start_discord()
    
    print("Type a message and press Enter to send it. Type 'quit' to exit.")
    print("Type 'read' to print the last received messages.")
    
    while True:
        text_to_send = input()
        
        if text_to_send.lower() == 'quit':
            print("Exiting...")
            break
            
        elif text_to_send.lower() == 'read':
            msgs = getLastMessage()
            print(f"Stored messages: {msgs if msgs else 'None'}")
            
        elif text_to_send.strip():
            send_message(text_to_send)
