#!/usr/bin/env bash
# Download and run Jaeger v2 locally (no Docker required).
#
# Usage:
#   ./scripts/start-jaeger.sh          # download + run
#   ./scripts/start-jaeger.sh --stop   # kill a running instance
#
# Jaeger UI: http://localhost:16686
# OTLP HTTP: http://localhost:4318

set -euo pipefail

JAEGER_VERSION="2.17.0"
INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)/.jaeger"
CONFIG="$(cd "$(dirname "$0")/.." && pwd)/jaeger-config.yaml"
PID_FILE="$INSTALL_DIR/jaeger.pid"

# ---------- stop mode ----------
if [[ "${1:-}" == "--stop" ]]; then
    if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "Jaeger (PID $pid) stopped."
        else
            echo "Jaeger process $pid not running."
        fi
        rm -f "$PID_FILE"
    else
        echo "No PID file found. Jaeger may not be running."
    fi
    exit 0
fi

# ---------- detect platform ----------
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    arm64)   ARCH="arm64" ;;
    *)       echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

TARBALL="jaeger-${JAEGER_VERSION}-${OS}-${ARCH}.tar.gz"
URL="https://github.com/jaegertracing/jaeger/releases/download/v${JAEGER_VERSION}/${TARBALL}"
BINARY="$INSTALL_DIR/jaeger-${JAEGER_VERSION}-${OS}-${ARCH}/jaeger"

# ---------- download if needed ----------
mkdir -p "$INSTALL_DIR"

if [[ ! -x "$BINARY" ]]; then
    echo "Downloading Jaeger v${JAEGER_VERSION} for ${OS}/${ARCH}..."
    curl -fSL "$URL" -o "$INSTALL_DIR/$TARBALL"
    tar -xzf "$INSTALL_DIR/$TARBALL" -C "$INSTALL_DIR"
    rm -f "$INSTALL_DIR/$TARBALL"
    echo "Installed to $BINARY"
fi

# ---------- run ----------
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Jaeger already running (PID $(cat "$PID_FILE")). Use --stop first."
    exit 0
fi

echo "Starting Jaeger v${JAEGER_VERSION}..."
echo "  UI:   http://localhost:16686"
echo "  OTLP: http://localhost:4318"
echo ""

"$BINARY" --config "$CONFIG" &
JAEGER_PID=$!
echo "$JAEGER_PID" > "$PID_FILE"
echo "Jaeger started (PID $JAEGER_PID). Stop with: $0 --stop"
