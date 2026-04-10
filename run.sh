#!/bin/bash
# MeTTaClaw Runner — simplified
# Usage: ./run.sh [command] [options]
#
# Commands:
#   build              Build the container image
#   run [script]       Run a MeTTa script (default: run.metta)
#   verbose [script]   Run with full MeTTa/Prolog trace output
#   dry-run [script]   Validate setup without calling LLM
#   shell              Open a shell in the container
#   reset-history      Clear memory/history.metta
#   clean              Remove the container image
#   status             Show build status
#   -h, --help         Show help
#
# Environment: Set API keys in .env or inline:
#   OPENAI_API_KEY=sk-... ./run.sh run
#   OLLAMA_API_BASE=http://localhost:11434 ./run.sh run
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${METTACLAW_VERSION:-$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "dev")}"

# Auto-create .env from example if missing
if [[ ! -f "$SCRIPT_DIR/.env" && -f "$SCRIPT_DIR/.env.example" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "Created .env from template — edit it with your API keys"
fi

[[ -f "$SCRIPT_DIR/.env" ]] && set -a; source "$SCRIPT_DIR/.env"; set +a

IMAGE_NAME="${IMAGE_NAME:-mettaclaw:latest}"
CONTAINER_WORKDIR="/opt/PeTTa"

# Detect runtime
RUNTIME=""
if command -v podman &>/dev/null; then
    RUNTIME="podman"
elif command -v docker &>/dev/null; then
    RUNTIME="docker"
else
    echo "Error: Install podman or docker" >&2; exit 1
fi

# Check API key exists (any provider)
has_api_key() {
    [[ -n "${OPENAI_API_KEY:-}" || -n "${ANTHROPIC_API_KEY:-}" || \
       -n "${OLLAMA_API_BASE:-}" || -n "${OPENROUTER_API_KEY:-}" || \
       -n "${GROQ_API_KEY:-}" ]]
}

# Common env vars for container
ENV_VARS=(
-e "OPENAI_API_KEY=${OPENAI_API_KEY:-}"
-e "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}"
-e "OLLAMA_API_BASE=${OLLAMA_API_BASE:-}"
-e "OLLAMA_MODEL=${OLLAMA_MODEL:-llama3}"
-e "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}"
-e "GROQ_API_KEY=${GROQ_API_KEY:-}"
-e "METTACLAW_CHANNEL=${METTACLAW_CHANNEL:-irc}"
-e "IRC_CHANNEL=${IRC_CHANNEL:-##metta}"
-e "IRC_SERVER=${IRC_SERVER:-irc.libera.chat}"
-e "METTACLAW_VERSION=$VERSION"
-e "PETTA_PATH=$CONTAINER_WORKDIR"
-e "TERM=xterm-256color"
)

RUN_FLAGS=(
    --network host --rm -it -w "$CONTAINER_WORKDIR"
)

# Common mount list for local MeTTa files (read-only, leaves memory/ writable)
local_mounts() {
if [[ -f "$SCRIPT_DIR/run.metta" ]]; then
echo "-v"
echo "$SCRIPT_DIR/run.metta:/opt/PeTTa/repos/mettaclaw/run.metta:ro"
echo "-v"
echo "$SCRIPT_DIR/lib_mettaclaw.metta:/opt/PeTTa/repos/mettaclaw/lib_mettaclaw.metta:ro"
echo "-v"
echo "$SCRIPT_DIR/lib_nal.metta:/opt/PeTTa/repos/mettaclaw/lib_nal.metta:ro"
echo "-v"
echo "$SCRIPT_DIR/lib_llm_ext.py:/opt/PeTTa/repos/mettaclaw/lib_llm_ext.py:ro"
echo "-v"
echo "$SCRIPT_DIR/src:/opt/PeTTa/repos/mettaclaw/src:ro"
echo "-v"
echo "$SCRIPT_DIR/channels:/opt/PeTTa/repos/mettaclaw/channels:ro"
echo "-v"
echo "$SCRIPT_DIR/container_run.sh:/opt/PeTTa/container_run.sh:ro"
echo "-v"
echo "$SCRIPT_DIR/agent_run.py:/opt/PeTTa/agent_run.py:ro"
fi
}

cmd_build() {
    cd "$SCRIPT_DIR"
    echo "Building $IMAGE_NAME with $RUNTIME..."
    $RUNTIME build --network host -t "$IMAGE_NAME" .
    echo "Build complete."
}

cmd_run() {
    local script="${1:-run.metta}"
    has_api_key || { echo "Error: Set an API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_API_BASE, etc.)" >&2; exit 1; }
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null || { echo "Error: Run './run.sh build' first" >&2; exit 1; }

    echo "v$VERSION | Running: $script"

    local mount_args=()
    while IFS= read -r line; do
        mount_args+=("$line")
    done < <(local_mounts)

    $RUNTIME run "${RUN_FLAGS[@]}" "${mount_args[@]}" "${ENV_VARS[@]}" \
        -v "$SCRIPT_DIR/memory:/opt/PeTTa/repos/mettaclaw/memory" \
        "$IMAGE_NAME" /opt/PeTTa/container_run.sh "$script"
}

cmd_verbose() {
    local script="${1:-run.metta}"
    has_api_key || { echo "Error: Set an API key first" >&2; exit 1; }
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null || { echo "Error: Run './run.sh build' first" >&2; exit 1; }

    echo "v$VERSION | Verbose run: $script"

    local mount_args=()
    while IFS= read -r line; do
        mount_args+=("$line")
    done < <(local_mounts)

    $RUNTIME run "${RUN_FLAGS[@]}" "${mount_args[@]}" "${ENV_VARS[@]}" \
        -e "METTACLAW_VERBOSE=true" \
        -v "$SCRIPT_DIR/memory:/opt/PeTTa/repos/mettaclaw/memory" \
        "$IMAGE_NAME" /opt/PeTTa/container_run.sh "$script"
}

cmd_dry_run() {
    local script="${1:-run.metta}"
    has_api_key || { echo "Error: Set an API key first" >&2; exit 1; }
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null || { echo "Error: Run './run.sh build' first" >&2; exit 1; }

    echo "v$VERSION | Dry run: $script (no LLM calls)"

    local mount_args=()
    while IFS= read -r line; do
        mount_args+=("$line")
    done < <(local_mounts)

    $RUNTIME run "${RUN_FLAGS[@]}" "${mount_args[@]}" "${ENV_VARS[@]}" \
        -e "METTACLAW_DRY_RUN=true" \
        -v "$SCRIPT_DIR/memory:/opt/PeTTa/repos/mettaclaw/memory" \
        "$IMAGE_NAME" /opt/PeTTa/container_run.sh "$script"
}

cmd_shell() {
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null || { echo "Error: Run './run.sh build' first" >&2; exit 1; }

    local mount_args=()
    while IFS= read -r line; do
        mount_args+=("$line")
    done < <(local_mounts)

    $RUNTIME run "${RUN_FLAGS[@]}" "${mount_args[@]}" "${ENV_VARS[@]}" \
        -v "$SCRIPT_DIR/memory:/opt/PeTTa/repos/mettaclaw/memory" \
        "$IMAGE_NAME" /bin/bash
}

cmd_reset_history() {
    echo "Resetting memory/history.metta..."
    : > "$SCRIPT_DIR/memory/history.metta"
    echo "Done."
}

cmd_clean() {
    $RUNTIME rmi -f "$IMAGE_NAME" 2>/dev/null || true
    echo "Cleaned."
}

cmd_status() {
    echo "MeTTaClaw v$VERSION"
    echo -n "  Runtime: $RUNTIME | Image: "
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null && echo "exists" || echo "not built"
    echo -n "  Local files: "
    [[ -f "$SCRIPT_DIR/run.metta" ]] && echo "yes (will be mounted)" || echo "no"
    echo -n "  API key: "
    has_api_key && echo "set" || echo "not set"
}

cmd_help() {
    cat <<EOF
Usage: $0 <command> [options]

Commands:
  build              Build the container image
  run [script]       Run a MeTTa script (default: run.metta)
  verbose [script]   Run with full MeTTa/Prolog trace
  dry-run [script]   Validate setup without LLM calls
  shell              Open a shell in the container
  reset-history      Clear memory/history.metta
  clean              Remove the container image
status Show build status and config
-h, --help Show help
cli Run in CLI mode (terminal interface)
irc Run in IRC mode

Env vars:
OPENAI_API_KEY OpenAI API key
ANTHROPIC_API_KEY Anthropic API key
OLLAMA_API_BASE Ollama endpoint (e.g., http://localhost:11434)
OLLAMA_MODEL Ollama model name
METTACLAW_CHANNEL Channel type: irc, cli (default: irc)
IRC_CHANNEL IRC channel to join (default: ##metta)
IRC_SERVER IRC server (default: irc.libera.chat)
METTACLAW_VERBOSE Set to true for full trace (or use ./run.sh verbose)
METTACLAW_DRY_RUN Set to true to validate without LLM (or use ./run.sh dry-run)

Examples:
$0 build
OPENAI_API_KEY=sk-... $0 run
OLLAMA_API_BASE=http://localhost:11434 $0 run myscript.metta
$0 cli
$0 irc
$0 verbose
$0 dry-run
$0 reset-history
EOF
}

cmd_cli() {
METTACLAW_CHANNEL=cli cmd_run "${1:-}"
}

cmd_irc() {
METTACLAW_CHANNEL=irc cmd_run "${1:-}"
}

case "${1:-run}" in
build) cmd_build ;;
run) cmd_run "${2:-}" ;;
verbose) cmd_verbose "${2:-}" ;;
dry-run) cmd_dry_run "${2:-}" ;;
shell|sh) cmd_shell ;;
reset-history) cmd_reset_history ;;
clean) cmd_clean ;;
status) cmd_status ;;
cli) cmd_cli "${2:-}" ;;
irc) cmd_irc "${2:-}" ;;
-h|--help) cmd_help ;;
*) echo "Unknown: $1" >&2; cmd_help; exit 1 ;;
esac
