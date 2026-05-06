#!/bin/bash
# LEGO Monitor Startup Script

set -e

echo "🧱 LEGO Monitor - Startup"
echo "========================"

# Check if Prometheus is running
echo "✓ Checking Prometheus config..."
if grep -q "lego-monitor" /home/drewt_p_weiner/code/docker-monitoring/prometheus/prometheus.yml; then
    echo "  ✓ Prometheus scrape config found"
else
    echo "  ⚠ Warning: Prometheus scrape config not found"
fi

# Start container
echo ""
echo "✓ Starting lego-monitor container..."
docker-compose up -d

# Wait for container to be ready
echo ""
echo "⏳ Waiting for container to start..."
sleep 3

# Check metrics endpoint
echo "✓ Checking metrics endpoint..."
if curl -s http://localhost:8888/metrics > /dev/null; then
    echo "  ✓ Metrics endpoint responding at http://localhost:8888"
else
    echo "  ⚠ Metrics endpoint not responding yet (may still be starting)"
fi

echo ""
echo "✓ Startup complete!"
echo ""
echo "📊 Dashboards:"
echo "  - Grafana:    http://localhost:3001 → LEGO Monitor"
echo "  - Prometheus: http://localhost:9090 → lego-monitor job"
echo "  - Metrics:    http://localhost:8888/metrics"
echo ""
echo "📝 Logs:"
echo "  docker-compose logs -f lego-monitor"
echo ""
