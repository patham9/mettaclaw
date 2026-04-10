# MeTTaClaw 2

An agentic AI system in MeTTa with embedding-based long-term memory.

---

## Quick Start (Docker/Podman)

**The only commands you need:**

```bash
# 1. Build the image
./run.sh build

# 2. Run (with your API key)
OPENAI_API_KEY=sk-... ./run.sh run
```

That's it! Want it even simpler? Create a `.env` file:

```bash
# .env
OPENAI_API_KEY=sk-...
```

Then just run:
```bash
./run.sh
```

### Other Commands

```bash
./run.sh start       # Interactive chat mode
./run.sh sh         # Shell for debugging
./run.sh status     # Check status
./run.sh clean     # Remove image
```

---

## LLM Providers

Set any of these in `.env`:

| Provider | Variable | Example |
|----------|---------|---------|
| OpenAI | `OPENAI_API_KEY` | `sk-...` |
| Anthropic | `ANTHROPIC_API_KEY` | `sk-ant-...` |
| Ollama | `OLLAMA_API_BASE` | `http://localhost:11434` |
| Groq | `GROQ_API_KEY` | `gsk_...` |
| OpenRouter | `OPENROUTER_API_KEY` | `...` |

Ollama example:
```bash
# Install Ollama, then:
# ollama pull llama3
OLLAMA_API_BASE=http://localhost:11434 OLLAMA_MODEL=llama3 ./run.sh
```

---

## Configuration (Optional)

Create `.env` file:

```bash
# .env - minimal
OPENAI_API_KEY=sk-...

# .env - Ollama (local, free)
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=llama3

# .env - Claude
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `./run.sh` | Run default script |
| `./run.sh build` | Build Docker image |
| `./run.sh run` | Run with script |
| `./run.sh start` | Interactive mode |
| `./run.sh sh` | Debug shell |
| `./run.sh clean` | Remove image |
| `./run.sh status` | Show status |

---

## Documentation

For more details, see:
- [CONFIG.md](CONFIG.md) - Full configuration
- [LITELLM_CONFIG.md](LITELLM_CONFIG.md) - LLM providers

---

## License

[MIT](LICENSE)