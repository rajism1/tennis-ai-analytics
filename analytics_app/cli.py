"""
CLI Entry Point for Module 2: Analytics Engine & Web Dashboard Module
"""

import argparse
import os
from .reporter import run_standalone_reporter
from .server import run_server

def main():
    parser = argparse.ArgumentParser(description="Module 2: Analytics Engine & Web Dashboard")
    parser.add_argument("--data", type=str, default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "tennis_match_analytics.json"), help="Path to input JSON telemetry")
    parser.add_argument("--port", type=int, default=8080, help="Web dashboard server port")
    parser.add_argument("--reporter-only", action="store_true", help="Run standalone reporter CLI without web server")
    args = parser.parse_args()

    if args.reporter_only:
        run_standalone_reporter(args.data)
    else:
        run_server(port=args.port)

if __name__ == "__main__":
    main()
