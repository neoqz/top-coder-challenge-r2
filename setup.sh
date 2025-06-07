#!/bin/bash
# Install dependencies for evaluation scripts
set -e

need_pkg() {
    if ! command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

install_pkg() {
    pkg=$1
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y "$pkg"
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y "$pkg"
    elif command -v brew >/dev/null 2>&1; then
        brew install "$pkg"
    else
        echo "Please install $pkg manually." >&2
    fi
}

if need_pkg jq; then
    echo "Installing jq..."
    install_pkg jq
else
    echo "jq already installed"
fi

if need_pkg bc; then
    echo "Installing bc..."
    install_pkg bc
else
    echo "bc already installed"
fi

if python3 - <<'PY'
import numpy
PY
then
    echo "NumPy already installed"
else
    echo "Installing NumPy..."
    pip3 install --user numpy
fi

echo "Setup complete."
