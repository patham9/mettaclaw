#!/bin/bash
# MeTTaClaw Runner — simplified
# Usage: ./run.sh [command] [options]
#
# Commands:
#   build              Build the container image
#   run [script]       Run a MeTTa script (default: run.metta)
#   shell              Open a shell in the container
#   clean              Remove the container image
#   status             Show build status
#   -h, --help         Show help
#
# Environment: Set API keys in .env or inline:
#   OPENAI_API_KEY=sk-... ./run.sh run
#   OLLAMA_API_BASE=http://localhost:11434 ./run.sh run
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Common env vars for container (space-separated for word splitting)
ENV_VARS=(
    -e "OPENAI_API_KEY=${OPENAI_API_KEY:-}"
    -e "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}"
    -e "OLLAMA_API_BASE=${OLLAMA_API_BASE:-}"
    -e "OLLAMA_MODEL=${OLLAMA_MODEL:-llama3}"
    -e "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}"
    -e "GROQ_API_KEY=${GROQ_API_KEY:-}"
    -e "PETTA_PATH=$CONTAINER_WORKDIR"
    -e "TERM=xterm-256color"
)

RUN_FLAGS=(
    --network host --rm -it -w "$CONTAINER_WORKDIR"
)

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

    local mount=()
    # Mount individual local MeTTa files read-only, leaving memory/ writable
    if [[ -f "$SCRIPT_DIR/run.metta" ]]; then
        mount+=(
            -v "$SCRIPT_DIR/run.metta:/opt/PeTTa/repos/mettaclaw/run.metta:ro"
            -v "$SCRIPT_DIR/lib_mettaclaw.metta:/opt/PeTTa/repos/mettaclaw/lib_mettaclaw.metta:ro"
            -v "$SCRIPT_DIR/lib_nal.metta:/opt/PeTTa/repos/mettaclaw/lib_nal.metta:ro"
            -v "$SCRIPT_DIR/lib_llm_ext.py:/opt/PeTTa/repos/mettaclaw/lib_llm_ext.py:ro"
            -v "$SCRIPT_DIR/memory/prompt.txt:/opt/PeTTa/repos/mettaclaw/memory/prompt.txt:ro"
            -v "$SCRIPT_DIR/src:/opt/PeTTa/repos/mettaclaw/src:ro"
        )
    fi

    echo "Running: $script"
    $RUNTIME run "${RUN_FLAGS[@]}" "${mount[@]}" "${ENV_VARS[@]}" "$IMAGE_NAME" \
        /opt/PeTTa/container_run.sh "$script"
}

cmd_shell() {
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null || { echo "Error: Run './run.sh build' first" >&2; exit 1; }

    local mount=()
    if [[ -f "$SCRIPT_DIR/run.metta" ]]; then
        mount+=(
            -v "$SCRIPT_DIR/run.metta:/opt/PeTTa/repos/mettaclaw/run.metta:ro"
            -v "$SCRIPT_DIR/lib_mettaclaw.metta:/opt/PeTTa/repos/mettaclaw/lib_mettaclaw.metta:ro"
            -v "$SCRIPT_DIR/lib_nal.metta:/opt/PeTTa/repos/mettaclaw/lib_nal.metta:ro"
            -v "$SCRIPT_DIR/lib_llm_ext.py:/opt/PeTTa/repos/mettaclaw/lib_llm_ext.py:ro"
            -v "$SCRIPT_DIR/memory/prompt.txt:/opt/PeTTa/repos/mettaclaw/memory/prompt.txt:ro"
            -v "$SCRIPT_DIR/src:/opt/PeTTa/repos/mettaclaw/src:ro"
        )
    fi

    $RUNTIME run "${RUN_FLAGS[@]}" "${mount[@]}" "${ENV_VARS[@]}" "$IMAGE_NAME" /bin/bash
}

cmd_clean() {
    $RUNTIME rmi -f "$IMAGE_NAME" 2>/dev/null || true
    echo "Cleaned."
}

cmd_status() {
    echo -n "Runtime: $RUNTIME | Image: "
    $RUNTIME image inspect "$IMAGE_NAME" &>/dev/null && echo "exists" || echo "not built"
    echo -n "Local files: "
    [[ -f "$SCRIPT_DIR/run.metta" ]] && echo "yes (will be mounted)" || echo "no"
}

cmd_help() {
    cat <<EOF
Usage: $0 <command> [options]

Commands:
  build              Build the container image
  run [script]       Run a MeTTa script (default: run.metta)
  shell              Open a shell in the container
  clean              Remove the container image
  status             Show build status
  -h, --help         Show help

Examples:
  ./run.sh build
  OPENAI_API_KEY=sk-... ./run.sh run
  OLLAMA_API_BASE=http://localhost:11434 ./run.sh run myscript.metta
  ./run.sh shell
EOF
}

case "${1:-run}" in
    build)     cmd_build ;;
    run)       cmd_run "${2:-}" ;;
    shell|sh)  cmd_shell ;;
    clean)     cmd_clean ;;
    status)    cmd_status ;;
    -h|--help) cmd_help ;;
    *)         echo "Unknown: $1" >&2; cmd_help; exit 1 ;;
esac
