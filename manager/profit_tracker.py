"""
Profit Tracker - Parse logs and calculate trading profits
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class Trade:
    """Represents a single trade"""
    def __init__(self, timestamp: datetime, pair: str, amount_in: float,
                 amount_out: float, route: str, success: bool, 
                 jito_tip: float = 0, tx_fee: float = 0.000005,
                 net_profit: Optional[float] = None):
        self.timestamp = timestamp
        self.pair = pair
        self.amount_in = amount_in
        self.amount_out = amount_out
        self.route = route
        self.success = success
        self.jito_tip = jito_tip
        self.tx_fee = tx_fee
        self._net_profit = net_profit
        
    @property
    def gross_profit(self) -> float:
        """Profit before fees"""
        if not self.success:
            return 0
        return self.amount_out - self.amount_in
    
    @property
    def net_profit(self) -> float:
        """Profit after fees"""
        if self._net_profit is not None:
            return self._net_profit
        if not self.success:
            return -self.tx_fee - self.jito_tip
        return self.gross_profit - self.tx_fee - self.jito_tip
    
    @property
    def profit_percent(self) -> float:
        """Profit as percentage"""
        if self.amount_in == 0:
            return 0
        return (self.net_profit / self.amount_in) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "pair": self.pair,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "route": self.route,
            "success": self.success,
            "jito_tip": self.jito_tip,
            "tx_fee": self.tx_fee,
            "gross_profit": self.gross_profit,
            "net_profit": self.net_profit,
            "profit_percent": self.profit_percent
        }


import fcntl
import os

class ProfitTracker:
    """Track and analyze trading profits"""
    
    def __init__(self, history_file: str = "logs/profits.json", log_file: str = "logs/notarb.log", state_file: str = "logs/monitor.state"):
        self.history_file = Path(history_file)
        self.log_file = Path(log_file)
        self.state_file = Path(state_file)
        self.trades: List[Trade] = []
        self.load_history()
        self._log_file_handle = None

    def load_history(self):
        """Load trade history from JSON file"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                for item in data:
                    trade = Trade(
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        pair=item['pair'],
                        amount_in=item['amount_in'],
                        amount_out=item['amount_out'],
                        route=item['route'],
                        success=item['success'],
                        jito_tip=item.get('jito_tip', 0),
                        tx_fee=item.get('tx_fee', 0.000005),
                        net_profit=item.get('net_profit')
                    )
                    self.trades.append(trade)
        except Exception as e:
            print(f"Warning: Could not load trade history: {e}")
    
    def save_history(self):
        """Save trade history to JSON file"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.history_file, 'w') as f:
            data = [trade.to_dict() for trade in self.trades]
            json.dump(data, f, indent=2)
    
    def add_trade(self, trade: Trade):
        """Add a new trade"""
        self.trades.append(trade)
        self.save_history()

    def _get_last_pos(self) -> int:
        """Read last processed file position"""
        if not self.state_file.exists():
            return 0
        try:
            with open(self.state_file, 'r') as f:
                return int(f.read().strip())
        except:
            return 0

    def _save_last_pos(self, pos: int):
        """Save last processed file position"""
        with open(self.state_file, 'w') as f:
            f.write(str(pos))

    def update(self):
        """Read new log lines and parse trades (thread/process safe)"""
        if not self.log_file.exists():
            return

        # Use a lock file to ensure only one process updates at a time
        lock_path = self.state_file.with_suffix('.lock')
        with open(lock_path, 'w') as lock_file:
            try:
                # Acquire exclusive lock (non-blocking)
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Read last position
                last_pos = self._get_last_pos()
                
                # Open log file
                with open(self.log_file, 'r') as f:
                    # Check if file was rotated (size smaller than last pos)
                    f.seek(0, 2)
                    current_size = f.tell()
                    
                    if current_size < last_pos:
                        last_pos = 0 # File rotated
                    
                    if current_size == last_pos:
                        return # Nothing new
                        
                    f.seek(last_pos)
                    new_lines = f.readlines()
                    new_pos = f.tell()
                
                # Parse lines
                if new_lines:
                    for line in new_lines:
                        self.parse_log_line(line)
                    
                    # Save new position
                    self._save_last_pos(new_pos)
                    
            except BlockingIOError:
                # Another process is updating, just skip
                pass
            except Exception as e:
                print(f"Error updating profits: {e}")
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def parse_log_line(self, line: str):
        """Parse a single log line for trade info"""
        # Example patterns (adjust based on actual logs):
        # "Swap success! Profit: 0.001 SOL"
        # "Arbitrage executed. Net: 0.005 SOL"
        
        try:
            line_lower = line.lower()
            if "profit" in line_lower and "sol" in line_lower:
                # Try to extract profit amount
                # Look for: "Profit: 0.123 SOL" or "Profit 0.123"
                profit_match = re.search(r'profit[:\s]+([+\-]?\d+\.?\d*)', line_lower)
                if profit_match:
                    profit = float(profit_match.group(1))
                    
                    # Try to extract pair
                    # Look for "SOL/USDC" or "SOL-USDC"
                    pair = "Unknown"
                    pair_match = re.search(r'([a-z0-9]+)[/-]([a-z0-9]+)', line_lower)
                    if pair_match:
                        pair = f"{pair_match.group(1).upper()}-{pair_match.group(2).upper()}"
                    
                    # Create trade object
                    trade = Trade(
                        timestamp=datetime.now(), # Use current time as approx
                        pair=pair,
                        amount_in=0, # Unknown from simple log
                        amount_out=0, # Unknown
                        route="Unknown",
                        success=True,
                        net_profit=profit # Assuming log shows net
                    )
                    
                    # Add trade
                    self.add_trade(trade)
                    
        except Exception:
            pass
    
    def get_stats(self, period: Optional[str] = None) -> Dict:
        """
        Get statistics for a time period
        period: '1h', '24h', '7d', '30d', or None for all-time
        """
        trades = self._filter_by_period(period)
        
        if not trades:
            return {
                'total_trades': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'success_rate': 0,
                'gross_profit': 0,
                'total_fees': 0,
                'net_profit': 0,
                'avg_profit_per_trade': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        successful = [t for t in trades if t.success]
        failed = [t for t in trades if not t.success]
        
        gross_profit = sum(t.gross_profit for t in trades)
        total_fees = sum(t.tx_fee + t.jito_tip for t in trades)
        net_profit = sum(t.net_profit for t in trades)
        
        profits = [t.net_profit for t in trades]
        
        return {
            'total_trades': len(trades),
            'successful_trades': len(successful),
            'failed_trades': len(failed),
            'success_rate': (len(successful) / len(trades)) * 100 if trades else 0,
            'gross_profit': gross_profit,
            'total_fees': total_fees,
            'net_profit': net_profit,
            'avg_profit_per_trade': net_profit / len(trades) if trades else 0,
            'best_trade': max(profits) if profits else 0,
            'worst_trade': min(profits) if profits else 0
        }
    
    def get_fee_stats(self, period: Optional[str] = None) -> Dict:
        """
        Get detailed fee statistics for a time period
        period: '1h', '24h', '7d', '30d', or None for all-time
        """
        trades = self._filter_by_period(period)
        
        if not trades:
            return {
                'total_fees': 0,
                'total_jito_tips': 0,
                'total_tx_fees': 0,
                'avg_fees_per_trade': 0,
                'avg_jito_tip': 0,
                'avg_tx_fee': 0,
                'total_trades': 0
            }
        
        total_fees = sum(t.tx_fee + t.jito_tip for t in trades)
        total_jito_tips = sum(t.jito_tip for t in trades)
        total_tx_fees = sum(t.tx_fee for t in trades)
        total_trades = len(trades)
        
        avg_fees_per_trade = total_fees / total_trades if total_trades > 0 else 0
        avg_jito_tip = total_jito_tips / total_trades if total_trades > 0 else 0
        avg_tx_fee = total_tx_fees / total_trades if total_trades > 0 else 0
        
        return {
            'total_fees': total_fees,
            'total_jito_tips': total_jito_tips,
            'total_tx_fees': total_tx_fees,
            'avg_fees_per_trade': avg_fees_per_trade,
            'avg_jito_tip': avg_jito_tip,
            'avg_tx_fee': avg_tx_fee,
            'total_trades': total_trades
        }
    
    def get_top_pairs(self, limit: int = 5, period: Optional[str] = None) -> List[Dict]:
        """Get most profitable trading pairs"""
        trades = self._filter_by_period(period)
        
        # Group by pair
        pairs = {}
        for trade in trades:
            if trade.pair not in pairs:
                pairs[trade.pair] = {
                    'pair': trade.pair,
                    'trades': [],
                    'total_profit': 0,
                    'success_count': 0
                }
            pairs[trade.pair]['trades'].append(trade)
            pairs[trade.pair]['total_profit'] += trade.net_profit
            if trade.success:
                pairs[trade.pair]['success_count'] += 1
        
        # Calculate stats and sort
        result = []
        for pair_data in pairs.values():
            trades_list = pair_data['trades']
            result.append({
                'pair': pair_data['pair'],
                'count': len(trades_list),
                'total_profit': pair_data['total_profit'],
                'avg_profit': pair_data['total_profit'] / len(trades_list),
                'success_rate': (pair_data['success_count'] / len(trades_list)) * 100
            })
        
        result.sort(key=lambda x: x['total_profit'], reverse=True)
        return result[:limit]
    
    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """Get most recent trades"""
        return sorted(self.trades, key=lambda t: t.timestamp, reverse=True)[:limit]
    
    def _filter_by_period(self, period: Optional[str]) -> List[Trade]:
        """Filter trades by time period"""
        if period is None:
            return self.trades
        
        now = datetime.now()
        
        # Parse period
        if period.endswith('h'):
            hours = int(period[:-1])
            cutoff = now - timedelta(hours=hours)
        elif period.endswith('d'):
            days = int(period[:-1])
            cutoff = now - timedelta(days=days)
        else:
            return self.trades
        
        return [t for t in self.trades if t.timestamp >= cutoff]
    
    def export_csv(self, filename: str, period: Optional[str] = None):
        """Export trades to CSV"""
        import csv
        
        trades = self._filter_by_period(period)
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'pair', 'amount_in', 'amount_out', 
                'route', 'success', 'net_profit', 'profit_percent'
            ])
            writer.writeheader()
            
            for trade in trades:
                writer.writerow({
                    'timestamp': trade.timestamp.isoformat(),
                    'pair': trade.pair,
                    'amount_in': trade.amount_in,
                    'amount_out': trade.amount_out,
                    'route': trade.route,
                    'success': trade.success,
                    'net_profit': trade.net_profit,
                    'profit_percent': trade.profit_percent
                })
