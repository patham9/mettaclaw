"""
EmbodimentBus - Multi-channel abstraction for MeTTaClaw.

Provides a unified interface for multiple communication channels (IRC, CLI, etc.).
Each channel must implement the Embodiment interface:
- start(channel, server, port, nick) or start(prompt, welcome) - Initialize the channel
- stop() - Shutdown the channel
- getLastMessage() - Get last message (non-blocking)
- send_message(text) - Send message
- is_connected() - Check connection status

Channels are registered and messages are aggregated via getNextMessage().
"""
import threading
from typing import Dict, List, Optional

# Global state
_channels: Dict[str, object] = {}
_active_channel: Optional[str] = None
_running = False

def register_channel(name: str, channel_module):
    """Register a communication channel."""
    _channels[name] = channel_module

def unregister_channel(name: str):
    """Unregister a channel."""
    if name in _channels:
        del _channels[name]

def start_irc(channel="#metta", server="irc.libera.chat", port=6667, nick="mettaclaw"):
    """Start IRC channel."""
    global _active_channel, _running
    try:
        import irc
        register_channel('irc', irc)
        irc.start_irc(channel, server, int(port), nick)
        _active_channel = 'irc'
        _running = True
        return True
    except Exception as e:
        print(f"Failed to start IRC: {e}")
        return False

def start_cli(prompt="> ", welcome_msg=None):
    """Start CLI channel."""
    global _active_channel, _running
    try:
        import cli
        register_channel('cli', cli)
        cli.start_cli(prompt=prompt, welcome_msg=welcome_msg)
        _active_channel = 'cli'
        _running = True
        # Start input thread for CLI
        cli.start_input_thread()
        return True
    except Exception as e:
        print(f"Failed to start CLI: {e}")
        return False

def stop_channel(name: str = None):
    """Stop a specific channel or all channels."""
    global _running
    if name:
        channel = _channels.get(name)
        if channel:
            stop_func = getattr(channel, 'stop_irc', None) or getattr(channel, 'stop_cli', None) or getattr(channel, 'stop', None)
            if stop_func:
                stop_func()
    else:
        _running = False
        for ch_name, channel in _channels.items():
            try:
                stop_func = getattr(channel, 'stop_irc', None) or getattr(channel, 'stop_cli', None) or getattr(channel, 'stop', None)
                if stop_func:
                    stop_func()
            except:
                pass

def stop_all():
    """Stop all channels."""
    stop_channel()

def getNextMessage() -> str:
    """Get the next message from any channel (FIFO order)."""
    # Check CLI first (it's usually more responsive)
    for name in ['cli', 'irc']:  # Priority order
        channel = _channels.get(name)
        if channel:
            try:
                # For CLI, use blocking read with small timeout
                if name == 'cli' and hasattr(channel, 'get_message_blocking'):
                    msg = channel.get_message_blocking(timeout=0.1)
                    if msg:
                        return msg
                else:
                    get_func = getattr(channel, 'getLastMessage', None)
                    if get_func:
                        msg = get_func()
                        if msg:
                            return msg
            except:
                pass
    return ""

def receive_all() -> str:
    """MeTTa integration: Get next message from any channel."""
    return getNextMessage()

def broadcast(text: str):
    """Send message to all connected channels."""
    for name, channel in _channels.items():
        try:
            send_func = getattr(channel, 'send_message', None) or getattr(channel, 'send', None)
            if send_func:
                connected_func = getattr(channel, 'is_connected', None)
                if connected_func is None or connected_func():
                    send_func(text)
        except Exception as e:
            print(f"Error sending to {name}: {e}")

def send_all(text: str):
    """MeTTa integration: Send to all channels."""
    broadcast(text)
    return None

def send_to(channel_name: str, text: str):
    """Send message to a specific channel."""
    channel = _channels.get(channel_name)
    if channel:
        try:
            send_func = getattr(channel, 'send_message', None) or getattr(channel, 'send', None)
            if send_func:
                send_func(text)
        except Exception as e:
            print(f"Error sending to {channel_name}: {e}")

def get_active_channels() -> List[str]:
    """Get list of connected channels."""
    active = []
    for name, channel in _channels.items():
        try:
            connected_func = getattr(channel, 'is_connected', None)
            if connected_func is None or connected_func():
                active.append(name)
        except:
            pass
    return active

def get_active_channel() -> Optional[str]:
    """Get the primary active channel name."""
    return _active_channel

def is_running() -> bool:
    """Check if embodiment bus is running."""
    return _running
