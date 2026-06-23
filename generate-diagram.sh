#!/bin/bash

# Convert Mermaid diagram to PNG
# Requires: npm install -g @mermaid-js/mermaid-cli

# Extract the mermaid diagram from ARCHITECTURE_DIAGRAM.md
sed -n '/```mermaid/,/```/p' ARCHITECTURE_DIAGRAM.md | sed '1d;$d' > /tmp/architecture.mmd

# Use mmdc (mermaid CLI) to convert to PNG
if command -v mmdc &> /dev/null; then
    mmdc -i /tmp/architecture.mmd -o ARCHITECTURE.png
    echo "✅ Generated ARCHITECTURE.png"
else
    echo "❌ Mermaid CLI not installed."
    echo "Install it with: npm install -g @mermaid-js/mermaid-cli"
    echo "Then run this script again."
fi
