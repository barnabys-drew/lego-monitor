# LEGO Monitor - Deployment Guide

**Status:** Ready to deploy  
**Architecture:** Docker container + Prometheus + Grafana  
**Location:** `/home/drewt_p_weiner/code/lego-monitor/`

## Quick Start (One Command)

```bash
cd /home/drewt_p_weiner/code/lego-monitor
./start.sh
```

This will:
1. Build the Docker image (if not cached)
2. Start the lego-monitor container
3. Verify Prometheus is configured
4. Display dashboard URLs

## Manual Deployment

### Step 1: Verify Prometheus Config
Check that lego-monitor is in the scrape configs:

```bash
grep -A2 "job_name: lego-monitor" /home/drewt_p_weiner/code/docker-monitoring/prometheus/prometheus.yml
```

Should show:
```yaml
- job_name: lego-monitor
  static_configs:
    - targets: ["lego-monitor:8888"]
  scrape_interval: 5m
```

✓ Already configured

### Step 2: Build Container

```bash
cd /home/drewt_p_weiner/code/lego-monitor
docker build -t lego-monitor:latest .
```

Expected output: `Successfully tagged lego-monitor:latest`

### Step 3: Start Container

```bash
docker-compose up -d
```

Check logs:
```bash
docker-compose logs -f lego-monitor
```

Expected output:
```
INFO:__main__:Starting Prometheus metrics server on port 8888
INFO:__main__:Starting LEGO monitor loop (interval: 3600s)
INFO:lego_scraper:======...
INFO:lego_scraper:Starting scrape cycle...
```

### Step 4: Verify Metrics Endpoint

```bash
curl http://localhost:8888/metrics | head -20
```

Should return Prometheus-format metrics (lines starting with `#` and `lego_`).

### Step 5: Check Prometheus Job Status

```bash
curl http://localhost:9090/api/v1/query?query=lego_scrape_success_total
```

Or visit: http://localhost:9090 → Status → Targets → look for `lego-monitor`

### Step 6: View Grafana Dashboard

1. Go to http://localhost:3001
2. Login with admin credentials
3. Look for dashboard: "LEGO Monitor - Market & Portfolio Tracking"
4. Panels will populate after first scrape cycle (1 hour)

## Adding Your Portfolio

Edit `data/lego_portfolio.json`:

```json
{
  "generated": "2026-05-06T15:55:00Z",
  "holdings": [
    {
      "set_id": "10189",
      "name": "Taj Mahal",
      "purchase_price": 800.00,
      "purchase_date": "2026-05-01",
      "quantity": 1
    },
    {
      "set_id": "71040",
      "name": "Disney Castle",
      "purchase_price": 350.00,
      "purchase_date": "2026-04-15",
      "quantity": 1
    }
  ]
}
```

Metrics will auto-update after next scrape cycle:
- `lego_portfolio_total_value`
- `lego_portfolio_unrealized_gain`
- `lego_portfolio_roi_percent`

## Configuration

Edit `.env` to customize:

```bash
# Prometheus metrics port
METRICS_PORT=8888

# Scraping interval in seconds
# 3600 = 1 hour, 1800 = 30 min, 86400 = 24 hours
SCRAPE_INTERVAL_SECONDS=3600

# Logging level
LOG_LEVEL=INFO
```

Then restart:
```bash
docker-compose restart lego-monitor
```

## Monitoring the System

### View Live Logs
```bash
docker-compose logs -f lego-monitor
```

### Check Scraper Health
In Grafana, look at "LEGO Monitor" dashboard:
- Panel "Scraper Health (24h)" — should show successful scrapes
- Panel "Scraper Errors (24h)" — should be minimal

### Query Prometheus Directly

```bash
# Latest portfolio value
curl "http://localhost:9090/api/v1/query?query=lego_portfolio_total_value"

# All set prices
curl "http://localhost:9090/api/v1/query?query=lego_set_current_price"

# ROI percentage
curl "http://localhost:9090/api/v1/query?query=lego_portfolio_roi_percent"
```

## Troubleshooting

### Container won't start

```bash
docker-compose logs lego-monitor
```

Look for:
- `ModuleNotFoundError` → dependencies missing, rebuild image
- `FileNotFoundError` → data directory issue, check permissions
- `ConnectionError` → network/DNS issue

### No metrics appearing

1. Check container is running: `docker-compose ps`
2. Check endpoint: `curl http://localhost:8888/metrics`
3. Wait 5+ minutes for Prometheus to scrape first time
4. Check Prometheus job status: http://localhost:9090 → Status → Targets

### Scraper errors (can't fetch prices)

1. Check BrickEconomy availability: `curl https://www.brickeconomy.com`
2. Check BrickLink: `curl https://www.bricklink.com`
3. Review logs: `docker-compose logs lego-monitor | grep -i error`

Possible fixes:
- Add retry logic (edit `src/lego_scraper.py`)
- Increase timeout (change `timeout=10` to `timeout=30`)
- Add request delays (prevents rate limiting)

### Grafana dashboard is empty

1. Wait 1+ hours for first scrape cycle
2. Check metrics exist: `curl http://localhost:9090/api/v1/query?query=lego_set_current_price`
3. Verify Prometheus data source is selected in dashboard
4. Check date range (top right) includes current time

## Updating System

### Pull latest code
```bash
cd /home/drewt_p_weiner/code/lego-monitor
git pull
```

### Rebuild image
```bash
docker build -t lego-monitor:latest .
```

### Restart container
```bash
docker-compose restart lego-monitor
```

## Stopping the System

```bash
docker-compose down
```

Data is preserved in `data/` directory.

## Performance Notes

- **Scrape cycle:** ~5-10 seconds for 7 target sets
- **Memory usage:** ~200-300MB
- **Disk usage:** ~1MB per day of price history
- **Prometheus retention:** 30 days (adjustable)

## Next Steps

1. **Deploy:** `./start.sh`
2. **Wait:** 1 hour for first scrape + Prometheus metrics
3. **Check:** http://localhost:3001 → LEGO Monitor dashboard
4. **Add portfolio:** Edit `data/lego_portfolio.json`
5. **Monitor:** Check dashboard weekly for price trends

## Support

Issues or questions? Check:
- `docker-compose logs lego-monitor` — Container logs
- `README.md` — Quick reference
- `SYSTEM_ARCHITECTURE.md` — System design
- Grafana dashboard — Visual health status
