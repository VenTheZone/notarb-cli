"""
Log Monitor - Monitor and parse log files in real-time
"""
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime


class LogMonitor:
    """Monitor bot and Jupiter logs"""
    
    def __init__(self, 
                 bot_log: str = "logs/notarb.log",
                 jupiter_log: str = "logs/jupiter.log"):
        self.bot_log = Path(bot_log)
        self.jupiter_log = Path(jupiter_log)
    
    def tail_logs(self, source: str = "bot", lines: int = 20) -> List[Tuple[str, str, str]]:
        """
        Tail log file and return formatted lines
        Returns list of (icon, color, text) tuples
        """
        if source == "bot":
            log_file = self.bot_log
        elif source == "jupiter":
            log_file = self.jupiter_log
        else:
            return []
        
        if not log_file.exists():
            return [("⚠️", "yellow", f"Log file not found: {log_file}")]
        
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_file)],
                capture_output=True,
                text=True,
                timeout=2
            )
            lines_list = result.stdout.strip().split('\n')
            return self.format_lines(lines_list)
        except Exception as e:
            return [("❌", "red", f"Error reading logs: {e}")]
    
    def format_lines(self, lines: List[str]) -> List[Tuple[str, str, str]]:
        """
        Add colors and icons to log lines
        Returns list of (icon, color, text) tuples
        """
        formatted = []
        for line in lines:
            if not line.strip():
                continue
                
            line_lower = line.lower()
            
            # Detect trade success
            if any(word in line_lower for word in ['success', 'executed', 'profit']):
                if 'profit' in line_lower and '+' in line:
                    formatted.append(("✅", "green", line))
                elif 'success' in line_lower:
                    formatted.append(("✅", "green", line))
                else:
                    formatted.append(("", "white", line))
            
            # Detect errors/failures
            elif any(word in line_lower for word in ['error', 'failed', 'exception']):
                formatted.append(("❌", "red", line))
            
            # Detect warnings
            elif any(word in line_lower for word in ['warn', 'warning', 'slippage']):
                formatted.append(("⚠️", "yellow", line))
            
            # Detect info about opportunities
            elif any(word in line_lower for word in ['opportunity', 'found', 'scanning']):
                formatted.append(("🔍", "cyan", line))
            
            # Default
            else:
                formatted.append(("", "white", line))
        
        return formatted
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """
        Parse recent trades from logs (basic implementation)
        This is a placeholder - customize based on actual log format
        """
        # TODO: Implement actual log parsing based on NotArb log format
        # For now, return empty list
        return []
    
    def follow_logs(self, source: str = "bot"):
        """
        Follow logs in real-time (generator)
        Use with: for line in monitor.follow_logs('bot'):
        """
        if source == "bot":
            log_file = self.bot_log
        elif source == "jupiter":
            log_file = self.jupiter_log
        else:
            return
        
        if not log_file.exists():
            return
        
        try:
            process = subprocess.Popen(
                ["tail", "-f", str(log_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line.rstrip()
        except Exception as e:
            print(f"Error following logs: {e}")
