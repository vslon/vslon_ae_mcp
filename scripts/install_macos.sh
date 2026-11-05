#!/usr/bin/env bash
# Installs the AE MCP Bridge CEP extension for Adobe After Effects (macOS).
# Note: developed and tested on Windows; the macOS path follows Adobe's CEP conventions.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DST_DIR="$HOME/Library/Application Support/Adobe/CEP/extensions"
DST="$DST_DIR/com.vslon.aemcp"

mkdir -p "$DST_DIR"
rm -rf "$DST"
cp -R "$REPO/extension/com.vslon.aemcp" "$DST"
echo "[ok] extension -> $DST"

for v in 9 10 11 12 13; do
  defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1
done
echo "[ok] PlayerDebugMode=1 for CSXS.9-13"

PY="$(command -v python3 || true)"
cat <<EOF

Add this to your MCP client config:
{
  "mcpServers": {
    "after-effects": { "command": "${PY:-python3}", "args": ["$REPO/server/ae_mcp_server.py"] }
  }
}

Then restart After Effects and your MCP client.
EOF
