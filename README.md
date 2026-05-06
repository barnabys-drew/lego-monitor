# LEGO Monitor - Live Market Tracking System

Real-time LEGO set price monitoring and portfolio tracking with Prometheus + Grafana integration.

## Architecture

- **Scraper** (`lego_scraper.py`) — Periodically fetches prices from BrickEconomy, BrickLink
- **Prometheus** — Time-series database for metric storage
- **Grafana** — Dashboards for visualization and monitoring

## Quick Start

### Build & Deploy

```bash
# Build image
docker build -t lego-monitor .

# Run container
docker-compose up -d

# Check logs
docker-compose logs -f lego-monitor
```

### Configuration

Edit `.env`:
- `METRICS_PORT` — Prometheus metrics endpoint (default: 8888)
- `SCRAPE_INTERVAL_SECONDS` — How often to scrape (default: 3600 = 1 hour)
- `LOG_LEVEL` — Logging verbosity (default: INFO)

### Viewing Data

1. **Grafana Dashboard:** http://localhost:3001
   - Look for "LEGO Monitor - Market & Portfolio Tracking"
   
2. **Prometheus Metrics:** http://localhost:9090
   - Query: `lego_set_current_price`, `lego_portfolio_roi_percent`, etc.

## Portfolio Management

Edit `data/lego_portfolio.json` to add your holdings:

```json
{
  "holdings": [
    {
      "set_id": "10189",
      "name": "Taj Mahal",
      "purchase_price": 800.00,
      "purchase_date": "2026-05-06",
      "quantity": 1
    }
  ]
}
```

The system automatically calculates:
- Portfolio value
- Unrealized gains
- ROI percentage

## Metrics Exported

### Set-Level
- `lego_set_current_price{set_id, name, theme}` — Current market price
- `lego_set_appreciation_ratio{set_id, name}` — Price / Retail ratio

### Portfolio-Level
- `lego_portfolio_total_value` — Total market value
- `lego_portfolio_unrealized_gain` — Unrealized gain in dollars
- `lego_portfolio_roi_percent` — ROI percentage

### System
- `lego_scrape_duration_seconds` — Scrape time histogram
- `lego_scrape_success_total` — Successful scrapes counter
- `lego_scrape_errors_total{set_id, error_type}` — Errors by type

## Data Storage

- **Price History:** `data/lego_price_history.jsonl` (one record per line)
- **Portfolio:** `data/lego_portfolio.json`
- **Targets:** `data/lego_targets.json`

## Future Improvements

- [ ] BrickLink API integration (requires auth key)
- [ ] Alert system (buy signals when prices dip)
- [ ] Multi-source price averaging
- [ ] Historical trend analysis
- [ ] ROI projections (Monte Carlo simulation)
