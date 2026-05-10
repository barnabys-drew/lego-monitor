#!/usr/bin/env python3
"""
LEGO Monthly ROI Report
Automated monthly portfolio performance tracking
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class MonthlyMetrics:
    month: str
    portfolio_value_start: float
    portfolio_value_end: float
    roi_pct: float
    strong_performers: list
    weak_performers: list
    actions_taken: list


class LEGOMonthlyReport:
    def __init__(self):
        self.portfolio_file = Path(__file__).parent.parent / "data" / "lego_portfolio.json"
        self.reports_dir = Path(__file__).parent.parent / "data" / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def load_portfolio(self) -> dict:
        """Load current portfolio"""
        with open(self.portfolio_file) as f:
            return json.load(f)

    def generate_monthly_report(self, month_label: str | None = None) -> MonthlyMetrics:
        """Generate monthly performance report"""

        if not month_label:
            month_label = datetime.now().strftime("%Y-%m")

        portfolio = self.load_portfolio()
        holdings = portfolio.get("holdings", [])

        # Calculate metrics
        total_cost = sum(h["cost_basis"] * h["quantity"] for h in holdings)
        total_value = sum(h["current_market_price"] * h["quantity"] for h in holdings)
        portfolio_roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        # Identify strong/weak performers
        strong = sorted(
            [h for h in holdings if h["roi_percent"] >= 30],
            key=lambda x: x["roi_percent"],
            reverse=True,
        )[:3]

        weak = sorted(
            [h for h in holdings if h["roi_percent"] < 0],
            key=lambda x: x["roi_percent"],
        )[:3]

        # Actions taken this month
        actions = self._recommend_actions(holdings)

        metrics = MonthlyMetrics(
            month=month_label,
            portfolio_value_start=total_cost,
            portfolio_value_end=total_value,
            roi_pct=portfolio_roi,
            strong_performers=strong,
            weak_performers=weak,
            actions_taken=actions,
        )

        return metrics

    def _recommend_actions(self, holdings: list) -> list:
        """Generate action recommendations"""
        actions = []

        for holding in holdings:
            if holding["roi_percent"] >= 50 and holding.get("quantity", 1) > 0:
                actions.append(
                    {
                        "type": "SELL",
                        "set": holding["name"],
                        "reason": f"ROI {holding['roi_percent']:.1f}% - target achieved",
                        "estimated_gain": (holding["current_market_price"] - holding["cost_basis"])
                        * holding["quantity"],
                    }
                )
            elif holding["roi_percent"] < -10:
                actions.append(
                    {
                        "type": "HOLD",
                        "set": holding["name"],
                        "reason": f"ROI {holding['roi_percent']:.1f}% - hold for recovery",
                        "hold_days": holding["hold_duration_days"],
                    }
                )
            elif holding["roi_percent"] >= 20 and holding["roi_percent"] < 30:
                actions.append(
                    {
                        "type": "MONITOR",
                        "set": holding["name"],
                        "reason": f"ROI {holding['roi_percent']:.1f}% - approaching target",
                        "target_price": holding["cost_basis"] * 1.5,
                    }
                )

        return actions

    def format_report(self, metrics: MonthlyMetrics) -> str:
        """Format report for display"""

        report = f"""
{'='*70}
LEGO PORTFOLIO - MONTHLY REPORT
Month: {metrics.month}
Generated: {datetime.now().isoformat()}
{'='*70}

📊 PORTFOLIO PERFORMANCE
{'-'*70}
Starting Value: ${metrics.portfolio_value_start:,.2f}
Current Value:  ${metrics.portfolio_value_end:,.2f}
Gain/Loss:      ${metrics.portfolio_value_end - metrics.portfolio_value_start:+,.2f}
ROI:            {metrics.roi_pct:+.1f}%

🟢 TOP PERFORMERS (>= 30% ROI)
{'-'*70}
"""

        if metrics.strong_performers:
            for h in metrics.strong_performers:
                gain = (h["current_market_price"] - h["cost_basis"]) * h["quantity"]
                report += f"  {h['name']}\n"
                report += f"    Cost: ${h['cost_basis']*h['quantity']:,.0f} → Value: ${h['current_market_price']*h['quantity']:,.0f}\n"
                report += f"    ROI: {h['roi_percent']:+.1f}% (${gain:+,.0f})\n\n"
        else:
            report += "  No sets at target yet.\n\n"

        report += f"""
🔴 UNDERPERFORMERS (< 0% ROI)
{'-'*70}
"""

        if metrics.weak_performers:
            for h in metrics.weak_performers:
                loss = (h["current_market_price"] - h["cost_basis"]) * h["quantity"]
                report += f"  {h['name']}\n"
                report += f"    Cost: ${h['cost_basis']*h['quantity']:,.0f} → Value: ${h['current_market_price']*h['quantity']:,.0f}\n"
                report += f"    ROI: {h['roi_percent']:+.1f}% (${loss:+,.0f})\n"
                report += f"    Hold time: {h['hold_duration_days']} days\n\n"
        else:
            report += "  All sets profitable!\n\n"

        report += f"""
✅ RECOMMENDED ACTIONS
{'-'*70}
"""

        if metrics.actions_taken:
            for action in metrics.actions_taken:
                if action["type"] == "SELL":
                    report += f"  SELL: {action['set']}\n"
                    report += f"    Reason: {action['reason']}\n"
                    report += f"    Estimated gain: ${action['estimated_gain']:,.0f}\n\n"
                elif action["type"] == "HOLD":
                    report += f"  HOLD: {action['set']}\n"
                    report += f"    Reason: {action['reason']}\n"
                    report += f"    Hold duration: {action['hold_days']} days\n\n"
                elif action["type"] == "MONITOR":
                    report += f"  MONITOR: {action['set']}\n"
                    report += f"    Reason: {action['reason']}\n"
                    report += f"    Target: ${action['target_price']:,.0f}\n\n"
        else:
            report += "  No actions recommended this month.\n\n"

        report += f"""
{'-'*70}
Next review: {(datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m-01')}
"""

        return report

    def save_report(self, metrics: MonthlyMetrics, report_text: str):
        """Save report to file"""
        filename = self.reports_dir / f"monthly_report_{metrics.month}.md"
        with open(filename, "w") as f:
            f.write(report_text)
        print(f"✓ Report saved to {filename}")

    def print_report(self, metrics: MonthlyMetrics):
        """Print report to console"""
        report_text = self.format_report(metrics)
        print(report_text)
        return report_text


if __name__ == "__main__":
    generator = LEGOMonthlyReport()
    metrics = generator.generate_monthly_report("2026-05")
    report = generator.print_report(metrics)
    generator.save_report(metrics, report)
