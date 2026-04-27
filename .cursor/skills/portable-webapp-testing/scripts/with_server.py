#!/usr/bin/env python3
"""
Start one or more local servers, wait for their ports, run a command, then clean up.

Examples:
    python scripts/with_server.py --server "npm run dev" --port 5173 -- python automation.py
    python scripts/with_server.py --server "cd backend && python server.py" --port 3000 \
      --server "cd frontend && npm run dev" --port 5173 -- python test.py
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def is_server_ready(host: str, port: int, timeout: int) -> bool:
    """Wait for a TCP listener to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command with one or more local servers")
    parser.add_argument("--server", action="append", dest="servers", required=True, help="Server command; can be repeated")
    parser.add_argument("--port", action="append", dest="ports", type=int, required=True, help="Port for each server; must match --server count")
    parser.add_argument("--host", default="localhost", help="Host to poll for readiness; default: localhost")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds per server; default: 30")
    parser.add_argument("--log-dir", default=os.environ.get("OUTPUT_DIR", "./test-results"), help="Directory for server logs; default: OUTPUT_DIR or ./test-results")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after servers are ready")

    args = parser.parse_args()

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if not args.command:
        print("Error: no command specified to run", file=sys.stderr)
        return 1

    if len(args.servers) != len(args.ports):
        print("Error: number of --server and --port arguments must match", file=sys.stderr)
        return 1

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    server_processes: list[tuple[subprocess.Popen[bytes], object]] = []

    try:
        for index, (cmd, port) in enumerate(zip(args.servers, args.ports), start=1):
            log_path = log_dir / f"server-{index}.log"
            log_file = log_path.open("wb")
            print(f"Starting server {index}/{len(args.servers)}: {cmd}")
            print(f"Server {index} log: {log_path}")

            process = subprocess.Popen(cmd, shell=True, stdout=log_file, stderr=subprocess.STDOUT)
            server_processes.append((process, log_file))

            print(f"Waiting for {args.host}:{port}...")
            if not is_server_ready(args.host, port, args.timeout):
                raise RuntimeError(f"Server failed to start on {args.host}:{port} within {args.timeout}s")
            print(f"Server ready on {args.host}:{port}")

        print(f"\nAll {len(server_processes)} server(s) ready")
        print(f"Running: {' '.join(args.command)}\n")
        result = subprocess.run(args.command)
        return result.returncode

    finally:
        print(f"\nStopping {len(server_processes)} server(s)...")
        for index, (process, log_file) in enumerate(server_processes, start=1):
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            finally:
                log_file.close()
            print(f"Server {index} stopped")
        print("All servers stopped")


if __name__ == "__main__":
    raise SystemExit(main())
