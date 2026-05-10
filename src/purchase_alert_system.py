#!/usr/bin/env python3
"""
LEGO Monitor Phase 2: Purchase Alert System
Tracks buy targets and alerts when deals appear on BrickLink/eBay

Workflow:
1. User adds sets to "buy targets" (max price, desired condition)
2. System monitors BrickLink/eBay prices daily
3. Alert if price < max OR condition improves
4. Track purchase history and cost basis
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import requests


@dataclass
class LEGOTarget:
    """Target set for purchase"""

    set_id: str
    set_name: str
    max_buy_price: float
    target_condition: str  # "New", "Like New", "Good", "Fair"
    retailer: str  # "BrickLink", "eBay", "Amazon"
    priority: int  # 1-5, higher = more important
    quantity: int = 1
    notes: str = ""


@dataclass
class PriceAlert:
    """Price drop alert"""

    date: str
    set_id: str
    set_name: str
    current_price: float
    max_target_price: float
    discount: float  # negative = below target, positive = above
    source: str
    alert_type: str  # "PRICE_DROP", "CONDITION_IMPROVED", "STOCK_AVAILABLE"


class LEGOAlertSystem:
    """Manages LEGO purchase targets and price alerts"""

    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.targets_file = self.config_dir / "lego_buy_targets.json"
        self.alerts_file = self.config_dir / "lego_price_alerts.json"
        self.purchases_file = self.config_dir / "lego_purchases.json"

        self.targets = self._load_targets()
        self.alerts = self._load_alerts()

    def _load_targets(self) -> list[LEGOTarget]:
        """Load buy targets"""
        if self.targets_file.exists():
            with open(self.targets_file) as f:
                data = json.load(f)
                return [LEGOTarget(**t) for t in data.get("targets", [])]
        return []

    def _save_targets(self):
        """Save buy targets"""
        with open(self.targets_file, "w") as f:
            json.dump({"targets": [asdict(t) for t in self.targets]}, f, indent=2)

    def _load_alerts(self) -> list[dict]:
        """Load alert history"""
        if self.alerts_file.exists():
            with open(self.alerts_file) as f:
                return json.load(f).get("alerts", [])
        return []

    def _save_alerts(self):
        """Save alert history"""
        with open(self.alerts_file, "w") as f:
            json.dump({"alerts": self.alerts}, f, indent=2)

    def add_target(
        self,
        set_id: str,
        set_name: str,
        max_buy_price: float,
        target_condition: str = "Good",
        retailer: str = "BrickLink",
        priority: int = 3,
        quantity: int = 1,
        notes: str = "",
    ) -> bool:
        """Add a set to buy targets"""
        target = LEGOTarget(
            set_id=set_id,
            set_name=set_name,
            max_buy_price=max_buy_price,
            target_condition=target_condition,
            retailer=retailer,
            priority=priority,
            quantity=quantity,
            notes=notes,
        )
        self.targets.append(target)
        self._save_targets()
        print(f"✓ Added to buy targets: {set_name} (max ${max_buy_price})")
        return True

    def remove_target(self, set_id: str) -> bool:
        """Remove a set from buy targets"""
        self.targets = [t for t in self.targets if t.set_id != set_id]
        self._save_targets()
        return True

    def log_price_check(
        self,
        set_id: str,
        current_price: float,
        condition: str = "Good",
        source: str = "BrickLink",
    ) -> PriceAlert | None:
        """
        Check price against target
        Returns alert if price triggers
        """
        # Find target
        target = next((t for t in self.targets if t.set_id == set_id), None)
        if not target:
            return None

        # Check if price is good
        discount = target.max_buy_price - current_price
        if discount >= 0:  # Price is at or below target
            alert = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "set_id": set_id,
                "set_name": target.set_name,
                "current_price": current_price,
                "target_price": target.max_buy_price,
                "discount": discount,
                "source": source,
                "alert_type": "PRICE_DROP" if discount > 0 else "STOCK_AVAILABLE",
                "condition": condition,
            }
            self.alerts.append(alert)
            self._save_alerts()
            return alert

        return None

    def check_all_targets(self, market_data: dict[str, dict]) -> list[dict]:
        """
        Check all targets against market data

        market_data format:
        {
            "set_id": {
                "bricklink_price": 150,
                "ebay_price": 160,
                "condition": "Good",
                "stock": true
            }
        }
        """
        new_alerts = []

        for target in self.targets:
            if target.set_id not in market_data:
                continue

            data = market_data[target.set_id]
            prices = {
                "BrickLink": data.get("bricklink_price"),
                "eBay": data.get("ebay_price"),
            }

            for source, price in prices.items():
                if price and price < target.max_buy_price:
                    alert = self.log_price_check(
                        set_id=target.set_id,
                        current_price=price,
                        condition=data.get("condition", "Unknown"),
                        source=source,
                    )
                    if alert:
                        new_alerts.append(alert)

        return new_alerts

    def get_active_targets(self, sorted_by_priority: bool = True) -> list[LEGOTarget]:
        """Get all active buy targets"""
        targets = self.targets[:]
        if sorted_by_priority:
            targets.sort(key=lambda t: t.priority, reverse=True)
        return targets

    def get_recent_alerts(self, days: int = 7) -> list[dict]:
        """Get alerts from last N days"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        recent = []
        for alert in self.alerts:
            try:
                alert_time = datetime.fromisoformat(alert["date"]).timestamp()
                if alert_time > cutoff:
                    recent.append(alert)
            except:
                pass
        return recent

    def log_purchase(
        self,
        set_id: str,
        purchase_price: float,
        retailer: str,
        date: str | None = None,
        quantity: int = 1,
    ) -> bool:
        """Log an actual purchase"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Load or initialize purchases
        if self.purchases_file.exists():
            with open(self.purchases_file) as f:
                purchases = json.load(f)
        else:
            purchases = {"purchases": []}

        # Find target for set
        target = next((t for t in self.targets if t.set_id == set_id), None)
        set_name = target.set_name if target else f"Set {set_id}"

        # Add purchase record
        purchases["purchases"].append(
            {
                "date": date,
                "set_id": set_id,
                "set_name": set_name,
                "price": purchase_price,
                "retailer": retailer,
                "quantity": quantity,
                "total_cost": purchase_price * quantity,
            }
        )

        # Save
        with open(self.purchases_file, "w") as f:
            json.dump(purchases, f, indent=2)

        print(
            f"✓ Logged purchase: {set_name} × {quantity} @ ${purchase_price} = ${purchase_price * quantity}"
        )
        return True

    def generate_status_report(self) -> str:
        """Generate current status report"""
        lines = []
        lines.append("=" * 70)
        lines.append("LEGO PURCHASE ALERT SYSTEM - STATUS")
        lines.append(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")

        # Active targets
        targets = self.get_active_targets()
        lines.append(f"ACTIVE BUY TARGETS: {len(targets)}")
        for i, target in enumerate(targets[:10], 1):
            priority_emoji = "🔥" if target.priority >= 4 else "🟡" if target.priority >= 3 else "🟢"
            lines.append(f"  {i}. {priority_emoji} {target.set_name} (Set #{target.set_id})")
            lines.append(f"     Max buy: ${target.max_buy_price} | Retailer: {target.retailer}")
            lines.append(f"     Priority: {target.priority}/5 | Qty: {target.quantity}")
        lines.append("")

        # Recent alerts
        alerts = self.get_recent_alerts(days=7)
        lines.append(f"PRICE ALERTS (Last 7 days): {len(alerts)}")
        if alerts:
            for alert in alerts[-5:]:  # Last 5
                lines.append(
                    f"  {alert['date']}: {alert['set_name']} @ ${alert['current_price']} "
                    f"(Target: ${alert['target_price']})"
                )
        else:
            lines.append("  No price drops detected")
        lines.append("")

        # Purchase history
        if self.purchases_file.exists():
            with open(self.purchases_file) as f:
                purchases = json.load(f).get("purchases", [])
            if purchases:
                total_invested = sum(p["total_cost"] for p in purchases)
                lines.append(f"PURCHASE HISTORY: {len(purchases)} transactions")
                lines.append(f"  Total invested: ${total_invested:,.2f}")
                lines.append(f"  Recent: {purchases[-1]['set_name']} on {purchases[-1]['date']}")
        lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def send_discord_alerts(self, alerts: list[dict]) -> int:
        """Post price-drop alerts to Discord webhook. Returns number posted."""
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        if not webhook_url or not alerts:
            return 0

        posted = 0
        for alert in alerts:
            discount_pct = (alert["discount"] / alert["target_price"]) * 100 if alert["target_price"] else 0
            embed = {
                "title": f"\U0001f9f1 LEGO BUY ALERT: {alert['set_name']}",
                "color": 0x00CC44,
                "fields": [
                    {"name": "Set ID", "value": alert["set_id"], "inline": True},
                    {
                        "name": "Price",
                        "value": f"${alert['current_price']:.2f}",
                        "inline": True,
                    },
                    {
                        "name": "Target",
                        "value": f"${alert['target_price']:.2f}",
                        "inline": True,
                    },
                    {
                        "name": "Savings",
                        "value": f"${alert['discount']:.2f} ({discount_pct:.0f}% under target)",
                        "inline": True,
                    },
                    {
                        "name": "Source",
                        "value": alert.get("source", "?"),
                        "inline": True,
                    },
                    {
                        "name": "Condition",
                        "value": alert.get("condition", "Unknown"),
                        "inline": True,
                    },
                ],
                "timestamp": datetime.utcnow().isoformat(),
            }
            try:
                r = requests.post(
                    webhook_url,
                    json={"username": "Argus LEGO", "embeds": [embed]},
                    timeout=10,
                )
                if r.status_code in (200, 204):
                    posted += 1
            except Exception:
                pass
        return posted


def example_usage():
    """Example: Set up buy targets and check for alerts"""
    system = LEGOAlertSystem()

    # Add some buy targets
    targets = [
        {
            "set_id": "10323",
            "set_name": "Pirates of Barracuda Bay",
            "max_price": 350,
            "priority": 5,
        },
        {
            "set_id": "10278",
            "set_name": "Police Station",
            "max_price": 200,
            "priority": 4,
        },
        {
            "set_id": "75324",
            "set_name": "Star Wars AT-TE Walker",
            "max_price": 150,
            "priority": 3,
        },
    ]

    for t in targets:
        system.add_target(
            set_id=t["set_id"],
            set_name=t["set_name"],
            max_buy_price=t["max_price"],
            priority=t["priority"],
        )

    # Example: Check prices (in real system, would come from scraper)
    market_data = {
        "10323": {"bricklink_price": 320, "ebay_price": 345, "condition": "Like New"},
        "10278": {"bricklink_price": 210, "ebay_price": 225, "condition": "Good"},
        "75324": {"bricklink_price": 140, "ebay_price": 155, "condition": "Good"},
    }

    alerts = system.check_all_targets(market_data)
    print(f"\n✓ Found {len(alerts)} price alerts\n")

    # Example: Log a purchase
    if alerts:
        system.log_purchase(
            set_id=alerts[0]["set_id"],
            purchase_price=alerts[0]["current_price"],
            retailer=alerts[0]["source"],
            quantity=1,
        )

    # Print status report
    print(system.generate_status_report())


if __name__ == "__main__":
    example_usage()
