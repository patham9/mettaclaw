"""
CLI Channel - Direct terminal interaction for MeTTaClaw.

Provides a simple command-line interface for interacting with the agent.
Supports both interactive mode and piped input.
"""
import sys
import threading
import os

_running = False
_connected = False
_last_message = ""
_msg_lock = threading.Lock()
_prompt = "> "

def _getch():
    """Get a single character from stdin (cross-platform)."""
    try:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch
    except ImportError:
        # Windows
        import msvcrt
        return msvcrt.getch().decode('utf-8', errors='ignore')

def start_cli(prompt="> ", welcome_msg=None):
    """Start CLI channel with optional welcome message."""
    global _running, _connected, _prompt
    _running = True
    _connected = True
    _prompt = prompt
    
    if welcome_msg:
        print(welcome_msg)
    
    return True

def stop_cli():
    """Stop CLI channel."""
    global _running, _connected
    _running = False
    _connected = False

def getLastMessage():
    """Get message from stdin (non-blocking check)."""
    global _last_message
    
    # For non-interactive (piped) input
    if not sys.stdin.isatty():
        try:
            line = sys.stdin.readline()
            if line:
                return line.rstrip('\n')
        except:
            pass
        return ""
    
    # For interactive mode, we need to check if input is available
    # This is a simplified approach - just returns empty if no input
    # The main loop handles the blocking read
    return ""

def send_message(text):
    """Send a message to stdout."""
    with _msg_lock:
        print(text)
        if _running and sys.stdin.isatty():
            print(_prompt, end='', flush=True)

def is_connected():
    """Check if CLI is connected."""
    return _connected and _running

def set_prompt(prompt):
    """Set the CLI prompt."""
    global _prompt
    _prompt = prompt

def get_prompt():
    """Get the current prompt."""
    return _prompt

def readline():
    """Blocking read a line from stdin with prompt."""
    try:
        if sys.stdin.isatty():
            print(_prompt, end='', flush=True)
        line = sys.stdin.readline()
        return line.rstrip('\n') if line else ""
    except EOFError:
        return ""
    except KeyboardInterrupt:
        return ""

# Alternative input method for interactive sessions
_input_buffer = ""
_input_ready = threading.Event()

def input_thread():
    """Background thread for input reading."""
    global _input_buffer, _running
    while _running:
        try:
            if sys.stdin.isatty():
                print(_prompt, end='', flush=True)
            line = sys.stdin.readline()
            if line:
                _input_buffer = line.rstrip('\n')
                _input_ready.set()
            else:
                break
        except:
            break

def start_input_thread():
    """Start the input reader thread."""
    t = threading.Thread(target=input_thread, daemon=True, name="CLI-Input")
    t.start()
    return t

def get_message_blocking(timeout=None):
    """Get message with optional timeout."""
    if _input_ready.wait(timeout):
        _input_ready.clear()
        msg = _input_buffer
        _input_buffer = ""
        return msg
    return ""
