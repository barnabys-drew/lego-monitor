"""
Discord LEGO Alerts — Post purchase opportunities to Discord.
Integrates with BrickLinkMonitor to send deal notifications.
"""

import os
from datetime import datetime

import requests

from bricklink_price_monitor import BrickLinkMonitor


class LEGODiscordAlerter:
    """Posts LEGO purchase opportunities to Discord"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        self.monitor = BrickLinkMonitor()

    def send_price_report(self, emit_console: bool = True) -> dict:
        """Generate and send LEGO price report to Discord"""
        report = self.monitor.generate_purchase_report()

        if emit_console:
            self._print_console_report(report)

        if not self.webhook_url:
            return {"posted": False, "reason": "No Discord webhook configured"}

        return self._post_to_discord(report)

    def _print_console_report(self, report: dict) -> None:
        """Print report to console"""
        print("\n" + "=" * 70)
        print("LEGO PURCHASE OPPORTUNITY REPORT")
        print("=" * 70)
        print(f"Tracking: {report['total_targets_tracked']} sets")
        print(f"Available deals: {report['available_deals']}")
        print(f"Buy signals: {report['buy_signals']}")

        if report["buy_now"]:
            print("\n🔴 BUY IMMEDIATELY:")
            for deal in report["buy_now"]:
                print(f"  • {deal['set_name']}")
                print(f"    ${deal['current_price']} ({deal['discount_percent']:.1f}% off)")

        if not report["buy_now"] and not report["monitor"]:
            print("\n⏳ No current deals. Market prices above target.")

    def _post_to_discord(self, report: dict) -> dict:
        """Post formatted report to Discord webhook"""
        try:
            if not report["recommendations"]:
                content = "📊 LEGO Market Report: No deals below target right now. Monitoring continues."
            else:
                content = self._format_message(report)

            payload = {"content": content}
            resp = requests.post(self.webhook_url, json=payload, timeout=10)

            if resp.status_code in (200, 204):
                return {
                    "posted": True,
                    "message_count": 1,
                    "deals_posted": len(report["recommendations"]),
                }
            else:
                return {"posted": False, "status_code": resp.status_code}
        except Exception as e:
            return {"posted": False, "error": str(e)}

    def _format_message(self, report: dict) -> str:
        """Format report as Discord message"""
        lines = [
            "🧱 **LEGO Investment Report**",
            f"*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n",
        ]

        if report["recommendations"]:
            lines.append("✅ **Buy Recommendations:**")
            for rec in report["recommendations"]:
                lines.append(
                    f"**#{rec['recommendation_rank']}: {rec['set_name']}**\n"
                    f"• Current: ${rec['current_price']} | Target: ${rec['target_price']}\n"
                    f"• Savings: ${rec['savings']} ({rec['discount_percent']:.1f}% off)\n"
                    f"• Action: {rec['action']}\n"
                    f"• {rec['reason']}\n"
                )
        else:
            lines.append(
                "⏳ No deals below target. Tracking {} sets.".format(report["total_targets_tracked"])
            )

        return "\n".join(lines)

    def continuous_monitor(self, interval_hours: int = 24) -> None:
        """Monitor continuously and alert on deals (for container deployment)"""
        print(f"[LEGO Monitor] Starting continuous monitoring every {interval_hours}h")
        self.send_price_report(emit_console=True)
        # In production, would use APScheduler or similar to run this periodically
