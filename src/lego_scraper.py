#!/usr/bin/env python3
"""
LEGO Monitor - Live Market Scraper
Continuously scrapes LEGO set prices and exports metrics to Prometheus
"""

import logging
import time
import os
import json
from datetime import datetime
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
lego_set_price = Gauge(
    'lego_set_current_price',
    'Current market price of LEGO set',
    ['set_id', 'name', 'theme']
)

lego_set_appreciation = Gauge(
    'lego_set_appreciation_ratio',
    'Appreciation ratio (current price / retail)',
    ['set_id', 'name']
)

lego_portfolio_value = Gauge(
    'lego_portfolio_total_value',
    'Total portfolio market value',
)

lego_portfolio_gain = Gauge(
    'lego_portfolio_unrealized_gain',
    'Portfolio unrealized gain in dollars',
)

lego_portfolio_roi = Gauge(
    'lego_portfolio_roi_percent',
    'Portfolio ROI percentage',
)

lego_scrape_duration = Histogram(
    'lego_scrape_duration_seconds',
    'Time taken to scrape prices',
)

lego_scrape_errors = Counter(
    'lego_scrape_errors_total',
    'Total scraping errors',
    ['set_id', 'error_type']
)

lego_scrape_success = Counter(
    'lego_scrape_success_total',
    'Total successful scrapes',
)


class LegoTargetSet:
    """Target LEGO set for monitoring"""
    def __init__(self, set_id: str, name: str, theme: str, retail_price: float):
        self.set_id = set_id
        self.name = name
        self.theme = theme
        self.retail_price = retail_price
        self.current_price = None
        self.last_updated = None
        self.scrape_count = 0
        self.scrape_failures = 0


class LegoMarketScraper:
    """Scrapes LEGO market prices from multiple sources"""
    
    def __init__(self):
        self.targets: Dict[str, LegoTargetSet] = {}
        self.portfolio_file = './data/lego_portfolio.json'
        self.price_history_file = './data/lego_price_history.jsonl'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Create data directory
        os.makedirs('./data', exist_ok=True)
        
        self._load_targets()
        self._load_portfolio()
    
    def _load_targets(self):
        """Load target sets from JSON"""
        targets_file = './data/lego_targets.json'
        if not os.path.exists(targets_file):
            logger.warning(f"Targets file not found: {targets_file}. Using defaults.")
            self._create_default_targets()
            return
        
        try:
            with open(targets_file) as f:
                data = json.load(f)
            
            for s in data.get('top_buys', []):
                target = LegoTargetSet(
                    set_id=s['set_id'],
                    name=s['name'],
                    theme=s['theme'],
                    retail_price=s['retail_price']
                )
                self.targets[s['set_id']] = target
                logger.info(f"Loaded target: {s['name']} ({s['set_id']})")
        except Exception as e:
            logger.error(f"Failed to load targets: {e}")
            self._create_default_targets()
    
    def _create_default_targets(self):
        """Create default target sets if file missing"""
        defaults = [
            ('10179', 'Star Wars Millennium Falcon', 'Star Wars', 499.99),
            ('10189', 'Creator Expert Taj Mahal', 'Creator Expert', 369.99),
            ('10182', 'Modular Cafe Corner', 'Modular', 149.99),
            ('10185', 'Modular Green Grocer', 'Modular', 149.99),
            ('71040', 'Creator Expert Disney Castle', 'Creator Expert', 349.99),
        ]
        
        for set_id, name, theme, retail in defaults:
            target = LegoTargetSet(set_id, name, theme, retail)
            self.targets[set_id] = target
            logger.info(f"Created default target: {name}")
    
    def _load_portfolio(self):
        """Load personal holdings"""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file) as f:
                    self.portfolio = json.load(f)
                    logger.info(f"Loaded portfolio with {len(self.portfolio.get('holdings', []))} holdings")
            except Exception as e:
                logger.error(f"Failed to load portfolio: {e}")
                self.portfolio = {'holdings': []}
        else:
            self.portfolio = {'holdings': []}
    
    async def fetch_brickeconomy_price(self, set_id: str) -> Optional[float]:
        """Fetch price from BrickEconomy"""
        try:
            url = f"https://www.brickeconomy.com/set/{set_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Look for price in common locations
                price_elem = soup.find('span', class_='price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = float(price_text.replace('$', '').replace(',', ''))
                    return price
        except Exception as e:
            logger.debug(f"BrickEconomy fetch failed for {set_id}: {e}")
        
        return None
    
    async def fetch_bricklink_price(self, set_id: str) -> Optional[float]:
        """Fetch price from BrickLink (web scrape, API requires auth)"""
        try:
            url = f"https://www.bricklink.com/v2/catalog/catalogitem.page?S={set_id}-1"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Look for average sale price
                price_elem = soup.find('span', class_='average-price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = float(price_text.replace('$', '').replace(',', ''))
                    return price
        except Exception as e:
            logger.debug(f"BrickLink fetch failed for {set_id}: {e}")
        
        return None
    
    async def scrape_set(self, set_id: str, target: LegoTargetSet):
        """Scrape price for a single set"""
        try:
            # Try multiple sources
            price = None
            
            # Try BrickEconomy first
            price = await self.fetch_brickeconomy_price(set_id)
            
            # Fallback to BrickLink if needed
            if not price:
                price = await self.fetch_bricklink_price(set_id)
            
            if price and price > 0:
                target.current_price = price
                target.last_updated = datetime.now().isoformat()
                target.scrape_count += 1
                
                # Update Prometheus metrics
                appreciation = price / target.retail_price if target.retail_price > 0 else 0
                lego_set_price.labels(
                    set_id=set_id,
                    name=target.name,
                    theme=target.theme
                ).set(price)
                
                lego_set_appreciation.labels(
                    set_id=set_id,
                    name=target.name
                ).set(appreciation)
                
                lego_scrape_success.inc()
                
                # Log price history
                self._log_price_history(set_id, target.name, price, appreciation)
                
                logger.info(f"✓ {target.name}: ${price:.2f} ({appreciation:.2f}x retail)")
            else:
                target.scrape_failures += 1
                lego_scrape_errors.labels(set_id=set_id, error_type='no_price').inc()
                logger.warning(f"✗ {target.name}: No price found")
        
        except Exception as e:
            target.scrape_failures += 1
            lego_scrape_errors.labels(set_id=set_id, error_type='exception').inc()
            logger.error(f"Error scraping {set_id}: {e}")
    
    def _log_price_history(self, set_id: str, name: str, price: float, appreciation: float):
        """Append price to JSONL history"""
        try:
            record = {
                'timestamp': datetime.now().isoformat(),
                'set_id': set_id,
                'name': name,
                'price': price,
                'appreciation': appreciation,
            }
            with open(self.price_history_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"Failed to log price history: {e}")
    
    def update_portfolio_metrics(self):
        """Calculate and update portfolio metrics"""
        holdings = self.portfolio.get('holdings', [])
        
        if not holdings:
            lego_portfolio_value.set(0)
            lego_portfolio_gain.set(0)
            lego_portfolio_roi.set(0)
            return
        
        total_invested = 0
        total_market_value = 0
        
        for holding in holdings:
            set_id = holding.get('set_id')
            purchase_price = holding.get('purchase_price', 0)
            quantity = holding.get('quantity', 1)
            
            # Get current price from targets or use last known
            current_price = purchase_price  # Default to purchase price
            if set_id in self.targets and self.targets[set_id].current_price:
                current_price = self.targets[set_id].current_price
            
            total_invested += purchase_price * quantity
            total_market_value += current_price * quantity
        
        unrealized_gain = total_market_value - total_invested
        roi_percent = (unrealized_gain / total_invested * 100) if total_invested > 0 else 0
        
        lego_portfolio_value.set(total_market_value)
        lego_portfolio_gain.set(unrealized_gain)
        lego_portfolio_roi.set(roi_percent)
        
        logger.info(f"Portfolio: ${total_market_value:.2f} | Gain: ${unrealized_gain:.2f} | ROI: {roi_percent:.1f}%")
    
    async def run_scrape_cycle(self):
        """Run one scrape cycle for all targets"""
        logger.info("=" * 60)
        logger.info(f"Starting scrape cycle ({len(self.targets)} sets)")
        logger.info("=" * 60)
        
        with lego_scrape_duration.time():
            tasks = [
                self.scrape_set(set_id, target)
                for set_id, target in self.targets.items()
            ]
            await asyncio.gather(*tasks)
        
        # Update portfolio metrics
        self.update_portfolio_metrics()
        
        logger.info(f"Scrape cycle complete")
    
    async def run_loop(self, interval_seconds: int = 3600):
        """Continuously run scraping"""
        logger.info(f"Starting LEGO monitor loop (interval: {interval_seconds}s)")
        
        while True:
            try:
                await self.run_scrape_cycle()
            except Exception as e:
                logger.error(f"Unexpected error in scrape loop: {e}")
            
            logger.info(f"Next scrape in {interval_seconds}s...")
            await asyncio.sleep(interval_seconds)


async def main():
    # Start Prometheus metrics server
    metrics_port = int(os.getenv('METRICS_PORT', '8888'))
    logger.info(f"Starting Prometheus metrics server on port {metrics_port}")
    start_http_server(metrics_port)
    
    # Initialize scraper
    scraper = LegoMarketScraper()
    
    # Scrape interval (default: hourly for LEGO, prices don't change fast)
    interval = int(os.getenv('SCRAPE_INTERVAL_SECONDS', '3600'))
    
    # Run scraper loop
    await scraper.run_loop(interval)


if __name__ == '__main__':
    asyncio.run(main())
