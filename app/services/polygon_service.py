import aiohttp
from typing import List, Dict, Any, Optional
from app.core.config import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PolygonService:
    """
    Service for interacting with Polygon.io API
    API Documentation: https://polygon.io/docs/stocks/getting-started
    """
    
    def __init__(self):
        self.stocks_api_key = settings.polygon_stocks_api_key
        self.options_api_key = settings.polygon_stocks_api_key
        
    async def _make_request(self, url: str, type: str) -> Dict[str, Any]:
        """
        Make async request to Polygon API
        """
        
        # Check if URL already has query parameters
        separator = "&" if "?" in url else "?"
        
        if type == "options":
            url = f"{url}{separator}apiKey={self.options_api_key}"
        else:
            url = f"{url}{separator}apiKey={self.stocks_api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print("error making request", error_text)
                        raise Exception(f"Polygon API error: {response.status}")
        except Exception as e:
            # Return empty result instead of raising to prevent complete failure
            print("error making request", e)
            return {"results": [], "status": "ERROR"}
        
    async def _get_ticker_details_data(self, type: str, ticker: str) -> Dict[str, Any]:
        """
        Get ticker details data from Polygon API
        """
        
        try:
            ticker_details_url = f"https://api.massive.com/v3/reference/tickers/{ticker}"
            ticker_details_data = await self._make_request(ticker_details_url, "stocks")
        
            if type == "stock":
                market_cap = ticker_details_data.get("results", {}).get("market_cap", 0)
                name = ticker_details_data.get("results", {}).get("name", "N/A")
        
                return {
                    "marketCap": market_cap,
                    "name": name,
                }
            elif type == "crypto":
                name = ticker_details_data.get("results", {}).get("name", "N/A")
                
                return {
                    "name": name,
                }
            elif type == "forex":
                name = ticker_details_data.get("results", {}).get("name", "N/A")
                
                return {
                    "name": name,
                }
        except Exception as e:
            print("error getting ticker details data", e)
            return {}
    
    async def _get_dividend_yield_data(self, ticker: str, price: float) -> Dict[str, Any]:
        """
        Get dividend yield data from Polygon API
        """
        try:
            dividends_url = f"https://api.massive.com/v3/reference/dividends?ticker={ticker}"
            dividends_data = await self._make_request(dividends_url, "stocks")
            dividends = dividends_data.get("results", [])
            
            if len(dividends) > 0:
                latest_dividend = dividends[0]
                cash_amount = latest_dividend.get("cash_amount", 0)
                frequency = latest_dividend.get("frequency", 4)  # Default to quarterly
                annual_dividend = cash_amount * frequency
                dividend_yield = (annual_dividend / price) * 100
                
                return {
                    "dividendYield": dividend_yield,
                }
                
            return {
                "dividendYield": 0,
            }
        except Exception as e:
            print("error getting dividends data", e)
            return {
                "dividendYield": 0,
            }
        
    def _get_snapshot_data(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get stock snapshot data
        """
        
        ticker = snapshot.get("ticker", "")
        volume = snapshot.get("day", {}).get("v", 0)
        price = snapshot.get("day", {}).get("c", 0)
        change_percent = snapshot.get("todaysChangePerc", 0)
        
        return {
            "ticker": ticker,
            "volume": volume,
            "price": price,
            "changePercent": change_percent,
        }
    
    async def screen_stocks(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks using Polygon API
        """
        
        try:
            current_page_results = []
            # Apply search filter if provided
            if search:
                search = search.upper()
                snapshot_url = f"https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers/{search}"
                snapshot_data = await self._make_request(snapshot_url, "stocks")
                snapshot_data = snapshot_data.get("ticker", {})
        
                if not snapshot_data:
                    print("No snapshot data received from Polygon API")
                    return []
                
                ticker_details_data = await self._get_ticker_details_data("stock", search)
                stock_snapshot_data = self._get_snapshot_data(snapshot_data)
                dividend_yield_data = await self._get_dividend_yield_data(search, stock_snapshot_data['price'])                    
        
                current_page_results.append({
                    **stock_snapshot_data,
                    **ticker_details_data,
                    **dividend_yield_data,
                })
            else:    
                snapshot_url = "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers"
                snapshot_data = await self._make_request(snapshot_url, "stocks");
                snapshot_data = snapshot_data.get("tickers", [])
        
                if not snapshot_data:
                    print("No snapshot data received from Polygon API")
                    return []
                
                # Calculate pagination offsets
                items_per_page = limit
                start_index = (page - 1) * items_per_page
                end_index = start_index + items_per_page
                
                # Process only the stocks for the current page
                current_page_stocks = snapshot_data[start_index:end_index]
            
                for i, snapshot in enumerate(current_page_stocks):
                    try:
                        ticker_details_data = await self._get_ticker_details_data("stock", snapshot['ticker'])
                        stock_snapshot_data = self._get_snapshot_data(snapshot)
                        dividend_yield_data = await self._get_dividend_yield_data(snapshot['ticker'], stock_snapshot_data['price'])                          

                        current_page_results.append({
                            **stock_snapshot_data,
                            **ticker_details_data,
                            **dividend_yield_data,
                        })   
                    except Exception as e:
                        print("error processing stock", e)
                        continue
            
            if not current_page_results:
                print("no current page results")
                return []
            
            return current_page_results
        except Exception as e:
            print("error processing stocks", e)
            return []
    
    async def screen_crypto(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Screen cryptocurrencies using Polygon API
        """
        try:
            current_page_results = []

            if search:
                search = f"X:{search.upper()}"
                snapshot_url = f"https://api.massive.com/v2/snapshot/locale/global/markets/crypto/tickers/{search}"
                snapshot_data = await self._make_request(snapshot_url, "crypto");
                snapshot_data = snapshot_data.get("ticker", {})

                if not snapshot_data:
                    print("No snapshot data received from Polygon API")
                    return []
                
                ticker_details_data = await self._get_ticker_details_data("crypto", search)
                crypto_snapshot_data = self._get_snapshot_data(snapshot_data)

                current_page_results.append({
                    **ticker_details_data,
                    **crypto_snapshot_data,
                })   
            else:
                snapshot_url = "https://api.massive.com/v2/snapshot/locale/global/markets/crypto/tickers"
                snapshot_data = await self._make_request(snapshot_url, "crypto");
                snapshot_data = snapshot_data.get("tickers", [])
            
            # Calculate pagination offsets
                items_per_page = limit
                start_index = (page - 1) * items_per_page
                end_index = start_index + items_per_page
                
                # Process only the stocks for the current page
                current_page_crypto = snapshot_data[start_index:end_index]
                
                for i, snapshot in enumerate(current_page_crypto):
                    try:
                        ticker_details_data = await self._get_ticker_details_data("crypto", snapshot['ticker'])
                        crypto_snapshot_data = self._get_snapshot_data(snapshot)

                        current_page_results.append({
                            **ticker_details_data,
                            **crypto_snapshot_data,
                        })   
                    except Exception as e:
                        print("error processing crypto", e)
                        continue
            
            if not current_page_results:
                print("no current page results")
                return []
            
            return current_page_results
            
        except Exception as e:
            print("error processing crypto", e)
            return []
    
    async def screen_forex(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Screen forex using Polygon API
        """
        
        try:
            current_page_results = []
            if search:
                search = f"C:{search.upper()}"
                snapshot_url = f"https://api.massive.com/v2/snapshot/locale/global/markets/forex/tickers/{search}"
                snapshot_data = await self._make_request(snapshot_url, "forex");
                snapshot_data = snapshot_data.get("ticker", {})        

                if not snapshot_data:
                    print("No snapshot data received from Polygon API")
                    return []
                
                ticker_details_data = await self._get_ticker_details_data("forex", search)
                forex_snapshot_data = self._get_snapshot_data(snapshot_data)

                current_page_results.append({
                    **ticker_details_data,
                    **forex_snapshot_data,
                })   
            else:
                snapshot_url = "https://api.massive.com/v2/snapshot/locale/global/markets/forex/tickers"
                snapshot_data = await self._make_request(snapshot_url, "forex");
                snapshot_data = snapshot_data.get("tickers", [])
                print(f"Total forex in snapshot: {len(snapshot_data)}")

                if not snapshot_data:
                    print("No snapshot data received from Polygon API")
                    return []
                
                # Calculate pagination offsets
                items_per_page = limit
                start_index = (page - 1) * items_per_page
                end_index = start_index + items_per_page
                
                # Process only the stocks for the current page
                current_page_forex = snapshot_data[start_index:end_index]
                
                for i, snapshot in enumerate(current_page_forex):
                    try:
                        ticker_details_data = await self._get_ticker_details_data("forex", snapshot['ticker'])
                        forex_snapshot_data = self._get_snapshot_data(snapshot)

                        current_page_results.append({
                            **ticker_details_data,
                            **forex_snapshot_data,
                        })   
                    except Exception as e:
                        print("error processing forex", e)
                        continue
                
            if not current_page_results:
                print("no current page results")
                return []
            
            return current_page_results
            
        except Exception as e:
            print("error processing forex", e)
            return []
    
    async def screen_options(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Screen options using Polygon API
        """
        
        try:
            count = 0
            current_page_results = []

            if search:
                search = search.upper()
                snapshot_url = f"https://api.massive.com/v3/snapshot/options/{search}?order=asc&limit={limit}&sort=ticker"
                while snapshot_url:
                    snapshot_data = await self._make_request(snapshot_url, "options");
                    snapshot_url = snapshot_data.get("next_url", None)
                    snapshot_data = snapshot_data.get("results", [])            
                    
                    if not snapshot_data:
                        break
                    
                    current_page_results = snapshot_data
                    count += 1
                    
                    if page == count:
                        break
                    
            if not current_page_results:
                print("no current page results")
                return []
            
            return current_page_results
            
        except Exception as e:
            print("error processing options", e)
            return []
        
    def _calculate_stock_score(self, change_percent: float, volume: float, price: float) -> float:
        """Calculate AI score for stocks"""
        score = 5.0  # Base score
        
        # Positive momentum
        if change_percent > 2:
            score += 2
        elif change_percent > 0:
            score += 1
        
        # High volume
        if volume > 10000000:
            score += 1.5
        elif volume > 5000000:
            score += 0.5
        
        # Price
        if price > 100:
            score += 1
        elif price > 50:
            score += 0.5
        
        return min(max(score, 0), 10)