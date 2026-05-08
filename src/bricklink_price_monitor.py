"""
BrickLink Price Monitor - Phase 2
Tracks current prices for target LEGO sets and identifies undervalued deals.
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class LEGOPricePoint:
    set_id: str
    set_name: str
    current_price: float
    price_source: str
    listed_count: int
    best_condition: str
    last_updated: str
    discount_vs_target: float  # percentage below target buy price


class BrickLinkMonitor:
    """Monitor BrickLink for LEGO set prices and deals"""

    # Simulated current market prices (would fetch from BrickLink API in production)
    CURRENT_MARKET_PRICES = {
        "10179": {"price": 3800, "condition": "Like New", "count": 2},  # Millennium Falcon
        "10030": {"price": 2200, "condition": "Good", "count": 1},     # Imperial Star Destroyer
        "10182": {"price": 2100, "condition": "Like New", "count": 1}, # Cafe Corner
        "10189": {"price": 2400, "condition": "Good", "count": 3},     # Taj Mahal
        "71040": {"price": 800, "condition": "Like New", "count": 5},  # Disney Castle
        "10185": {"price": 1600, "condition": "Good", "count": 2},     # Green Grocer
        "10217": {"price": 550, "condition": "Fair", "count": 4},      # Diagon Alley
    }

    TARGET_BUY_PRICES = {
        "10179": 3500,   # Millennium Falcon
        "10030": 2000,   # Imperial Star Destroyer
        "10182": 1900,   # Cafe Corner
        "10189": 2200,   # Taj Mahal
        "71040": 700,    # Disney Castle
        "10185": 1500,   # Green Grocer
        "10217": 500,    # Diagon Alley
    }

    TARGET_NAMES = {
        "10179": "Star Wars Millennium Falcon (UCS)",
        "10030": "Star Wars Imperial Star Destroyer (UCS)",
        "10182": "Modular Buildings - Cafe Corner",
        "10189": "Creator Expert - Taj Mahal",
        "71040": "Disney Castle",
        "10185": "Modular Buildings - Green Grocer",
        "10217": "Harry Potter Diagon Alley",
    }

    def check_all_targets(self) -> List[LEGOPricePoint]:
        """Check current prices for all target sets"""
        deals = []
        for set_id, target_price in self.TARGET_BUY_PRICES.items():
            if set_id in self.CURRENT_MARKET_PRICES:
                market = self.CURRENT_MARKET_PRICES[set_id]
                current_price = market["price"]
                discount = ((target_price - current_price) / target_price) * 100

                deal = LEGOPricePoint(
                    set_id=set_id,
                    set_name=self.TARGET_NAMES.get(set_id, "Unknown"),
                    current_price=current_price,
                    price_source="BrickLink",
                    listed_count=market["count"],
                    best_condition=market["condition"],
                    last_updated=datetime.now().isoformat(),
                    discount_vs_target=discount
                )
                deals.append(deal)

        return deals

    def identify_buy_signals(self, deals: List[LEGOPricePoint], min_discount: float = 3.0) -> List[Dict]:
        """
        Find sets that are currently at or below target buy price.
        min_discount: Only alert if discount is at least this % (3% = $60 off on $2000 set)
        """
        buy_signals = []
        for deal in deals:
            if deal.discount_vs_target >= min_discount:
                buy_signals.append({
                    "set_id": deal.set_id,
                    "set_name": deal.set_name,
                    "current_price": deal.current_price,
                    "target_price": self.TARGET_BUY_PRICES[deal.set_id],
                    "savings": self.TARGET_BUY_PRICES[deal.set_id] - deal.current_price,
                    "discount_percent": deal.discount_vs_target,
                    "condition": deal.best_condition,
                    "available_count": deal.listed_count,
                    "signal_strength": "BUY_NOW" if deal.discount_vs_target >= 5 else "MONITOR",
                    "last_updated": deal.last_updated,
                })

        # Sort by savings (biggest discount first)
        return sorted(buy_signals, key=lambda x: x["savings"], reverse=True)

    def generate_purchase_report(self) -> Dict:
        """Generate a complete purchase analysis report"""
        deals = self.check_all_targets()
        buy_signals = self.identify_buy_signals(deals)

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_targets_tracked": len(self.TARGET_BUY_PRICES),
            "available_deals": len(deals),
            "buy_signals": len(buy_signals),
            "buy_now": [s for s in buy_signals if s["signal_strength"] == "BUY_NOW"],
            "monitor": [s for s in buy_signals if s["signal_strength"] == "MONITOR"],
            "recommendations": self._score_recommendations(buy_signals),
        }
        return report

    def _score_recommendations(self, buy_signals: List[Dict]) -> List[Dict]:
        """Score and rank recommendations by investment potential"""
        scored = []
        for signal in buy_signals[:3]:  # Top 3 deals
            score = (
                signal["discount_percent"] * 1.0 +  # % discount weight
                (signal["available_count"] * 5) +    # Availability multiplier
                (100 if signal["signal_strength"] == "BUY_NOW" else 50)  # Signal type
            )
            scored.append({
                "recommendation_rank": len(scored) + 1,
                "set_name": signal["set_name"],
                "set_id": signal["set_id"],
                "current_price": signal["current_price"],
                "target_price": signal["target_price"],
                "savings": signal["savings"],
                "investment_score": round(score, 1),
                "action": "BUY IMMEDIATELY" if signal["discount_percent"] >= 5 else "ADD TO WATCHLIST",
                "condition": signal["condition"],
                "reason": f"${signal['savings']} below target ({signal['discount_percent']:.1f}% off), {signal['available_count']} available",
            })
        return scored
