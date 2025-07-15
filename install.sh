#!/bin/bash
# Installation script for sgtm-debug-header

set -e

SCRIPT_NAME="sgtm-debug-header"
INSTALL_DIR="/usr/local/bin"
SCRIPT_URL="https://raw.githubusercontent.com/prabapro/sgtm-debug-header/main/sgtm-debug-header.py"

echo "Installing sgtm-debug-header CLI tool..."

# Check if mitmproxy is installed
if ! command -v mitmdump &> /dev/null; then
    echo "Error: mitmproxy is required but not installed."
    echo "Please install it with: brew install mitmproxy"
    exit 1
fi

# Create the script content (embedding the Python script)
cat > "$SCRIPT_NAME" << 'EOF'
#!/usr/bin/env python3
"""
SGTM Debug CLI - A mitmproxy wrapper for adding X-Gtm-Server-Preview headers
Usage: sgtm-debug-header <domain> <header_value>
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path

def create_mitmproxy_script(domain, header_value):
    """Create a temporary mitmproxy script that adds the header for the specified domain."""
    script_content = f'''
import mitmproxy.http
from mitmproxy import ctx

def request(flow: mitmproxy.http.HTTPFlow) -> None:
    """Add X-Gtm-Server-Preview header to requests for the target domain."""
    target_domain = "{domain}"
    header_value = "{header_value}"
    
    # Check if the request is for the target domain
    if target_domain in flow.request.pretty_host:
        flow.request.headers["X-Gtm-Server-Preview"] = header_value
        ctx.log.info(f"Added X-Gtm-Server-Preview: {{header_value}} to {{flow.request.pretty_url}}")
    else:
        ctx.log.debug(f"Skipping {{flow.request.pretty_url}} - not target domain")

def response(flow: mitmproxy.http.HTTPFlow) -> None:
    """Log responses for debugging."""
    target_domain = "{domain}"
    
    if target_domain in flow.request.pretty_host:
        ctx.log.info(f"Response {{flow.response.status_code}} for {{flow.request.pretty_url}}")
'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        return f.name

def main():
    # Parse arguments
    args = sys.argv[1:]
    
    if len(args) < 2:
        print("Usage: sgtm-debug-header <domain> <header_value> [options]")
        print("Example: sgtm-debug-header example.com ZW52LWRldjEyMzQ1")
        print("Options:")
        print("  --web    Use web interface (default: console)")
        print("  --proxy  Use manual proxy mode (requires browser config)")
        print("  --transparent  Use transparent proxy mode (default)")
        sys.exit(1)
    
    domain = args[0]
    header_value = args[1]
    
    # Check for flags
    use_web = '--web' in args
    use_proxy = '--proxy' in args
    use_transparent = '--transparent' in args or not use_proxy  # default to transparent
    
    print(f"Starting SGTM debug session for domain: {domain}")
    print(f"Header value: {header_value}")
    print("Configure your browser to use proxy: 127.0.0.1:8080")
    print("Press Ctrl+C to stop\n")
    
    # Create the mitmproxy script
    script_path = create_mitmproxy_script(domain, header_value)
    
    try:
        # Run mitmproxy with the script
        cmd = [
            'mitmdump',
            '--listen-port', '8080',
            '--script', script_path,
            '--set', 'confdir=~/.mitmproxy'
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\nStopping SGTM debug session...")
    except FileNotFoundError:
        print("Error: mitmproxy not found. Please install it with: brew install mitmproxy")
        sys.exit(1)
    finally:
        # Clean up temporary script
        try:
            os.unlink(script_path)
        except OSError:
            pass

if __name__ == "__main__":
    main()
EOF

# Make it executable
chmod +x "$SCRIPT_NAME"

# Move to install directory
if [ -w "$INSTALL_DIR" ]; then
    mv "$SCRIPT_NAME" "$INSTALL_DIR/"
    echo "✅ sgtm-debug-header installed successfully to $INSTALL_DIR"
else
    echo "Installing to $INSTALL_DIR requires sudo..."
    sudo mv "$SCRIPT_NAME" "$INSTALL_DIR/"
    echo "✅ sgtm-debug-header installed successfully to $INSTALL_DIR"
fi

echo ""
echo "Usage: sgtm-debug-header <domain> <header_value>"
echo "Example: sgtm-debug-header example.com ZW52LWRldjEyMzQ1"
echo ""
echo "The proxy will run on 127.0.0.1:8080"
echo "Configure your browser to use this proxy, then visit your domain."