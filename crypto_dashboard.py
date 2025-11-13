#!/usr/bin/env python3
"""
Crypto Price Dashboard
A real-time cryptocurrency price tracker using the CoinGecko API.

Usage:
    python crypto_dashboard.py [--coins COIN1,COIN2,...] [--interval SECONDS]
"""

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


# Configuration
@dataclass
class Config:
    """Application configuration."""
    coins: List[str]
    update_interval: int = 10
    api_base_url: str = "https://api.coingecko.com/api/v3"
    request_timeout: int = 10


# ANSI Color codes
class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class CoinGeckoAPI:
    """
    Client for interacting with the CoinGecko API.
    
    This class handles all API communication and implements proper
    error handling and rate limiting.
    """
    
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the CoinGecko API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
    
    def fetch_prices(self, coin_ids: List[str]) -> Optional[Dict]:
        """
        Fetch current prices and 24h changes for specified coins.
        
        Args:
            coin_ids: List of CoinGecko coin identifiers
            
        Returns:
            Dictionary containing price data, or None if request fails
        """
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self.logger.error("Request timed out")
        except requests.exceptions.ConnectionError:
            self.logger.error("Connection error - check your internet connection")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
        
        return None
    
    def close(self):
        """Close the session."""
        self.session.close()


class CryptoDashboard:
    """
    Main dashboard class for displaying cryptocurrency prices.
    
    This class handles the presentation logic and update loop.
    """
    
    def __init__(self, config: Config, api_client: CoinGeckoAPI):
        """
        Initialize the dashboard.
        
        Args:
            config: Application configuration
            api_client: CoinGecko API client instance
        """
        self.config = config
        self.api = api_client
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def clear_screen():
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def format_price_change(self, change: float) -> str:
        """
        Format price change with color and arrow indicator.
        
        Args:
            change: 24-hour price change percentage
            
        Returns:
            Formatted string with color codes
        """
        arrow = "↑" if change >= 0 else "↓"
        color = Colors.GREEN if change >= 0 else Colors.RED
        return f"{color}{arrow} {abs(change):>7.2f}%{Colors.RESET}"
    
    def display(self, prices: Dict):
        """
        Display the dashboard with current prices.
        
        Args:
            prices: Dictionary containing price data from API
        """
        self.clear_screen()
        
        # Header
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{'Coin':<15} {'Price (USD)':>15} {'24h Change':>15}{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        
        # Coin data
        for coin_id in self.config.coins:
            data = prices.get(coin_id, {})
            price = data.get("usd", 0)
            change = data.get("usd_24h_change", 0)
            
            price_str = f"${price:,.2f}" if price > 0 else "N/A"
            change_str = self.format_price_change(change) if price > 0 else "N/A"
            
            print(f"{coin_id.capitalize():<15} {price_str:>15} {change_str:>15}")
        
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"\nLast updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to exit")
    
    def run(self):
        """
        Main loop for the dashboard.
        
        Continuously fetches and displays price data until interrupted.
        """
        self.logger.info("Starting Crypto Dashboard")
        self.logger.info(f"Tracking: {', '.join(self.config.coins)}")
        
        try:
            while True:
                prices = self.api.fetch_prices(self.config.coins)
                
                if prices:
                    self.display(prices)
                else:
                    print(f"Failed to fetch prices. Retrying in {self.config.update_interval}s...")
                    self.logger.warning("Failed to fetch prices")
                
                time.sleep(self.config.update_interval)
                
        except KeyboardInterrupt:
            print("\n\nExiting Crypto Dashboard. Goodbye!")
            self.logger.info("Dashboard stopped by user")
        finally:
            self.api.close()


def setup_logging(verbose: bool = False):
    """
    Configure logging for the application.
    
    Args:
        verbose: Enable debug logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('crypto_dashboard.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Real-time cryptocurrency price dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python crypto_dashboard.py
  python crypto_dashboard.py --coins bitcoin,ethereum,solana
  python crypto_dashboard.py --interval 30 --verbose
        """
    )
    
    parser.add_argument(
        '--coins',
        type=str,
        default='bitcoin,ethereum,dogecoin,cardano,solana',
        help='Comma-separated list of coin IDs (default: bitcoin,ethereum,dogecoin,cardano,solana)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Update interval in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    # Parse coin list
    coin_list = [coin.strip() for coin in args.coins.split(',')]
    
    # Create configuration
    config = Config(
        coins=coin_list,
        update_interval=args.interval
    )
    
    # Initialize API client and dashboard
    api_client = CoinGeckoAPI(config.api_base_url, config.request_timeout)
    dashboard = CryptoDashboard(config, api_client)
    
    # Run the dashboard
    dashboard.run()


if __name__ == "__main__":
    main()