#!/usr/bin/env python3
"""
LEGO Portfolio Analyzer
Tracks holdings, ROI, and rebalancing signals
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

PORTFOLIO_FILE = Path(__file__).parent.parent / "data" / "lego_portfolio.json"

class PortfolioAnalyzer:
    def __init__(self):
        with open(PORTFOLIO_FILE) as f:
            self.data = json.load(f)
    
    def get_metrics(self) -> dict:
        """Get portfolio health metrics"""
        holdings = self.data["holdings"]
        
        total_cost = sum(h["cost_basis"] * h["quantity"] for h in holdings)
        total_value = sum(h["current_market_price"] * h["quantity"] for h in holdings)
        
        profits = [h for h in holdings if h["roi_percent"] > 0]
        losses = [h for h in holdings if h["roi_percent"] < 0]
        
        return {
            "total_holdings": len(holdings),
            "total_cost_basis": total_cost,
            "total_current_value": total_value,
            "total_gain": total_value - total_cost,
            "portfolio_roi_pct": round((total_value - total_cost) / total_cost * 100, 1),
            "profitable_count": len(profits),
            "loss_count": len(losses),
            "success_rate_pct": round(len(profits) / len(holdings) * 100, 1),
        }
    
    def get_sell_signals(self, roi_threshold: float = 50) -> list:
        """Get holdings that hit ROI target (suggest selling)"""
        holdings = self.data["holdings"]
        sells = [
            {
                "name": h["name"],
                "cost": h["cost_basis"],
                "current_value": h["current_market_price"],
                "roi_pct": h["roi_percent"],
                "hold_days": h["hold_duration_days"],
                "action": "SELL - Target achieved",
            }
            for h in holdings if h["roi_percent"] >= roi_threshold
        ]
        return sells
    
    def get_hold_signals(self) -> list:
        """Get holdings that are performing well (hold)"""
        holdings = self.data["holdings"]
        holds = [
            {
                "name": h["name"],
                "roi_pct": h["roi_percent"],
                "days_held": h["hold_duration_days"],
                "action": "HOLD - Momentum good",
            }
            for h in holdings if 10 <= h["roi_percent"] < 50
        ]
        return holds
    
    def get_watch_signals(self) -> list:
        """Get holdings that underperform (watch)"""
        holdings = self.data["holdings"]
        watches = [
            {
                "name": h["name"],
                "roi_pct": h["roi_percent"],
                "days_held": h["hold_duration_days"],
                "action": "WATCH - Below target" if h["roi_percent"] > -15 else "CONSIDER SELLING - Negative",
            }
            for h in holdings if h["roi_percent"] < 10
        ]
        return watches
    
    def print_report(self):
        """Print portfolio report"""
        metrics = self.get_metrics()
        
        print("=" * 70)
        print("LEGO PORTFOLIO REPORT")
        print("=" * 70)
        
        print(f"\n📊 PORTFOLIO METRICS:")
        print(f"  Total Holdings: {metrics['total_holdings']}")
        print(f"  Cost Basis: ${metrics['total_cost_basis']:,}")
        print(f"  Current Value: ${metrics['total_current_value']:,}")
        print(f"  Gain/Loss: ${metrics['total_gain']:+,}")
        print(f"  Portfolio ROI: {metrics['portfolio_roi_pct']:.1f}%")
        print(f"  Success Rate: {metrics['success_rate_pct']:.1f}% ({metrics['profitable_count']}/{metrics['total_holdings']})")
        
        sells = self.get_sell_signals(50)
        if sells:
            print(f"\n🟢 SELL SIGNALS (ROI >= 50%):")
            for s in sells:
                print(f"  {s['name']}: {s['roi_pct']:.1f}% gain")
        
        holds = self.get_hold_signals()
        if holds:
            print(f"\n🟡 HOLD (10-50% ROI):")
            for h in holds:
                print(f"  {h['name']}: {h['roi_pct']:.1f}% gain")
        
        watches = self.get_watch_signals()
        if watches:
            print(f"\n🔵 WATCH (< 10% ROI):")
            for w in watches:
                print(f"  {w['name']}: {w['roi_pct']:.1f}% gain - {w['action']}")
        
        print("\n" + "=" * 70)


if __name__ == "__main__":
    analyzer = PortfolioAnalyzer()
    analyzer.print_report()
