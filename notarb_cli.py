#!/usr/bin/env python3
"""
NotArb CLI Dashboard
Real-time monitoring and control center for the terminal.
"""
import sys
import signal
from rich.console import Console
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from manager.dashboard_ui import DashboardUI
from manager.profit_tracker import ProfitTracker
from manager.log_monitor import LogMonitor

def handle_sigint(signum, frame):
    """Handle Ctrl+C gracefully"""
    sys.exit(0)

def main():
    # Setup signal handler
    signal.signal(signal.SIGINT, handle_sigint)
    
    console = Console()
    
    try:
        # Initialize components
        profit_tracker = ProfitTracker()
        log_monitor = LogMonitor()
        ui = DashboardUI(profit_tracker, log_monitor)
        
        # Run interactive dashboard
        ui.run()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
