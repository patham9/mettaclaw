#!/bin/bash
# MeTTaClaw Podman/Docker Runner Script
# =====================================
# Usage:
#   ./run.sh build              Build the Docker image
#   ./run.sh run [script]      Run MeTTa script (default: run.metta)
#   ./run.sh                  Short for: ./run.sh run
#   ./run.sh start            Run interactively
#   ./run.sh sh               Shell in container
#   ./run.sh clean           Remove image
#   ./run.sh reset           Clean + rebuild
#   ./run.sh status         Show status
#   ./run.sh -h, --help       Show help
#
set -euo pipefail

# --------------------------------------------------------------------
# Directory - always derive from script location
# --------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if present
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a; source "$SCRIPT_DIR/.env"; set +a
fi

# --------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --------------------------------------------------------------------
# Configuration (all parameterized)
# --------------------------------------------------------------------
IMAGE_NAME="${IMAGE_NAME:-mettaclaw:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-mettaclaw}"
DEFAULT_REPO="${METTACLAW_REPO:-https://github.com/autonull/mettaclaw}"
DEFAULT_BRANCH="${METTACLAW_BRANCH:-main}"
CONTAINER_PETTA_PATH="${CONTAINER_PETTA_PATH:-/opt/PeTTa}"
CONTAINER_METTACLAW_PATH="${CONTAINER_METTACLAW_PATH:-/opt/PeTTa/repos/mettaclaw}"
LOCAL_CODE_INDICATORS="${LOCAL_CODE_INDICATORS:-run.metta|lib_mettaclaw.metta|lib_nal.metta|src}"
DEFAULT_SCRIPT="${DEFAULT_SCRIPT:-run.metta}"
PETTA_REPO="${PETTA_REPO:-https://github.com/trueagi-io/PeTTa}"
PETTA_BRANCH="${PETTA_BRANCH:-main}"
FORCE_NO_CACHE="${FORCE_NO_CACHE:-false}"
PULL_ALWAYS="${PULL_ALWAYS:-false}"

# LLM config
LLM_MODEL="${LLM_MODEL:-}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"

RUNTIME=""

# --------------------------------------------------------------------
# Runtime Detection
# --------------------------------------------------------------------
detect_runtime() {
    if command -v podman &>/dev/null; then
        RUNTIME="podman"
    elif command -v docker &>/dev/null; then
        RUNTIME="docker"
    else
        echo -e "${RED}Error: Neither podman nor docker is installed${NC}"
        echo -e "${YELLOW}Install: https://podman.io or https://docker.io${NC}"
        exit 1
    fi
    echo -e "${CYAN}Using: $RUNTIME${NC}"
}

# --------------------------------------------------------------------
# Network Check
# --------------------------------------------------------------------
check_network() {
    curl --silent --fail --connect-timeout 5 https://github.com >/dev/null 2>&1
    return $?
}

# --------------------------------------------------------------------
# Image Check
# --------------------------------------------------------------------
check_image() {
    "$RUNTIME" image inspect "$IMAGE_NAME" >/dev/null 2>&1
}

# --------------------------------------------------------------------
# Validate Config
# --------------------------------------------------------------------
validate_config() {
    if [[ -n "${OPENAI_API_KEY:-}" && ! "$OPENAI_API_KEY" =~ ^sk-[a-zA-Z0-9-]+$ ]]; then
        echo -e "${YELLOW}Warning: OPENAI_API_KEY format looks unusual${NC}"
    fi
    CONTAINER_PETTA_PATH="${CONTAINER_PETTA_PATH#/}"
    CONTAINER_METTACLAW_PATH="${CONTAINER_METTACLAW_PATH#/}"
}

# --------------------------------------------------------------------
# Help
# --------------------------------------------------------------------
show_help() {
    cat << EOF
${BOLD}MeTTaClaw Runner${NC}

Usage: $0 <command> [options]

Commands:
  build              Build Docker image
  run [script]       Run script (default: $DEFAULT_SCRIPT)
  start              Run interactively
  sh                 Shell in container
  clean              Remove image
  reset              Clean + rebuild
  status             Show status
  -h, --help         Show this help

Environment:
  OPENAI_API_KEY     Required for LLM
  METTACLAW_REPO     (default: $DEFAULT_REPO)
  IMAGE_NAME         (default: $IMAGE_NAME)

Examples:
  $0 build
  OPENAI_API_KEY=sk-... $0 run
  METTACLAW_REPO=https://github.com/user/repo $0 build

EOF
}

banner() {
    echo -e "${PURPLE}===== MeTTaClaw Runner =====${NC}"
    echo ""
}

# --------------------------------------------------------------------
# Local Code Detection
# --------------------------------------------------------------------
check_local_code() {
    local IFS='|'
    for f in $LOCAL_CODE_INDICATORS; do
        [[ -e "$SCRIPT_DIR/$f" ]] && return 0
    done
    return 1
}

# --------------------------------------------------------------------
# Build
# --------------------------------------------------------------------
cmd_build() {
    echo -e "${BLUE}Building image...${NC}"
    
    check_network || { echo -e "${RED}No network${NC}"; exit 1; }
    detect_runtime
    
    local repo="${METTACLAW_REPO:-$DEFAULT_REPO}"
    local branch="${METTACLAW_BRANCH:-$DEFAULT_BRANCH}"
    local petta_repo="${PETTA_REPO:-$PETTA_REPO}"
    local petta_branch="${PETTA_BRANCH:-$PETTA_BRANCH}"
    
    echo -e "${CYAN}MeTTaClaw: $repo ($branch)${NC}"
    echo -e "${CYAN}PeTTa: $petta_repo ($petta_branch)${NC}"
    
    check_local_code && echo -e "${GREEN}Local code detected${NC}" || echo -e "${YELLOW}No local code${NC}"
    
    cd "$SCRIPT_DIR"
    
    local -a args=()
    [[ "$FORCE_NO_CACHE" == "true" ]] && args+=(--no-cache)
    [[ "$PULL_ALWAYS" == "true" ]] && args+=(--pull)
    
    echo -e "${GREEN}Building...${NC}"
    # Build with host network (fixes some container/netns issues)
    "$RUNTIME" build --network host "${args[@]}" \
        --build-arg "METTACLAW_REPO=$repo" \
        --build-arg "METTACLAW_BRANCH=$branch" \
        --build-arg "PETTA_REPO=$petta_repo" \
        --build-arg "PETTA_BRANCH=$petta_branch" \
        --build-arg "CONTAINER_PETTA_PATH=$CONTAINER_PETTA_PATH" \
        --build-arg "CONTAINER_METTACLAW_PATH=$CONTAINER_METTACLAW_PATH" \
        -t "$IMAGE_NAME" .
    
    echo -e "${GREEN}Done!${NC}"
}

# --------------------------------------------------------------------
# Run
# --------------------------------------------------------------------
cmd_run() {
    local script="${1:-$DEFAULT_SCRIPT}"
    
    # Check for ANY provider key (not just OpenAI - supports Ollama, Claude, etc.)
    local has_key=0
    [[ -n "${OPENAI_API_KEY:-}" ]] && has_key=1
    [[ -n "${ANTHROPIC_API_KEY:-}" ]] && has_key=1
    [[ -n "${OLLAMA_API_BASE:-}" ]] && has_key=1
    [[ -n "${OPENROUTER_API_KEY:-}" ]] && has_key=1
    [[ -n "${GROQ_API_KEY:-}" ]] && has_key=1
    
    [[ $has_key -eq 0 ]] && { echo -e "${RED}No API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_API_BASE${NC}"; exit 1; }
    
    echo -e "${CYAN}Running: $script${NC}"
    [[ -n "$OPENAI_API_KEY" ]] && echo -e "${CYAN}Provider: OpenAI${NC}"
    [[ -n "$ANTHROPIC_API_KEY" ]] && echo -e "${CYAN}Provider: Anthropic${NC}"
    [[ -n "$OLLAMA_API_BASE" ]] && echo -e "${CYAN}Provider: Ollama${NC}"
    
    validate_config
    detect_runtime
    
    check_image || { echo -e "${RED}Image missing. Run: $0 build${NC}"; exit 1; }
    
    check_local_code
    local has_local=$?
    
    cd "$SCRIPT_DIR"
    
    local vol=""
    [[ $has_local -eq 0 ]] && vol="-v $SCRIPT_DIR:$CONTAINER_METTACLAW_PATH:ro"
    
    echo -e "${GREEN}Starting...${NC}"
    "$RUNTIME" run --rm -it \
        --name "$CONTAINER_NAME" \
        -e "OPENAI_API_KEY=${OPENAI_API_KEY:-}" \
        -e "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}" \
        -e "OLLAMA_API_BASE=${OLLAMA_API_BASE:-}" \
        -e "LLM_MODEL=${LLM_MODEL:-}" \
        -e "OLLAMA_MODEL=${OLLAMA_MODEL:-}" \
        -e "TERM=xterm-256color" \
        -e "PETTA_PATH=$CONTAINER_PETTA_PATH" \
        $vol \
        -w "$CONTAINER_PETTA_PATH" \
        "$IMAGE_NAME" \
        sh -c "cp $CONTAINER_METTACLAW_PATH/run.metta . 2>/dev/null || true && sh run.sh $script"
}

# --------------------------------------------------------------------
# Interactive
# --------------------------------------------------------------------
cmd_start() {
    local has_key=0
    [[ -n "${OPENAI_API_KEY:-}" ]] && has_key=1
    [[ -n "${ANTHROPIC_API_KEY:-}" ]] && has_key=1
    [[ -n "${OLLAMA_API_BASE:-}" ]] && has_key=1
    
    [[ $has_key -eq 0 ]] && { echo -e "${RED}No API key found${NC}"; exit 1; }
    
    echo -e "${CYAN}Interactive mode${NC}"
    
    validate_config
    detect_runtime
    check_image || { echo -e "${RED}Image missing${NC}"; exit 1; }
    check_local_code
    local has_local=$?
    
    cd "$SCRIPT_DIR"
    
    local vol=""
    [[ $has_local -eq 0 ]] && vol="-v $SCRIPT_DIR:$CONTAINER_METTACLAW_PATH:ro"
    
    "$RUNTIME" run --rm -it \
        --name "$CONTAINER_NAME" \
        -e "OPENAI_API_KEY=$OPENAI_API_KEY" \
        -e "TERM=xterm-256color" \
        -e "PETTA_PATH=$CONTAINER_PETTA_PATH" \
        $vol \
        -w "$CONTAINER_PETTA_PATH" \
        "$IMAGE_NAME" \
        sh -c "cp $CONTAINER_METTACLAW_PATH/run.metta . 2>/dev/null || true && sh run.sh $DEFAULT_SCRIPT"
}

# --------------------------------------------------------------------
# Shell
# --------------------------------------------------------------------
cmd_sh() {
    echo -e "${CYAN}Shell mode${NC}"
    
    detect_runtime
    check_image || { echo -e "${RED}Image missing${NC}"; exit 1; }
    check_local_code
    local has_local=$?
    
    cd "$SCRIPT_DIR"
    
    local vol=""
    [[ $has_local -eq 0 ]] && vol="-v $SCRIPT_DIR:$CONTAINER_METTACLAW_PATH:ro"
    
    "$RUNTIME" run --rm -it \
        --name "$CONTAINER_NAME" \
        -e "OPENAI_API_KEY=${OPENAI_API_KEY:-}" \
        -e "TERM=xterm-256color" \
        -e "PETTA_PATH=$CONTAINER_PETTA_PATH" \
        $vol \
        -w "$CONTAINER_PETTA_PATH" \
        "$IMAGE_NAME" \
        /bin/bash
}

# --------------------------------------------------------------------
# Clean
# --------------------------------------------------------------------
cmd_clean() {
    echo -e "${BLUE}Cleaning...${NC}"
    
    detect_runtime
    "$RUNTIME" rm -f "$CONTAINER_NAME" 2>/dev/null || true
    "$RUNTIME" rmi "$IMAGE_NAME" 2>/dev/null || echo -e "${YELLOW}Image not found${NC}"
    
    echo -e "${GREEN}Done${NC}"
}

# --------------------------------------------------------------------
# Status
# --------------------------------------------------------------------
cmd_status() {
    detect_runtime
    
    echo -e "${CYAN}Image: $IMAGE_NAME${NC}"
    check_image && echo -e "${GREEN}  Exists${NC}" || echo -e "${RED}  Missing${NC}"
    
    echo -e "${CYAN}Container: $CONTAINER_NAME${NC}"
    if "$RUNTIME" ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${YELLOW}  Running${NC}"
    else
        echo -e "${GREEN}  Not running${NC}"
    fi
    
    check_local_code && echo -e "${GREEN}Local code${NC}" || echo -e "${YELLOW}No local code${NC}"
}

# --------------------------------------------------------------------
# Reset
# --------------------------------------------------------------------
cmd_reset() {
    cmd_clean
    echo ""
    cmd_build
}

# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
main() {
    # No args = run default script
    if [[ $# -eq 0 ]]; then
        cmd_run
        return $?
    fi
    
    case "${1:-help}" in
        build) cmd_build ;;
        run) cmd_run "${2:-}" ;;
        start) cmd_start ;;
        sh) cmd_sh ;;
        clean) cmd_clean ;;
        reset) cmd_reset ;;
        status) cmd_status ;;
        -h|--help|help) show_help ;;
        *) echo -e "${RED}Unknown: $1${NC}"; show_help; exit 1 ;;
    esac
}

main "$@"