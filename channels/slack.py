import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

_running = False
_last_message = ""
_msg_lock = threading.Lock()
_state_lock = threading.Lock()

_bot_token = ""
_channel_id = ""
_poll_interval = 10
_bot_user_id = ""
_connected = False
_user_cache = {}
_channel_offsets = {}
_channel_name_cache = {}
_auto_bind_channels = []
_auto_bind_index = 0
_auto_bind_last_refresh = 0.0

_auth_secret = ""
_authenticated_user_id = None
_rate_limit_until = 0.0
_AUTO_BIND_REFRESH_INTERVAL = 300


class _SlackRateLimitError(Exception):
    def __init__(self, retry_after):
        super().__init__(f"Slack rate limited (retry after {retry_after}s)")
        self.retry_after = retry_after


_URL_DISPLAY_RE = re.compile(r"<[^|>\s]+\|([^>]*)>")
_URL_BARE_RE = re.compile(r"<([^>\s]+)>")


def _slack_unwrap(text):
    """Reverse Slack's outgoing auto-formatting so downstream layers see the original text."""
    if not text:
        return text
    text = _URL_DISPLAY_RE.sub(r"\1", text)
    text = _URL_BARE_RE.sub(r"\1", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return text


def _set_last(msg):
    global _last_message
    with _msg_lock:
        if _last_message == "":
            _last_message = msg
        else:
            _last_message = _last_message + " | " + msg


def getLastMessage():
    global _last_message
    with _msg_lock:
        tmp = _last_message
        _last_message = ""
        return tmp


def _set_auth_secret(secret=None):
    global _auth_secret, _authenticated_user_id
    if secret is None:
        secret = os.environ.get("OMEGACLAW_AUTH_SECRET", "")
    with _state_lock:
        _auth_secret = (secret or "").strip()
        _authenticated_user_id = None


def _parse_auth_candidate(msg):
    text = msg.strip()
    lower = text.lower()
    if lower.startswith("auth "):
        return text[5:].strip()
    if lower.startswith("/auth "):
        return text[6:].strip()
    return text


def _channel_label(channel_id):
    with _state_lock:
        label = _channel_name_cache.get(channel_id)
    return label or channel_id


def _is_allowed_message(channel_id, user_id, msg):
    global _authenticated_user_id
    candidate = _parse_auth_candidate(msg)
    with _state_lock:
        if _channel_id and channel_id != _channel_id:
            return "ignore"

        if not _auth_secret:
            if not _channel_id:
                _bind_label = _channel_name_cache.get(channel_id, channel_id)
                print(f"[SLACK] Auto-bound to channel {_bind_label}")
                _set_bound_channel(channel_id)
            return "allow"

        if candidate == _auth_secret:
            if _authenticated_user_id is None:
                _authenticated_user_id = user_id
                _set_bound_channel(channel_id)
                return "auth_bound"
            return "ignore"
        if _authenticated_user_id is None:
            return "ignore"
        return "allow" if user_id == _authenticated_user_id else "ignore"


def _set_bound_channel(channel_id):
    global _channel_id
    _channel_id = channel_id


def _parse_retry_after(value):
    try:
        seconds = int(str(value).strip())
        return max(1, seconds)
    except Exception:
        return 60


def _set_rate_limit_backoff(seconds):
    global _rate_limit_until
    until = time.time() + max(1, int(seconds))
    with _state_lock:
        if until > _rate_limit_until:
            _rate_limit_until = until


def _wait_for_rate_limit_window():
    with _state_lock:
        wait = _rate_limit_until - time.time()
    if wait > 0:
        time.sleep(wait)


def _api_call(method, params=None, timeout=30):
    if not _bot_token:
        raise RuntimeError("Slack adapter not initialized")

    params = params or {}
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=body,
        headers={
            "Authorization": f"Bearer {_bot_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    _wait_for_rate_limit_window()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
            response_headers = response.headers
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry_after = _parse_retry_after(exc.headers.get("Retry-After"))
            _set_rate_limit_backoff(retry_after)
            raise _SlackRateLimitError(retry_after) from exc
        raise

    if not payload.get("ok"):
        err = payload.get("error", f"{method} failed")
        if err == "ratelimited":
            retry_after = _parse_retry_after(response_headers.get("Retry-After"))
            _set_rate_limit_backoff(retry_after)
            raise _SlackRateLimitError(retry_after)
        raise RuntimeError(err)

    return payload


def _get_display_name(user_id):
    with _state_lock:
        cached = _user_cache.get(user_id)
    if cached:
        return cached

    name = user_id
    try:
        payload = _api_call("users.info", {"user": user_id}, timeout=15)
        user = payload.get("user") or {}
        profile = user.get("profile") or {}

        display_name = str(profile.get("display_name", "")).strip()
        real_name = str(profile.get("real_name", "")).strip()
        username = str(user.get("name", "")).strip()

        if display_name:
            name = display_name
        elif real_name:
            name = real_name
        elif username:
            name = username
    except Exception as exc:
        print(f"[SLACK] Could not resolve user {user_id}: {exc}")

    with _state_lock:
        _user_cache[user_id] = name
    return name


def _cache_channel(channel):
    channel_id = str(channel.get("id", "")).strip()
    if not channel_id:
        return
    channel_name = str(channel.get("name", "")).strip()
    label = f"#{channel_name}" if channel_name else channel_id
    with _state_lock:
        _channel_name_cache[channel_id] = label


def _initialize_identity():
    global _bot_user_id
    payload = _api_call("auth.test", timeout=15)
    bot_user_id = str(payload.get("user_id", "")).strip()
    with _state_lock:
        _bot_user_id = bot_user_id


def _validate_channel():
    payload = _api_call("conversations.info", {"channel": _channel_id}, timeout=15)
    channel = payload.get("channel") or {}
    _cache_channel(channel)
    channel_name = str(channel.get("name", "")).strip()
    if channel_name:
        print(f"[SLACK] Channel ready: #{channel_name}")
    else:
        print(f"[SLACK] Channel ready: {_channel_id}")


def _list_joined_channels():
    channels = []
    cursor = ""
    while True:
        params = {
            "types": "public_channel,private_channel",
            "exclude_archived": "true",
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor

        payload = _api_call("conversations.list", params=params, timeout=20)
        for channel in payload.get("channels") or []:
            if not channel.get("is_member"):
                continue
            channel_id = str(channel.get("id", "")).strip()
            if not channel_id:
                continue
            _cache_channel(channel)
            channels.append(channel_id)

        metadata = payload.get("response_metadata") or {}
        cursor = str(metadata.get("next_cursor", "")).strip()
        if not cursor:
            break
    return channels


def _initialize_cursor_for_channel(channel_id):
    try:
        payload = _api_call(
            "conversations.history",
            {"channel": channel_id, "limit": 1},
            timeout=15,
        )
        messages = payload.get("messages") or []
        ts = ""
        if messages:
            ts = str(messages[0].get("ts", "")).strip()
        with _state_lock:
            _channel_offsets[channel_id] = ts
    except Exception as exc:
        print(f"[SLACK] Could not initialize cursor for {_channel_label(channel_id)}: {exc}")


def _initialize_auto_bind_cursors():
    channels = _refresh_auto_bind_channels(force=True)
    if not channels:
        print("[SLACK] Auto-bind waiting: no joined channels visible yet.")
    else:
        print(f"[SLACK] Auto-bind watching {len(channels)} joined channel(s).")


def _refresh_auto_bind_channels(force=False):
    global _auto_bind_channels, _auto_bind_last_refresh, _auto_bind_index
    now = time.time()
    with _state_lock:
        cached = list(_auto_bind_channels)
        last_refresh = _auto_bind_last_refresh

    if (not force) and cached and (now - last_refresh) < _AUTO_BIND_REFRESH_INTERVAL:
        return cached

    channels = _list_joined_channels()
    with _state_lock:
        _auto_bind_channels = channels
        _auto_bind_last_refresh = now
        if _auto_bind_index >= len(channels):
            _auto_bind_index = 0
    return channels


def _next_auto_bind_channel():
    global _auto_bind_index
    with _state_lock:
        if not _auto_bind_channels:
            return ""
        channel_id = _auto_bind_channels[_auto_bind_index]
        _auto_bind_index = (_auto_bind_index + 1) % len(_auto_bind_channels)
    return channel_id


def _poll_channel(channel_id):
    params = {"channel": channel_id, "limit": 15}
    with _state_lock:
        oldest = _channel_offsets.get(channel_id, "")
    if oldest:
        params["oldest"] = oldest
        params["inclusive"] = "false"

    payload = _api_call("conversations.history", params=params, timeout=30)
    messages = payload.get("messages") or []
    if not messages:
        return

    ordered = sorted(messages, key=lambda m: float(m.get("ts", 0.0)))
    max_ts = oldest
    for message in ordered:
        ts = str(message.get("ts", "")).strip()
        if ts:
            max_ts = ts

        # Ignore bot/system messages and process regular user text.
        if message.get("subtype"):
            continue

        text = _slack_unwrap(str(message.get("text", "")).strip())
        user_id = str(message.get("user", "")).strip()
        if not text or not user_id:
            continue

        with _state_lock:
            bot_user_id = _bot_user_id
        if bot_user_id and user_id == bot_user_id:
            continue

        state = _is_allowed_message(channel_id, user_id, text)
        display_name = _get_display_name(user_id)
        if state == "allow":
            _set_last(f"{display_name}: {text}")
        elif state == "auth_bound":
            send_message(f"Authentication successful for {display_name}.")

    if max_ts != oldest:
        with _state_lock:
            _channel_offsets[channel_id] = max_ts


def _poll_loop():
    global _connected
    print("[SLACK] Polling started")

    while _running:
        try:
            with _state_lock:
                bound_channel = _channel_id

            if bound_channel:
                with _state_lock:
                    known = bound_channel in _channel_offsets
                if not known:
                    _initialize_cursor_for_channel(bound_channel)
                    _connected = True
                else:
                    _poll_channel(bound_channel)
            else:
                channels = _refresh_auto_bind_channels()
                if not channels:
                    channels = _refresh_auto_bind_channels(force=True)
                channel_id = _next_auto_bind_channel()
                if channel_id:
                    with _state_lock:
                        known = channel_id in _channel_offsets
                    if not known:
                        _initialize_cursor_for_channel(channel_id)
                        _connected = True
                    else:
                        _poll_channel(channel_id)

            _connected = True
        except _SlackRateLimitError as exc:
            _connected = False
            print(f"[SLACK] Rate limited. Backing off for {exc.retry_after}s.")
        except Exception as exc:
            _connected = False
            print(f"[SLACK] Poll error: {exc}")

        time.sleep(max(1, int(_poll_interval)))

    _connected = False
    print("[SLACK] Polling stopped")


def start_slack(bot_token, channel_id, poll_interval=60, auth_secret=None):
    global _running, _bot_token, _channel_id, _poll_interval, _connected
    global _rate_limit_until, _auto_bind_channels, _auto_bind_index, _auto_bind_last_refresh

    _bot_token = str(bot_token).strip()
    if not _bot_token:
        raise ValueError("SL_BOT_TOKEN is required")

    _channel_id = str(channel_id).strip()

    try:
        _poll_interval = min(60, int(poll_interval))
    except Exception:
        _poll_interval = 60

    with _state_lock:
        _user_cache.clear()
        _channel_offsets.clear()
        _channel_name_cache.clear()
    _auto_bind_channels = []
    _auto_bind_index = 0
    _auto_bind_last_refresh = 0.0
    _rate_limit_until = 0.0
    _connected = False
    _set_auth_secret(auth_secret)
    _initialize_identity()
    if _channel_id:
        _validate_channel()
        _initialize_cursor_for_channel(_channel_id)
    else:
        print("[SLACK] Starting adapter in auto-bind mode (channel not configured).")
        _initialize_auto_bind_cursors()

    _running = True
    print(f"[SLACK] Starting adapter with channel target: {_channel_id or 'auto-bind'}")
    t = threading.Thread(target=_poll_loop, daemon=True)
    t.start()
    return t


def stop_slack():
    global _running
    _running = False


def send_message(text):
    text = str(text).replace("\\n", "\n").replace("\r", "")
    if not text:
        return
    if not _channel_id:
        return

    max_len = 3900
    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        if not chunk:
            continue
        try:
            _api_call("chat.postMessage", {"channel": _channel_id, "text": chunk}, timeout=15)
        except Exception as exc:
            print(f"[SLACK] Send failed: {exc}")
            return
