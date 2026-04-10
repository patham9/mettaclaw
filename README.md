# MeTTaClaw

An agentic AI system in MeTTa with embedding-based long-term memory, multi-channel support, and autonomous goal pursuit.

---

## Quick Start

### 1. Build the image

```bash
./run.sh build
```

### 2. Set your API key

On first run, a `.env` file is auto-created from the template. Edit it:

```bash
# OpenAI
OPENAI_API_KEY="sk-..."
```

Or pass it inline:

```bash
OPENAI_API_KEY="sk-..." ./run.sh
```

### 3. Run

```bash
./run.sh
```

That's it. The agent will connect to IRC by default. For CLI mode:

```bash
./run.sh cli
```

---

## LLM Providers

Pick **one** provider and set the corresponding environment variable. The system auto-detects which one to use.

### OpenAI (GPT-4, GPT-4o, o1, o3)

```bash
# .env
OPENAI_API_KEY="sk-..."
```

```bash
# Or inline
OPENAI_API_KEY="sk-..." ./run.sh
```

Get a key: https://platform.openai.com/api-keys

### Anthropic (Claude)

```bash
# .env
ANTHROPIC_API_KEY="sk-ant-..."
```

Get a key: https://console.anthropic.com/settings/keys

### Ollama (Local, Free)

Install [Ollama](https://ollama.ai), pull a model, then:

```bash
# .env
OLLAMA_API_BASE="http://localhost:11434"
OLLAMA_MODEL="llama3"
```

```bash
# Inline with a specific model (e.g., Qwen3 8B GGUF)
OLLAMA_API_BASE="http://localhost:11434" \
OLLAMA_MODEL="hf.co/bartowski/Qwen_Qwen3-8B-GGUF:Q6_K" \
./run.sh
```

```bash
# One-time setup
ollama pull llama3
```

### OpenRouter (100+ models, one API)

```bash
# .env
OPENROUTER_API_KEY="..."
```

Get a key: https://openrouter.ai/settings/keys

### Groq (Fast inference)

```bash
# .env
GROQ_API_KEY="gsk_..."
```

Get a key: https://console.groq.com/keys

### Other Providers

MeTTaClaw uses [LiteLLM](https://docs.litellm.ai/) under the hood, so it supports any provider LiteLLM supports: Together AI, Google Vertex AI, AWS Bedrock, Azure OpenAI, and custom OpenAI-compatible endpoints.

See `.env.example` for all available options.

---

## Communication Channels

MeTTaClaw supports multiple communication channels. Select one with the `METTACLAW_CHANNEL` environment variable.

### CLI Mode (Terminal)

Direct terminal interaction - type messages and see responses in your terminal.

```bash
# Start in CLI mode
OLLAMA_API_BASE=http://localhost:11434 ./run.sh cli

# Or use the environment variable
METTACLAW_CHANNEL=cli OLLAMA_API_BASE=http://localhost:11434 ./run.sh
```

**Features:**
- Interactive prompt (`> `)
- Direct stdin/stdout communication
- No network required
- Great for testing and development

### IRC Mode (Default)

Connect to IRC channels for multi-user interaction.

```bash
# Default: ##metta @ irc.libera.chat
OLLAMA_API_BASE=http://localhost:11434 ./run.sh irc

# Custom channel and server
IRC_CHANNEL="##mychannel" \
IRC_SERVER="irc.libera.chat" \
OLLAMA_API_BASE=http://localhost:11434 ./run.sh irc
```

**IRC Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `IRC_CHANNEL` | `##metta` | IRC channel to join |
| `IRC_SERVER` | `irc.libera.chat` | IRC server hostname |
| `IRC_PORT` | `6667` | IRC server port |

### Multi-Channel Architecture

The channel system is built on the `embodiment.py` abstraction layer, which:

- Provides a unified interface for all channels
- Aggregates messages from multiple sources
- Broadcasts responses to all connected channels
- Supports adding new channels (Matrix, Discord, etc.)

**Architecture:**
```
┌─────────────────┐
│  EmbodimentBus  │  ← Multi-channel abstraction
├─────────────────┤
│   IRC Channel   │  ← IRC implementation
│   CLI Channel   │  ← Terminal implementation
│ Mattermost (WIP)│  ← Future channels
└─────────────────┘
        ↓
   AgentLoop.metta  ← Channel-agnostic agent loop
```

---

## Commands

| Command | Description |
|---------|-------------|
| `./run.sh` | Run `run.metta` (IRC mode, filtered output) |
| `./run.sh build` | Build the container image |
| `./run.sh run [script]` | Run a specific script |
| `./run.sh verbose [script]` | Run with full MeTTa/Prolog trace |
| `./run.sh dry-run [script]` | Validate setup without LLM calls |
| `./run.sh shell` | Open a shell in the container |
| `./run.sh cli` | Run in CLI mode (terminal) |
| `./run.sh irc` | Run in IRC mode |
| `./run.sh reset-history` | Clear memory/history.metta |
| `./run.sh clean` | Remove the image |
| `./run.sh status` | Check build status and config |
| `./run.sh -h` | Show help |

---

## Agent Skills

The agent has access to these skills (S-expression commands):

### Memory Skills
| Skill | Description | Example |
|-------|-------------|---------|
| `remember` | Store to long-term memory | `(remember "User prefers terse responses")` |
| `query` | Search long-term memory | `(query "preferences about style")` |
| `pin` | Pin to working memory | `(pin "Current task: debugging")` |

### Communication Skills
| Skill | Description | Example |
|-------|-------------|---------|
| `send` | Send message to user | `(send "Task completed")` |
| `send-to` | Send to specific channel | `(send-to "irc" "Hello IRC")` |

### File Skills
| Skill | Description | Example |
|-------|-------------|---------|
| `read-file` | Read file contents | `(read-file "config.json")` |
| `write-file` | Write to file | `(write-file "output.txt" "content")` |
| `append-file` | Append to file | `(append-file "log.txt" "entry")` |

### Other Skills
| Skill | Description | Example |
|-------|-------------|---------|
| `shell` | Execute shell command | `(shell "git status")` |
| `search` | Web search | `(search "latest AI news")` |
| `metta` | Evaluate MeTTa expression | `(metta "(+ 1 2)")` |

---

## Examples

```bash
# Build
./run.sh build

# Run with CLI mode
OLLAMA_API_BASE=http://localhost:11434 ./run.sh cli

# Run with IRC mode (default)
OLLAMA_API_BASE=http://localhost:11434 ./run.sh

# Run with inline API key
OPENAI_API_KEY="sk-..." ./run.sh

# Run a specific script
OPENAI_API_KEY="sk-..." ./run.sh run myscript.metta

# Run with Ollama (local)
OLLAMA_API_BASE="http://localhost:11434" OLLAMA_MODEL="llama3" ./run.sh

# Run with Ollama and a GGUF model
OLLAMA_API_BASE="http://localhost:11434" \
OLLAMA_MODEL="hf.co/bartowski/Qwen_Qwen3-8B-GGUF:Q6_K" \
./run.sh

# Run with Claude
ANTHROPIC_API_KEY="sk-ant-..." ./run.sh

# Validate setup before running (no LLM calls)
OLLAMA_API_BASE=http://localhost:11434 ./run.sh dry-run

# Full trace output for debugging
./run.sh verbose

# Debug shell inside container
./run.sh shell

# Clear agent history
./run.sh reset-history

# Check status
./run.sh status
```

---

## How It Works

```
Host (run.sh)                Container (/opt/PeTTa)
────────────                 ──────────────────────
./run.sh build ──build──▶    PeTTa + MeTTaClaw cloned
                             
./run.sh run ──exec──▶       container_run.sh
                                     ↓
                             provider_init.metta (auto-detected from env)
                                     ↓
                             agent_run.py (filters output, writes agent.log)
                                     ↓
                             run.metta → PeTTa → LLM
                                     ↓
                             channels/embodiment.py → IRC/CLI
```

### Key Components

- **`run.sh`** (host) — builds and runs the container
- **`container_run.sh`** (inside) — detects provider from env vars
- **`agent_run.py`** (inside) — runs PeTTa with output filtering and structured logging
- **`lib_llm_ext.py`** — Python LLM interface using LiteLLM (supports all providers)
- **`channels/embodiment.py`** — Multi-channel abstraction layer
- **`channels/cli.py`** — Terminal/CLI implementation
- **`channels/irc.py`** — IRC protocol implementation

### Output Filtering

By default, MeTTa compilation noise (Prolog clauses, specialization traces) is suppressed. You see only:
- Iteration numbers
- Human messages received
- LLM prompts sent and responses
- Command results and errors

Use `./run.sh verbose` for the full trace.

### Structured Logging

Every run writes `/opt/PeTTa/agent.log` with JSON lines:
```json
{"t": 0.01, "event": "iteration", "k": 1, "loops": 50, "human_msg": ""}
{"t": 30.5, "event": "response", "text": "((query \"goals\"))"}
```

Copy it out after a run:
```bash
podman cp <container>:/opt/PeTTa/agent.log .
```

### Local Development

Local MeTTa files (`run.metta`, `lib_mettaclaw.metta`, `src/`, `channels/`) are mounted read-only into the container. The `memory/` directory is mounted read-write for history persistence. Edit files on your host and they're available on next run — no rebuild needed.

---

## Project Structure

| File | Purpose |
|------|---------|
| `run.sh` | Host-side runner (build, run, verbose, dry-run, shell, cli, irc, clean, status) |
| `container_run.sh` | Inside-container entrypoint (provider detection) |
| `agent_run.py` | Inside-container PeTTa wrapper (filtering, logging, dry-run) |
| `Dockerfile` | Container image definition |
| `lib_llm_ext.py` | Python LLM wrapper (LiteLLM, all providers) |
| `channels/embodiment.py` | Multi-channel abstraction layer |
| `channels/cli.py` | CLI channel implementation |
| `channels/irc.py` | IRC channel implementation |
| `src/loop.metta` | Agent main loop |
| `src/channels.metta` | Channel initialization and message handling |
| `src/memory.metta` | Memory functions (remember, query, history) |
| `src/skills.metta` | Skill definitions |
| `src/helper.py` | Python helper functions |
| `memory/prompt.txt` | Agent system prompt (edit locally) |
| `memory/history.metta` | Conversation history (persistent) |
| `VERSION` | Current version |
| `.env.example` | Configuration template |
| `.env` | Your config (gitignored) |

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `METTACLAW_CHANNEL` | `irc` | Channel type: `irc` or `cli` |
| `IRC_CHANNEL` | `##metta` | IRC channel to join |
| `IRC_SERVER` | `irc.libera.chat` | IRC server hostname |
| `IRC_PORT` | `6667` | IRC server port |
| `OLLAMA_API_BASE` | - | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENROUTER_API_KEY` | - | OpenRouter API key |
| `GROQ_API_KEY` | - | Groq API key |
| `METTACLAW_VERBOSE` | `false` | Enable full trace |
| `METTACLAW_DRY_RUN` | `false` | Validate without LLM |

---

## License

[MIT](LICENSE)
