#!/usr/bin/env bash
set -eo pipefail

# Alice v2 Model Fetcher
# Automatically downloads required models for development/production

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create models directory if it doesn't exist
mkdir -p "$MODELS_DIR"

# Function to download model if it doesn't exist
download_model() {
    local filename="$1"
    local url="$2"
    local filepath="$MODELS_DIR/$filename"
    
    if [[ -f "$filepath" ]]; then
        log_info "Model $filename already exists, skipping download"
        return 0
    fi
    
    log_info "Downloading $filename from $url"
    
    if curl -fsSL -o "$filepath" "$url"; then
        log_info "Successfully downloaded $filename"
        # Verify file size (should be > 1MB for models)
        local size
        size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null || echo "0")
        if [[ $size -lt 1048576 ]]; then
            log_warn "Downloaded file seems too small ($size bytes), may be corrupted"
        fi
    else
        log_error "Failed to download $filename"
        rm -f "$filepath" 2>/dev/null || true
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting model download for Alice v2"
    log_info "Models directory: $MODELS_DIR"
    
    local failed_downloads=0
    
    # Download e5-small.onnx
    if ! download_model "e5-small.onnx" "https://huggingface.co/intfloat/e5-small/resolve/main/model.onnx"; then
        failed_downloads=$((failed_downloads + 1))
    fi
    
    # Download e5-tokenizer.json
    if ! download_model "e5-tokenizer.json" "https://huggingface.co/intfloat/e5-small/resolve/main/tokenizer.json"; then
        failed_downloads=$((failed_downloads + 1))
    fi
    
    if [[ $failed_downloads -eq 0 ]]; then
        log_info "All models downloaded successfully! 🚀"
        log_info "You can now start Alice v2 with: ./scripts/dev_up.sh"
    else
        log_error "$failed_downloads model(s) failed to download"
        log_warn "Some features may not work without the required models"
        exit 1
    fi
}

# Run main function
main "$@"

