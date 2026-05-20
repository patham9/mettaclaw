"""Pytest fixtures for the Telegram test suite.

Two transports, selected via `--transport=mock|live` (default `mock`):

- `mock` — `MockTelegramServer` on tcp:9766. Agent's Telegram adapter is
  pointed at it via `TG_API_BASE=http://172.17.0.1:9766`. Fully offline.
- `live` — `RealTgDriver` against real api.telegram.org via a second
  "driver" bot. Agent runs against real Telegram (no `TG_API_BASE` set).
  Requires `TG_DRIVER_TOKEN` and `TG_AGENT_USERNAME` env vars, plus both
  bots opted into bot-to-bot mode in BotFather. See README_live.md.

The LLM mock (`LlmMockController` on tcp:9765) is shared by both transports
and unchanged — the agent still uses the Test provider for deterministic
answers; only the message-delivery transport differs.

The autouse `_tg_authenticate` fixture sends `auth <secret>` once as the
test user so subsequent injects pass the adapter's first-user auth gate.
"""
import os
import sys

import pytest

# Reuse the LLM mock harness from Autotests/mock/ without duplicating its code.
_MOCK_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "mock"))
if _MOCK_DIR not in sys.path:
    sys.path.insert(0, _MOCK_DIR)

# Allow this directory to import its own siblings (server.py, real_driver.py).
_SELF_DIR = os.path.dirname(__file__)
if _SELF_DIR not in sys.path:
    sys.path.insert(0, _SELF_DIR)

from llm import LlmMockController  # noqa: E402
from rpc import PORT_DEFAULT as LLM_PORT_DEFAULT  # noqa: E402

from server import MockTelegramServer, PORT_DEFAULT as TG_PORT_DEFAULT  # noqa: E402


AUTH_SECRET = os.environ.get("OMEGACLAW_AUTH_SECRET") or "0000"
TG_TOKEN = os.environ.get("MOCK_TG_TOKEN") or "DUMMYTESTTOKEN"


def pytest_addoption(parser):
    parser.addoption(
        "--transport",
        action="store",
        default="mock",
        choices=("mock", "live"),
        help="Telegram transport: 'mock' (local HTTP emulator) or "
             "'live' (real api.telegram.org via driver bot).",
    )


@pytest.fixture(scope="session")
def llm():
    controller = LlmMockController(("0.0.0.0", LLM_PORT_DEFAULT))
    try:
        yield controller
    finally:
        controller.stop(5)


@pytest.fixture(scope="session")
def tg(request):
    transport = request.config.getoption("--transport")
    if transport == "live":
        driver_token = os.environ.get("TG_DRIVER_TOKEN")
        agent_username = os.environ.get("TG_AGENT_USERNAME")
        if not driver_token or not agent_username:
            pytest.skip(
                "live transport requires TG_DRIVER_TOKEN and TG_AGENT_USERNAME "
                "env vars (see Autotests/mock_telegram/README_live.md)"
            )
        from real_driver import RealTgDriver  # noqa: E402
        driver = RealTgDriver(driver_token, agent_username)
        try:
            yield driver
        finally:
            driver.stop(5)
    else:
        server = MockTelegramServer(
            ("0.0.0.0", TG_PORT_DEFAULT), expected_token=TG_TOKEN
        )
        server.start()
        try:
            yield server
        finally:
            server.stop(5)


@pytest.fixture(scope="session", autouse=True)
def _tg_authenticate(tg, request):
    """Bind the test user as the authenticated owner of the agent's TG channel.

    The adapter's first-user auth gate accepts the first sender of
    `auth <secret>`; later senders are ignored. Doing this once per session
    is enough — all later injects use the same sender.
    """
    transport = request.config.getoption("--transport")
    auth_timeout = 30 if transport == "live" else 15

    tg.inject_user_message(f"auth {AUTH_SECRET}")
    print(f"[conftest] sent auth secret ({transport}); "
          f"waiting up to {auth_timeout}s for agent confirmation", flush=True)
    # If the agent was already authenticated from a previous pytest run against
    # the same container, the adapter silently ignores the second auth — no
    # reply is sent. A short window is enough; tests will surface a real auth
    # failure on their own prompts anyway.
    chat_id, text = tg.pop_agent_reply(timeout=auth_timeout)
    if text is None:
        print("[conftest] no agent reply to auth (likely already authenticated "
              "from a prior run); proceeding", flush=True)
    else:
        print(f"[conftest] agent confirmed auth: chat={chat_id} text={text!r}", flush=True)
    # Soak any extra greetings.
    extras = tg.drain_agent_replies(max_wait=3)
    if extras:
        print(f"[conftest] drained {len(extras)} extra agent replies post-auth", flush=True)
    yield
