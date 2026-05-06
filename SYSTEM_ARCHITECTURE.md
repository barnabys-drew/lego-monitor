# LEGO Monitor - System Architecture

## Overview

Live monitoring system for LEGO set prices and portfolio tracking. Integrated with Prometheus + Grafana for visualization and auto-tuning.

```
┌─────────────────────┐
│  lego-monitor       │
│  (Container)        │
│                     │
│  • Async scraper    │
│  • Price history    │
│  • Portfolio calc   │
└──────────┬──────────┘
           │
           │ :8888 (Prometheus format)
           ▼
┌─────────────────────┐
│ Prometheus          │
│ (Metrics Store)     │
│                     │
│ • Time-series DB    │
│ • 30-day retention  │
│ • InfluxQL queries  │
└──────────┬──────────┘
           │
           │ (queries)
           ▼
┌─────────────────────┐
│ Grafana             │
│ (Dashboards)        │
│                     │
│ • Price trends      │
│ • ROI curves        │
│ • Portfolio summary │
│ • Scraper health    │
└─────────────────────┘
```

## Data Flow

### 1. Scraping (Hourly)
```
lego-monitor:lego_scraper.py
  ├─ Load targets from data/lego_targets.json
  ├─ Load portfolio from data/lego_portfolio.json
  ├─ For each target:
  │   ├─ Fetch BrickEconomy price
  │   ├─ Fallback to BrickLink if needed
  │   └─ Store in Prometheus metrics
  └─ Append price to data/lego_price_history.jsonl
```

### 2. Metrics Export
```
Every 5 minutes, Prometheus scrapes lego-monitor:8888
  ├─ lego_set_current_price{set_id, name, theme}
  ├─ lego_set_appreciation_ratio{set_id, name}
  ├─ lego_portfolio_total_value
  ├─ lego_portfolio_unrealized_gain
  ├─ lego_portfolio_roi_percent
  ├─ lego_scrape_duration_seconds (histogram)
  ├─ lego_scrape_success_total (counter)
  └─ lego_scrape_errors_total{set_id, error_type}
```

### 3. Visualization
```
Grafana dashboard pulls from Prometheus
  ├─ Panel 1: Current set prices (pie chart)
  ├─ Panel 2: Portfolio summary (stat cards)
  ├─ Panel 3: Price trends (time series)
  ├─ Panel 4: Appreciation ratios (bar chart)
  ├─ Panel 5: Scraper health (success/errors)
  └─ Panel 6: Error breakdown (stacked area)
```

## Kubernetes-Ready Readiness

Currently runs as Docker container. To upgrade to K8s:

1. Create Deployment manifest
2. Add Service (port 8888)
3. Add PersistentVolume for data/
4. Add ServiceMonitor for Prometheus auto-discovery
5. Update Prometheus scrape config → ServiceMonitor

```yaml
# Future K8s manifest structure
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lego-monitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lego-monitor
  template:
    metadata:
      labels:
        app: lego-monitor
    spec:
      containers:
      - name: lego-monitor
        image: lego-monitor:latest
        ports:
        - containerPort: 8888
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: lego-monitor-data
```

## Auto-Tuning Strategy

**I manage this system by:**

1. **Monitoring scraper health**
   - Watch error rates in Grafana
   - If >5% failures → investigate data source issues
   - Adjust retry logic if needed

2. **Optimizing scrape frequency**
   - Default: 1 hour (LEGO prices don't change fast)
   - If target prices spike → reduce to 30min temporarily
   - Adjust in `.env` SCRAPE_INTERVAL_SECONDS

3. **Improving data sources**
   - If BrickEconomy API gets rate-limited → add delay
   - If BrickLink prices more accurate → prioritize it
   - Add new sources (eBay, Mercari) as needed

4. **Portfolio insights**
   - Watch ROI trends in Grafana
   - Alert when appreciation slows (reaching plateau)
   - Recommend exits when targets hit ROI goals

5. **Performance tuning**
   - Monitor scrape duration histogram
   - Optimize web scraping if too slow
   - Cache responses when available

## Data Retention

- **Prometheus:** 30 days (configurable in prometheus.yml)
- **Price history JSONL:** Indefinite (append-only)
- **Portfolio JSON:** Current state only

To extend Prometheus retention:
```yaml
prometheus:
  command:
    - --storage.tsdb.retention.time=90d  # Change 30d → 90d
```

## Deployment Checklist

- [x] Docker image builds
- [x] Prometheus scrape config updated
- [x] Grafana dashboard provisioned
- [x] Data directories initialized
- [x] Git repository initialized
- [ ] Run container: `./start.sh`
- [ ] Verify metrics at http://localhost:8888
- [ ] Check Grafana dashboard loads
- [ ] Add your portfolio holdings to `data/lego_portfolio.json`
- [ ] Wait for first scrape cycle (1 hour) to populate data

## Container Commands

```bash
# Build
docker build -t lego-monitor:latest .

# Run (single)
docker-compose up -d

# Logs
docker-compose logs -f lego-monitor

# Stop
docker-compose down

# Restart
docker-compose restart lego-monitor

# Shell into container
docker-compose exec lego-monitor /bin/bash

# Check metrics
curl http://localhost:8888/metrics

# Reload Prometheus config (if changed)
curl -X POST http://localhost:9090/-/reload
```

## Integration with Core 4

LEGO Monitor is **independent** of Core 4 systems:
- No shared dependencies
- Separate container
- Separate Prometheus job
- Separate Grafana dashboard

Can run in parallel without interference.

## Future Enhancements

- [ ] Multi-source price averaging (improve accuracy)
- [ ] Alert system (buy signal when price dips below threshold)
- [ ] Historical trend analysis (calculate appreciation rate)
- [ ] Monte Carlo ROI projections
- [ ] Automated buy recommendations
- [ ] Integration with portfolio ledger (CSV export)
- [ ] BrickLink API integration (requires auth token)
- [ ] eBay API integration (track secondary market)

## Performance Targets

- Scrape cycle: < 30 seconds (5 sets)
- Metrics export: < 1 second
- Grafana dashboard load: < 2 seconds
- Data storage: < 100MB for 6 months history
