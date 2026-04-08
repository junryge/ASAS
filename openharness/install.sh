#!/bin/bash
# OpenHarness Team Installation Script
# Usage: bash install.sh

set -e

echo "╔══════════════════════════════════════════╗"
echo "║  OpenHarness Installer v0.1.0            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OH_HOME="$HOME/.openharness"

# 1. Create user config directory
echo "→ Creating config directory: $OH_HOME"
mkdir -p "$OH_HOME"/{skills,plugins,sessions}

# 2. Create TOKEN.TXT template if not exists
if [ ! -f "$OH_HOME/TOKEN.TXT" ]; then
    touch "$OH_HOME/TOKEN.TXT"
    echo "→ Created TOKEN.TXT (empty)"
    echo "  ⚠️  Place your API key in: $OH_HOME/TOKEN.TXT"
else
    echo "→ TOKEN.TXT already exists"
fi

# 3. Install package
echo "→ Installing OpenHarness..."
pip install -e "$SCRIPT_DIR" 2>/dev/null || pip install -e "$SCRIPT_DIR" --break-system-packages

# 4. Verify installation
echo ""
echo "→ Verifying installation..."
if command -v oh &> /dev/null; then
    echo "  ✅ 'oh' command installed successfully"
else
    echo "  ⚠️  'oh' command not found in PATH"
    echo "     Try: python -m openharness"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Installation Complete!                  ║"
echo "║                                          ║"
echo "║  1. Add API key: $OH_HOME/TOKEN.TXT      ║"
echo "║  2. Run: oh                              ║"
echo "║  3. Help: oh --help                      ║"
echo "╚══════════════════════════════════════════╝"
