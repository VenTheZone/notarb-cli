"""
Dashboard UI - Rich terminal interface for monitoring
"""
import subprocess
import psutil
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from datetime import datetime
import time
from typing import Optional

from .profit_tracker import ProfitTracker
from .log_monitor import LogMonitor


class DashboardUI:
    """Interactive dashboard for NotArb MEV bot"""
    
    def __init__(self, profit_tracker: ProfitTracker, log_monitor: LogMonitor):
        self.console = Console()
        self.profit_tracker = profit_tracker
        self.log_monitor = log_monitor
        self.current_view = "dashboard"
        self.log_source = "bot"
        self.navigation_stack = ["dashboard"]  # Track navigation history
    
    def get_view_display_name(self, view: str) -> str:
        """Get user-friendly display name for a view"""
        view_names = {
            "dashboard": "Dashboard",
            "logs": "Bot Logs",
            "profit": "Profit Report", 
            "fees": "Fees Report"
        }
        return view_names.get(view, view.title())
    
    def render_breadcrumbs(self) -> Panel:
        """Render navigation breadcrumbs"""
        if len(self.navigation_stack) <= 1:
            breadcrumb_text = f"[bold]🏠[/bold] {self.get_view_display_name(self.current_view)}"
        else:
            breadcrumb_parts = []
            for i, view in enumerate(self.navigation_stack):
                if i == 0:
                    breadcrumb_parts.append(f"[link]🏠 Home[/link]")
                else:
                    breadcrumb_parts.append(f"[dim]>[/dim] {self.get_view_display_name(view)}")
            
            breadcrumb_text = " ".join(breadcrumb_parts)
        
        return Panel(
            Text(breadcrumb_text, style="bold"),
            style="dim",
            border_style="dim"
        )
    
    def check_process(self, pattern: str) -> bool:
        """Check if a process matching pattern is running"""
        try:
            return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0
        except Exception:
            return False
    
    def get_process_info(self, name_pattern: str) -> Optional[dict]:
        """Get process info by name pattern"""
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline())
                if name_pattern in cmdline:
                    return {
                        'pid': proc.info['pid'],
                        'cpu': proc.info['cpu_percent'],
                        'memory': proc.info['memory_info'].rss / 1024 / 1024  # MB
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def render_status_panel(self) -> Panel:
        """Render system status panel"""
        # Check processes
        bot_running = self.check_process("task=onchain-bot")
        
        # Build status text
        status_table = Table.grid(padding=(0, 2))
        status_table.add_column(style="bold")
        status_table.add_column()
        
        # Bot status
        bot_status = "[green]●[/green] RUNNING" if bot_running else "[red]●[/red] STOPPED"
        status_table.add_row("MEV Bot:", bot_status)
        
        # Simulation mode (check config - simplified for now)
        status_table.add_row("Mode:", "[yellow]ON-CHAIN[/yellow]")
        
        return Panel(status_table, title="[bold cyan]Status[/bold cyan]", border_style="cyan")
    
    def render_profit_panel(self, period: str = "24h") -> Panel:
        """Render profit summary panel"""
        stats = self.profit_tracker.get_stats(period)
        fee_stats = self.profit_tracker.get_fee_stats(period)
        
        profit_table = Table.grid(padding=(0, 2))
        profit_table.add_column(style="bold")
        profit_table.add_column(justify="right")
        
        # Trade counts
        total = stats['total_trades']
        successful = stats['successful_trades']
        failed = stats['failed_trades']
        success_rate = stats['success_rate']
        
        profit_table.add_row("Total Trades:", str(total))
        profit_table.add_row(
            "Success Rate:",
            f"[green]{successful}[/green] / [red]{failed}[/red] ({success_rate:.1f}%)"
        )
        profit_table.add_row("", "")
        
        # Profits
        gross = stats['gross_profit']
        fees = fee_stats['total_fees']
        jito_tips = fee_stats['total_jito_tips']
        tx_fees = fee_stats['total_tx_fees']
        net = stats['net_profit']
        
        net_color = "green" if net > 0 else "red"
        profit_table.add_row("Gross Profit:", f"{gross:.6f} SOL")
        profit_table.add_row("Jito Tips:", f"{jito_tips:.6f} SOL")
        profit_table.add_row("TX Fees:", f"{tx_fees:.6f} SOL")
        profit_table.add_row("Total Fees:", f"{fees:.6f} SOL")
        profit_table.add_row("Net Profit:", f"[{net_color}]{net:+.6f} SOL[/{net_color}]")
        
        if total > 0:
            avg = stats['avg_profit_per_trade']
            avg_fees = fees / total if total > 0 else 0
            profit_table.add_row("Avg/Trade:", f"{avg:.6f} SOL")
            profit_table.add_row("Avg Fees/Trade:", f"{avg_fees:.6f} SOL")
        
        title = f"[bold green]Profit Summary[/bold green] ({period})"
        return Panel(profit_table, title=title, border_style="green")
    
    def render_recent_activity_panel(self, limit: int = 5) -> Panel:
        """Render recent trades panel"""
        recent_trades = self.profit_tracker.get_recent_trades(limit)
        
        if not recent_trades:
            no_trades = Text("No trades yet", style="dim italic")
            return Panel(no_trades, title="[bold yellow]Recent Activity[/bold yellow]", 
                        border_style="yellow")
        
        activity_text = Text()
        for trade in recent_trades:
            timestamp = trade.timestamp.strftime("%H:%M:%S")
            icon = "✅" if trade.success else "❌"
            profit_color = "green" if trade.net_profit > 0 else "red"
            
            activity_text.append(f"{timestamp} ", style="dim")
            activity_text.append(f"{icon} ")
            activity_text.append(f"{trade.pair}", style="cyan")
            activity_text.append(" | ", style="dim")
            activity_text.append(
                f"{trade.net_profit:+.6f} SOL",
                style=profit_color
            )
            if trade.route:
                activity_text.append(f" | {trade.route}", style="dim")
            activity_text.append("\n")
        
        return Panel(activity_text, title="[bold yellow]Recent Activity[/bold yellow]",
                    border_style="yellow")
    
    def render_top_pairs_panel(self, limit: int = 5) -> Panel:
        """Render top performing pairs"""
        top_pairs = self.profit_tracker.get_top_pairs(limit, "24h")
        
        if not top_pairs:
            no_pairs = Text("No data yet", style="dim italic")
            return Panel(no_pairs, title="[bold magenta]Top Pairs (24h)[/bold magenta]",
                        border_style="magenta")
        
        pairs_table = Table(show_header=False, box=None, padding=(0, 1))
        pairs_table.add_column("Rank", style="dim", width=2)
        pairs_table.add_column("Pair", style="cyan")
        pairs_table.add_column("Trades", justify="right", style="dim")
        pairs_table.add_column("Profit", justify="right")
        
        for i, pair in enumerate(top_pairs, 1):
            profit_color = "green" if pair['total_profit'] > 0 else "red"
            pairs_table.add_row(
                str(i),
                pair['pair'],
                f"{pair['count']} trades",
                f"[{profit_color}]{pair['total_profit']:+.5f}[/{profit_color}]"
            )
        
        return Panel(pairs_table, title="[bold magenta]Top Pairs (24h)[/bold magenta]",
                    border_style="magenta")
    
    def render_fees_panel(self, period: str = "24h") -> Panel:
        """Render detailed fees and expenses panel"""
        stats = self.profit_tracker.get_stats(period)
        fee_stats = self.profit_tracker.get_fee_stats(period)
        
        fees_table = Table.grid(padding=(0, 2))
        fees_table.add_column(style="bold")
        fees_table.add_column(justify="right")
        
        # Fee breakdown
        total_fees = fee_stats['total_fees']
        jito_tips = fee_stats['total_jito_tips']
        tx_fees = fee_stats['total_tx_fees']
        
        fees_table.add_row("Total Fees:", f"{total_fees:.6f} SOL")
        fees_table.add_row("Jito Tips:", f"{jito_tips:.6f} SOL")
        fees_table.add_row("Transaction Fees:", f"{tx_fees:.6f} SOL")
        fees_table.add_row("", "")
        
        # Fee ratios
        total_trades = stats['total_trades']
        gross_profit = stats['gross_profit']
        
        if gross_profit > 0:
            fee_ratio = (total_fees / gross_profit) * 100
            fees_table.add_row("Fees/Gross Profit:", f"{fee_ratio:.2f}%")
        else:
            fees_table.add_row("Fees/Gross Profit:", "N/A")
        
        if total_trades > 0:
            avg_jito = fee_stats['avg_jito_tip']
            avg_tx = fee_stats['avg_tx_fee']
            avg_total = fee_stats['avg_fees_per_trade']
            
            fees_table.add_row("Avg Jito Tip/Trade:", f"{avg_jito:.6f} SOL")
            fees_table.add_row("Avg TX Fee/Trade:", f"{avg_tx:.6f} SOL")
            fees_table.add_row("Avg Total Fees/Trade:", f"{avg_total:.6f} SOL")
        
        fees_table.add_row("", "")
        fees_table.add_row("Total Trades:", str(total_trades))
        
        title = f"[bold red]Fees & Expenses[/bold red] ({period})"
        return Panel(fees_table, title=title, border_style="red")
    
    def render_footer_menu(self) -> Panel:
        """Render navigation menu based on current view"""
        menu = Text()

        if self.current_view == "dashboard":
            menu.append("[L]", style="bold cyan")
            menu.append("ogs ", style="dim")
            menu.append("[P]", style="bold green")
            menu.append("rofit ", style="dim")
            menu.append("[F]", style="bold red")
            menu.append("ees ", style="dim")
            menu.append("[S]", style="bold yellow")
            menu.append("tats ", style="dim")
            menu.append("[B]", style="bold blue")
            menu.append("ot(Toggle) ", style="dim")
            menu.append("[Q]", style="bold magenta")
            menu.append("uit", style="dim")
        else:
            menu.append("[B]", style="bold blue")
            menu.append("ack ", style="dim")
            menu.append("[H]", style="bold yellow")
            menu.append("ome ", style="dim")
            menu.append("[Q]", style="bold magenta")
            menu.append("uit", style="dim")

        return Panel(menu, style="dim")

    def render_common_layout(self, content_panel: Panel) -> Layout:
        """Create common layout with header, breadcrumbs, content, and footer"""
        layout = Layout()

        header = Panel(
            Text("NotArb MEV Bot Dashboard", justify="center", style="bold magenta"),
            style="magenta"
        )

        breadcrumbs = self.render_breadcrumbs()

        layout.split_column(
            Layout(header, size=2),
            Layout(breadcrumbs, size=2),
            Layout(content_panel, name="body"),
            Layout(self.render_footer_menu(), size=3)
        )

        return layout

    def render_logs_panel(self, lines: int = 15) -> Panel:
        """Render recent logs"""
        log_lines = self.log_monitor.tail_logs(self.log_source, lines)

        log_text = Text()
        for icon, color, line in log_lines:
            if icon:
                log_text.append(f"{icon} ", style=color)
            log_text.append(line, style=color if color != "white" else "")
            log_text.append("\n")

        source_name = "Bot" if self.log_source == "bot" else "Jupiter"
        title = f"[bold blue]{source_name}  Logs[/bold blue]"
        return Panel(log_text, title=title, border_style="blue")
    
    def render_dashboard(self) -> Layout:
        """Render main dashboard layout"""
        layout = Layout()
        
        # Create header with breadcrumbs
        breadcrumbs = self.render_breadcrumbs()
        
        header = Panel(
            Text("NotArb MEV Bot Dashboard", justify="center", style="bold magenta"),
            style="magenta"
        )
        
        # Create main sections
        layout.split_column(
            Layout(header, size=2),
            Layout(breadcrumbs, size=2),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into left and right
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Left column: Status + Profit + Top Pairs
        layout["left"].split_column(
            Layout(self.render_status_panel(), size=7),
            Layout(self.render_profit_panel(), size=11),
            Layout(self.render_top_pairs_panel())
        )
        
        # Right column: Recent Activity + Fees + Logs
        layout["right"].split_column(
            Layout(self.render_recent_activity_panel(), size=8),
            Layout(self.render_fees_panel(), size=7),
            Layout(self.render_logs_panel())
        )
        
        # Footer with enhanced menu
        menu = Text()
        
        if self.current_view == "dashboard":
            menu.append("[L]", style="bold cyan")
            menu.append("ogs ", style="dim")
            menu.append("[P]", style="bold green")
            menu.append("rofit ", style="dim")
            menu.append("[F]", style="bold red")
            menu.append("ees ", style="dim")
            menu.append("[S]", style="bold yellow")
            menu.append("tats ", style="dim")
            menu.append("[B]", style="bold blue")
            menu.append("ot(Toggle) ", style="dim")
            menu.append("[Q]", style="bold magenta")
            menu.append("uit", style="dim")
        else:
            menu.append("[B]", style="bold blue")
            menu.append("ack ", style="dim")
            menu.append("[H]", style="bold yellow")
            menu.append("ome ", style="dim")
            menu.append("[Q]", style="bold magenta")
            menu.append("uit", style="dim")
        
        footer_panel = Panel(menu, style="dim")
        layout["footer"].update(footer_panel)
        
        return layout
    
    def render_full_logs(self) -> Layout:
        """Render full-screen logs view"""
        log_lines = self.log_monitor.tail_logs(self.log_source, 30)

        log_text = Text()
        for icon, color, line in log_lines:
            if icon:
                log_text.append(f"{icon} ", style=color)
            log_text.append(line, style=color if color != "white" else "")
            log_text.append("\n")

        source_name = "Bot" if self.log_source == "bot" else "Jupiter"
        title = f"[bold blue]{source_name} Logs[/bold blue]"
        logs_panel = Panel(log_text, title=title, border_style="blue")

        return self.render_common_layout(logs_panel)
    
    def render_fees_report(self) -> Layout:
        """Render detailed fees report"""
        fee_stats = self.profit_tracker.get_fee_stats("24h")
        stats = self.profit_tracker.get_stats("24h")

        report = Text()
        report.append("Fees & Expenses Report - Last 24 Hours\n\n", style="bold red")

        # Overall fee summary
        report.append("═" * 60 + "\n", style="dim")
        report.append("FEE BREAKDOWN:\n\n", style="bold")

        total_fees = fee_stats['total_fees']
        jito_tips = fee_stats['total_jito_tips']
        tx_fees = fee_stats['total_tx_fees']
        total_trades = stats['total_trades']

        report.append(f"Total Fees:          {total_fees:.6f} SOL\n")
        report.append(f"  └─ Jito Tips:       {jito_tips:.6f} SOL\n")
        report.append(f"  └─ TX Fees:         {tx_fees:.6f} SOL\n")
        report.append("\n")

        # Averages
        if total_trades > 0:
            avg_jito = fee_stats['avg_jito_tip']
            avg_tx = fee_stats['avg_tx_fee']
            avg_total = fee_stats['avg_fees_per_trade']

            report.append("AVERAGES PER TRADE:\n\n", style="bold")
            report.append(f"Avg Jito Tip:        {avg_jito:.6f} SOL\n")
            report.append(f"Avg TX Fee:          {avg_tx:.6f} SOL\n")
            report.append(f"Avg Total Fees:      {avg_total:.6f} SOL\n")
            report.append("\n")

        # Fee efficiency
        gross_profit = stats['gross_profit']
        if gross_profit > 0:
            fee_ratio = (total_fees / gross_profit) * 100
            report.append("EFFICIENCY:\n\n", style="bold")
            report.append(f"Fees/Gross Profit:   {fee_ratio:.2f}%\n")
            report.append(f"Net Profit:          {stats['net_profit']:+.6f} SOL\n")
        else:
            report.append("EFFICIENCY:\n\n", style="bold")
            report.append(f"No gross profit to analyze\n")

        report.append("\n" + "═" * 60 + "\n\n", style="dim")
        report.append(f"Total Trades:        {total_trades}\n")
        if gross_profit > 0:
            fee_ratio = (total_fees / gross_profit) * 100
            report.append(f"Fee Impact:          ", style=("red" if fee_ratio > 10 else "yellow" if fee_ratio > 5 else "green"))
            report.append(f"{fee_ratio:.1f}% of gross profit\n", style=("red" if fee_ratio > 10 else "yellow" if fee_ratio > 5 else "green"))
        else:
            report.append(f"Fee Impact:          N/A (no gross profit)\n")

        fees_panel = Panel(report, title="[bold red]Detailed Fees Report[/bold red]",
                           border_style="red")

        return self.render_common_layout(fees_panel)
    
    def render_profit_report(self) -> Layout:
        """Render detailed profit report"""
        stats = self.profit_tracker.get_stats("24h")

        report = Text()
        report.append("Profit Report - Last 24 Hours\n\n", style="bold magenta")

        # Overall stats
        report.append("═" * 60 + "\n", style="dim")
        report.append(f"Total Trades:        {stats['total_trades']}\n")
        report.append(f"Successful:          {stats['successful_trades']} ", style="green")
        report.append(f"({stats['success_rate']:.1f}%)\n", style="green")
        report.append(f"Failed:              {stats['failed_trades']}\n", style="red")
        report.append("\n")

        # Profits
        net_color = "green" if stats['net_profit'] > 0 else "red"
        report.append(f"Gross Profit:        {stats['gross_profit']:.6f} SOL\n")
        report.append(f"Total Fees:          {stats['total_fees']:.6f} SOL\n")
        report.append(f"Net Profit:          ", style=net_color)
        report.append(f"{stats['net_profit']:+.6f} SOL\n", style=f"bold {net_color}")
        report.append("\n")

        if stats['total_trades'] > 0:
            report.append(f"Average/Trade:       {stats['avg_profit_per_trade']:.6f} SOL\n")
            report.append(f"Best Trade:          ", style="green")
            report.append(f"{stats['best_trade']:+.6f} SOL\n", style="bold green")
            report.append(f"Worst Trade:         ", style="red")
            report.append(f"{stats['worst_trade']:+.6f} SOL\n", style="bold red")

        report.append("\n" + "═" * 60 + "\n\n", style="dim")

        # Top pairs
        top_pairs = self.profit_tracker.get_top_pairs(10, "24h")
        if top_pairs:
            report.append("Top Performing Pairs:\n\n", style="bold cyan")
            for i, pair in enumerate(top_pairs, 1):
                profit_style = "green" if pair['total_profit'] > 0 else "red"
                report.append(f"{i:2d}. ", style="dim")
                report.append(f"{pair['pair']:20s} ", style="cyan")
                report.append(f"{pair['count']:3d} trades  ", style="dim")
                report.append(f"{pair['total_profit']:+.6f} SOL ", style=profit_style)
                report.append(f"({pair['success_rate']:.0f}% win)\n", style="dim")

        profit_panel = Panel(report, title="[bold green]Detailed Profit Report[/bold green]",
                            border_style="green")

        return self.render_common_layout(profit_panel)
    
    def start_jupiter(self):
        """Start Jupiter server"""
        try:
            subprocess.Popen(["./run-jupiter.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            pass

    def stop_jupiter(self):
        """Stop Jupiter server"""
        try:
            subprocess.run(["pkill", "-f", "task=jupiter-server"], check=False)
        except Exception:
            pass

    def start_bot(self):
        """Start MEV bot"""
        try:
            subprocess.Popen(["./run-bot.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            pass

    def stop_bot(self):
        """Stop MEV bot"""
        try:
            subprocess.run(["pkill", "-f", "task=onchain-bot"], check=False)
        except Exception:
            pass

    def run(self):
        """Run interactive dashboard"""
        import sys
        import select
        import tty
        import termios

        self.console.clear()
        
        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            # Set raw mode (allows reading single chars)
            tty.setcbreak(sys.stdin.fileno())
            
            with Live(self.render_dashboard(), console=self.console,
                     refresh_per_second=4, screen=True) as live:
                
                while True:
                    # Update profit tracker
                    self.profit_tracker.update()

                    # Handle input
                    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                        key = sys.stdin.read(1).lower()
                        
                        if key == 'q':
                            break
                        elif key == 'l':
                            # Navigate to logs (push to stack)
                            if self.current_view != "logs":
                                self.navigation_stack.append("logs")
                            self.current_view = "logs"
                            self.log_source = "bot"
                        elif key == 'p':
                            # Navigate to profit report (push to stack)
                            if self.current_view != "profit":
                                self.navigation_stack.append("profit")
                            self.current_view = "profit"
                        elif key == 'f':
                            # Navigate to fees report (push to stack)
                            if self.current_view != "fees":
                                self.navigation_stack.append("fees")
                            self.current_view = "fees"
                        elif key == 's':
                            # Navigate to stats/dashboard (clear stack except dashboard)
                            self.navigation_stack = ["dashboard"]
                            self.current_view = "dashboard"
                        elif key == 'h':
                            # Navigate to home/dashboard (clear stack except dashboard)
                            self.navigation_stack = ["dashboard"]
                            self.current_view = "dashboard"
                        elif key == 'b':
                            if self.current_view != "dashboard":
                                # Go back to previous view
                                if len(self.navigation_stack) > 1:
                                    self.navigation_stack.pop()  # Remove current view
                                    self.current_view = self.navigation_stack[-1]  # Go to previous
                            else:
                                # Toggle Bot when on dashboard
                                if self.check_process("task=onchain-bot"):
                                    self.stop_bot()
                                else:
                                    self.start_bot()
                    
                    # Update display
                    if self.current_view == "dashboard":
                        live.update(self.render_dashboard())
                    elif self.current_view == "logs":
                        live.update(self.render_full_logs())
                    elif self.current_view == "profit":
                        live.update(self.render_profit_report())
                    elif self.current_view == "fees":
                        live.update(self.render_fees_report())
                    
                    time.sleep(0.1)
                    
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
