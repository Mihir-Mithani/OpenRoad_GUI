#!/bin/bash
# =============================================================================
# Quick Start Script for ORFS Data Collection
# =============================================================================
# This script sets up the environment and runs data collection
# on a new machine for ORFS designs.
#
# Usage:
#   ./collect_data_quickstart.sh [options]
#
# Options:
#   --orfs-root PATH     ORFS root directory (default: ~/OpenROAD-flow-scripts)
#   --platforms LIST     Platforms to collect (default: all)
#   --workers N          Parallel workers (default: 4)
#   --output DIR         Output directory (default: ./collected_data)
#   --remote-host HOST   Remote SSH host (optional)
#   --resume             Resume from checkpoint
#   --help               Show this help
# =============================================================================

set -euo pipefail

# Default values
ORFS_ROOT="${ORFS_ROOT:-$HOME/OpenROAD-flow-scripts}"
PLATFORMS=("asap7" "sky130hd" "nangate45" "gf180")
WORKERS=4
OUTPUT_DIR="./collected_data"
REMOTE_HOST=""
REMOTE_USER=""
REMOTE_ORFS_ROOT=""
SSH_KEY=""
RESUME=true
WORKERS=4

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --orfs-root)
            ORFS_ROOT="$2"
            shift 2
            ;;
        --platforms)
            IFS=',' read -ra PLATFORMS <<< "$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --remote-host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        --remote-user)
            REMOTE_USER="$2"
            shift 2
            ;;
        --remote-orfs-root)
            REMOTE_ORFS_ROOT="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY="$2"
            shift 2
            ;;
        --no-resume)
            RESUME=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --orfs-root PATH       ORFS root directory (default: ~/OpenROAD-flow-scripts)"
            echo "  --platforms LIST       Comma-separated platforms (default: asap7,sky130hd,nangate45,gf180)"
            echo "  --workers N            Parallel workers (default: 4)"
            echo "  --output DIR           Output directory (default: ./collected_data)"
            echo "  --remote-host HOST     Remote SSH host (optional)"
            echo "  --remote-user USER     Remote SSH user"
            echo "  --remote-orfs-root PATH Remote ORFS root"
            echo "  --ssh-key PATH         SSH private key path"
            echo "  --no-resume            Disable resume from checkpoint"
            echo "  --help                 Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Expand paths
ORFS_ROOT=$(eval echo "$ORFS_ROOT")
OUTPUT_DIR=$(eval echo "$OUTPUT_DIR")

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}ORFS Data Collection Quick Start${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "ORFS Root:      ${GREEN}$ORFS_ROOT${NC}"
echo -e "Platforms:      ${GREEN}${PLATFORMS[*]}${NC}"
echo -e "Workers:        ${GREEN}$WORKERS${NC}"
echo -e "Output Dir:     ${GREEN}$OUTPUT_DIR${NC}"
if [[ -n "$REMOTE_HOST" ]]; then
    echo -e "Remote Host:    ${GREEN}$REMOTE_HOST${NC}"
fi
echo -e "${BLUE}=================================================================${NC}"

# Check ORFS installation
if [[ ! -d "$ORFS_ROOT" ]]; then
    echo -e "${RED}Error: ORFS root not found: $ORFS_ROOT${NC}"
    echo "Please install OpenROAD Flow Scripts first:"
    echo "  git clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git"
    echo "  cd OpenROAD-flow-scripts && ./setup.sh"
    exit 1
fi

if [[ ! -f "$ORFS_ROOT/use-openroad.sh" ]]; then
    echo -e "${RED}Error: use-openroad.sh not found in $ORFS_ROOT${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ORFS installation found${NC}"

# Check Python dependencies
echo -e "${YELLOW}Checking Python dependencies...${NC}"
python3 -c "import pandas, numpy, lightgbm, torch, polars, sklearn" 2>/dev/null || {
    echo -e "${RED}Missing Python dependencies. Installing...${NC}"
    pip install pandas numpy lightgbm torch polars scikit-learn tqdm pyyaml paramiko
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build Python command
PYTHON_SCRIPT="$(dirname "$0")/orfs_data_collection_master.py"
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    # Try to find it relative to this script
    PYTHON_SCRIPT="$(dirname "$0")/../orfs_data_collection_master.py"
fi

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo -e "${RED}Error: orfs_data_collection_master.py not found${NC}"
    echo "Please ensure orfs_data_collection_master.py is in the same directory"
    exit 1
fi

# Build Python command
PY_CMD=(
    python3 "$(dirname "$0")/orfs_data_collection_master.py"
    --orfs-root "$ORFS_ROOT"
    --platforms "${PLATFORMS[@]}"
    --workers "$WORKERS"
    --output "$OUTPUT_DIR"
)

if [[ "$RESUME" == "false" ]]; then
    PY_CMD+=(--no-resume)
fi

if [[ -n "$REMOTE_HOST" ]]; then
    PY_CMD+=(--remote-host "$REMOTE_HOST")
    [[ -n "$REMOTE_USER" ]] && PY_CMD+=(--remote-user "$REMOTE_USER")
    [[ -n "$REMOTE_ORFS_ROOT" ]] && PY_CMD+=(--remote-orfs-root "$REMOTE_ORFS_ROOT")
    [[ -n "$SSH_KEY" ]] && PY_CMD+=(--ssh-key "$SSH_KEY")
fi

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}Starting Data Collection${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo "Command: ${PY_CMD[*]}"
echo ""

# Run collection
start_time=$(date +%s)
python3 -m orfs_data_collection_master \
    --orfs-root "$ORFS_ROOT" \
    --platforms "${PLATFORMS[@]}" \
    --workers "$WORKERS" \
    --output "$OUTPUT_DIR" \
    "$@" || {
    echo -e "${RED}Collection failed!${NC}"
    exit 1
fi

# Generate training data
echo -e "${YELLOW}Generating training data...${NC}"
python3 -m openroad_gui.intelligence.data.prepare_real_training_data \
    --input "$OUTPUT_DIR/all_collected_records.json" \
    --output "$OUTPUT_DIR/training_data.json" || true

# Summary
END_TIME=$(date +%s)
ELAPSED=$(( $(date +%s) - START_TIME ))
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}Collection Complete!${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo "Results saved to: $OUTPUT_DIR"
echo "Elapsed time: $((ELAPSED / 60)) minutes"
echo ""
echo "Generated files:"
echo "  - $OUTPUT_DIR/all_collected_records.json"
echo "  - $OUTPUT_DIR/training_data.json (for training)"
echo "  - $OUTPUT_DIR/collection_summary.json"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review collected data in $OUTPUT_DIR/all_collected_records.json"
echo "2. Train models: python -m openroad_gui.intelligence.training.train_all_v3"
echo "3. Or run full pipeline: python -m openroad_gui.intelligence.training.train_all_v3 --aws-data \$OUTPUT_DIR/aws_real_runs_comprehensive.json"