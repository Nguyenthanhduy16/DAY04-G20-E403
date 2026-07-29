from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from env_loader import load_lab_env

def main() -> None:
    load_lab_env(ROOT)
    print("=== Starting Deployment Helper ===")

    # 1. Start Streamlit App
    print("1. Starting Streamlit application on port 8501...")
    streamlit_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        "8501",
        "--server.address",
        "localhost",
    ]
    
    streamlit_proc = subprocess.Popen(
        streamlit_cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Give Streamlit 3 seconds to start
    time.sleep(3)
    if streamlit_proc.poll() is not None:
        print("Error: Streamlit failed to start. Output:")
        print(streamlit_proc.stdout.read())
        sys.exit(1)
    
    print("Streamlit successfully started at http://localhost:8501")

    # 2. Try starting Cloudflare Tunnel
    print("\n2. Attempting to start Cloudflare Tunnel (cloudflared)...")
    try:
        tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print("[WARNING] 'cloudflared' command not found.")
        print("To expose the app to other teams, install Cloudflare Tunnel:")
        print(" - Windows (winget): winget install --id Cloudflare.cloudflared")
        print(" - macOS (brew): brew install cloudflared")
        print(" - Linux: Follow official Cloudflare guide")
        print("\nYou can still access the app locally at http://localhost:8501")
        
        # Keep waiting for streamlit to finish
        try:
            streamlit_proc.wait()
        except KeyboardInterrupt:
            streamlit_proc.terminate()
            print("\nStopped Streamlit.")
        return

    # Parse cloudflared stderr/stdout to find the trycloudflare URL
    tunnel_url = None
    try:
        # We need to read lines from stderr since cloudflared prints logs to stderr
        print("Waiting for Cloudflare Tunnel URL...")
        for line in iter(tunnel_proc.stderr.readline, ""):
            print(f"[cloudflared] {line.strip()}")
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                tunnel_url = match.group(0)
                print("\n" + "="*60)
                print(f"🎉 DEPLOYMENT SUCCESSFUL!")
                print(f"Local URL:  http://localhost:8501")
                print(f"Public URL: {tunnel_url}")
                print("="*60 + "\n")
                break
        
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        tunnel_proc.terminate()
        streamlit_proc.terminate()
        print("Services stopped.")

if __name__ == "__main__":
    main()
