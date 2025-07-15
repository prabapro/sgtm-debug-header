#!/usr/bin/env python3
"""
SGTM Debug CLI - A mitmproxy wrapper for adding X-Gtm-Server-Preview headers
Usage: sgtm-debug <domain> <header_value>
"""

import sys
import subprocess
import tempfile
import os
import signal
import platform
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
        ctx.log.info(f"✅ Added X-Gtm-Server-Preview: {{header_value}} to {{flow.request.pretty_url}}")
    else:
        ctx.log.debug(f"⏭️  Skipping {{flow.request.pretty_url}} - not target domain")

def response(flow: mitmproxy.http.HTTPFlow) -> None:
    """Log responses for debugging."""
    target_domain = "{domain}"
    
    if target_domain in flow.request.pretty_host:
        ctx.log.info(f"📥 Response {{flow.response.status_code}} for {{flow.request.pretty_url}}")
'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        return f.name

def setup_transparent_proxy():
    """Setup transparent proxy on macOS."""
    if platform.system() != 'Darwin':
        return False
    
    try:
        # Enable IP forwarding
        subprocess.run(['sudo', 'sysctl', '-w', 'net.inet.ip.forwarding=1'], check=True)
        
        # Add firewall rule to redirect traffic
        subprocess.run([
            'sudo', 'pfctl', '-f', '/dev/stdin'
        ], input=b'''
rdr pass inet proto tcp from any to any port 80 -> 127.0.0.1 port 8080
rdr pass inet proto tcp from any to any port 443 -> 127.0.0.1 port 8080
''', check=True)
        
        # Enable the firewall
        subprocess.run(['sudo', 'pfctl', '-e'], check=True)
        
        return True
    except subprocess.CalledProcessError:
        return False

def cleanup_transparent_proxy():
    """Cleanup transparent proxy settings."""
    if platform.system() != 'Darwin':
        return
    
    try:
        # Disable firewall
        subprocess.run(['sudo', 'pfctl', '-d'], check=False)
        # Reset IP forwarding
        subprocess.run(['sudo', 'sysctl', '-w', 'net.inet.ip.forwarding=0'], check=False)
    except:
        pass

def main():
    # Parse arguments
    args = sys.argv[1:]
    
    if len(args) < 2:
        print("Usage: sgtm-debug <domain> <header_value> [options]")
        print("Example: sgtm-debug example.com ZW52LWRldjEyMzQ1")
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
    
    print(f"🚀 Starting SGTM debug session for domain: {domain}")
    print(f"📝 Header value: {header_value}")
    
    # Create the mitmproxy script
    script_path = create_mitmproxy_script(domain, header_value)
    
    # Setup signal handler for cleanup
    def signal_handler(sig, frame):
        print("\n⏹️  Stopping SGTM debug session...")
        cleanup_transparent_proxy()
        try:
            os.unlink(script_path)
        except OSError:
            pass
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if use_proxy:
            # Manual proxy mode
            print("🔧 Configure your browser to use proxy: 127.0.0.1:8080")
            if use_web:
                print("🌐 Web interface: http://127.0.0.1:8081")
            print("⏹️  Press Ctrl+C to stop\n")
            
            cmd = [
                'mitmweb' if use_web else 'mitmdump',
                '--listen-port', '8080',
                '--script', script_path,
                '--set', 'confdir=~/.mitmproxy'
            ]
            
            if use_web:
                cmd.extend(['--web-port', '8081'])
                
        elif use_transparent:
            # Transparent proxy mode (default)
            print("📡 Setting up transparent proxy...")
            
            if setup_transparent_proxy():
                print("✅ Transparent proxy enabled")
                if use_web:
                    print("🌐 Web interface: http://127.0.0.1:8081")
                print("📱 All HTTP/HTTPS traffic will be intercepted automatically")
                print("⏹️  Press Ctrl+C to stop\n")
                
                cmd = [
                    'mitmweb' if use_web else 'mitmdump',
                    '--listen-port', '8080',
                    '--script', script_path,
                    '--set', 'confdir=~/.mitmproxy',
                    '--mode', 'transparent'
                ]
                
                if use_web:
                    cmd.extend(['--web-port', '8081'])
                    
            else:
                print("❌ Could not setup transparent proxy. Falling back to manual proxy mode.")
                print("🔧 Configure your browser to use proxy: 127.0.0.1:8080")
                if use_web:
                    print("🌐 Web interface: http://127.0.0.1:8081")
                print("⏹️  Press Ctrl+C to stop\n")
                
                cmd = [
                    'mitmweb' if use_web else 'mitmdump',
                    '--listen-port', '8080',
                    '--script', script_path,
                    '--set', 'confdir=~/.mitmproxy'
                ]
                
                if use_web:
                    cmd.extend(['--web-port', '8081'])
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n⏹️  Stopping SGTM debug session...")
    except FileNotFoundError:
        print("❌ Error: mitmproxy not found. Please install it with: brew install mitmproxy")
        sys.exit(1)
    finally:
        # Clean up
        cleanup_transparent_proxy()
        try:
            os.unlink(script_path)
        except OSError:
            pass

if __name__ == "__main__":
    main()