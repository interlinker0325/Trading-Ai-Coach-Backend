from typing import Dict, List, Set, Callable
import threading
from massive import WebSocketClient
from massive.websocket.models import WebSocketMessage, Feed, Market
from app.core.config import settings

class MarketWebSocketService:
    """
    Service for managing Polygon WebSocket connections for real-time market data
    """
    
    # Fixed top 5 symbols for each asset class
    TOP_STOCKS = ["AM.AAPL", "AM.MSFT", "AM.GOOGL", "AM.AMZN", "AM.TSLA"]
    TOP_CRYPTO = ["XA.BTC-USD", "XA.ETH-USD", "XA.SOL-USD", "XA.BNB-USD", "XA.XRP-USD"]
    TOP_FOREX = ["CA.EUR/USD", "CA.GBP/USD", "CA.USD/JPY", "CA.AUD/USD", "CA.USD/CAD"]
    TOP_COMMODITIES = ["CA.XAU/USD", "CA.XAG/USD"]
    
    def __init__(self):
        self.stocks_api_key = settings.polygon_stocks_api_key
        self.currencies_api_key = settings.polygon_currencies_api_key
        self.ws_clients: Dict[str, WebSocketClient] = {}
        self.subscribers: Set[Callable] = set()
        self.current_data: Dict[str, Dict] = {}
        self._running = False
        self._threads: Dict[str, threading.Thread] = {}
        
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format for display"""
        # Remove prefixes: AM. -> stocks, XA. -> crypto, CA. -> forex/commodities
        return symbol[3:]

    def _get_asset_type(self, symbol: str, market_type: str = None) -> str:
        """Determine asset type from symbol and optional market type"""
        # If market type is provided, use it
        if market_type:
            if market_type == "stocks":
                return "stocks"
            elif market_type == "crypto":
                return "crypto"
            elif market_type == "forex":
                # Check if it's a commodity based on symbol
                if any(comm in symbol.upper() for comm in ["XAU", "XAG"]):
                    return "commodities"
                return "forex"
        
        # Fallback to symbol-based detection
        return "stocks"
    
    def _parse_message(self, msg: WebSocketMessage, market_type: str = None) -> Dict:
        """Parse WebSocket message and extract relevant data"""
        try:
            # Handle EquityAgg objects (from massive websocket)
            symbol = None
            price = None
            change_percent = None
            
            # Check if it's an object with attributes (like EquityAgg, CryptoAgg, etc.)
            if hasattr(msg, 'symbol'):
                symbol = msg.symbol
            elif hasattr(msg, 'pair'):
                symbol = msg.pair
            elif hasattr(msg, 'sym'):
                symbol = msg.sym
            
            if not symbol:
                return None
            
            # Get close price (most recent price)
            if hasattr(msg, 'close'):
                price = msg.close
            elif hasattr(msg, 'c'):
                price = msg.c
            elif hasattr(msg, 'last_price'):
                price = msg.last_price
            elif hasattr(msg, 'p'):
                price = msg.p
            
            if price is None:
                return None
            
            # Calculate change percentage from open and close
            if hasattr(msg, 'open') and hasattr(msg, 'close') and msg.open and msg.close:
                open_price = msg.open
                close_price = msg.close
                if open_price > 0:
                    change_percent = ((close_price - open_price) / open_price) * 100
            # Or use provided change percentage if available
            elif hasattr(msg, 'dp'):
                change_percent = msg.dp
            elif hasattr(msg, 'change_percent'):
                change_percent = msg.change_percent
            elif hasattr(msg, 'todaysChangePerc'):
                change_percent = msg.todaysChangePerc
            elif hasattr(msg, 'pct_change'):
                change_percent = msg.pct_change
            
            # Fallback to dict access
            if isinstance(msg, dict):
                symbol = symbol or msg.get('symbol') or msg.get('sym') or msg.get('pair')
                price = price or msg.get('close') or msg.get('c') or msg.get('last_price') or msg.get('price') or msg.get('p')
                
                # Calculate change percentage
                if msg.get('open') and msg.get('close'):
                    open_price = msg['open']
                    close_price = msg['close']
                    if open_price > 0:
                        change_percent = ((close_price - open_price) / open_price) * 100
                else:
                    change_percent = change_percent or msg.get('dp') or msg.get('change_percent') or msg.get('todaysChangePerc') or msg.get('pct_change')
            
            if not symbol or price is None:
                return None
            
            # Normalize symbol (remove prefix like AM., XA., CA.)
            asset_type = self._get_asset_type(symbol, market_type)
            
            return {
                "symbol": symbol,
                "price": float(price),
                "change": float(change_percent) if change_percent is not None else 0.0,
                "asset_type": asset_type,
            }
        except Exception as e:
            print(f"Error parsing WebSocket message: {e}, message type: {type(msg)}")
        
        return None
    
    def _create_message_handler(self, market_type: str):
        """Create a message handler function for a specific market type"""
        def handle_message(messages: List[WebSocketMessage]):
            """Handle incoming WebSocket messages for a specific market"""
            for msg in messages:
                try:
                    parsed_data = self._parse_message(msg, market_type)
                    print(f"Parsed data: {parsed_data}")
                    if parsed_data:
                        symbol = parsed_data["symbol"]
                        asset_type = parsed_data["asset_type"]
                        
                        # Update current data
                        if asset_type not in self.current_data:
                            self.current_data[asset_type] = {}
                        
                        self.current_data[asset_type][symbol] = {
                            "symbol": symbol,
                            "price": parsed_data["price"],
                            "change": parsed_data["change"]
                        }
                        
                        # Notify all subscribers
                        for subscriber in self.subscribers:
                            try:
                                subscriber(parsed_data)
                            except Exception as e:
                                print(f"Error notifying subscriber: {e}")
                except Exception as e:
                    print(f"Error handling message: {e}")
        
        return handle_message
    
    def start(self):
        """Start all WebSocket connections for different market types"""
        if self._running:
            print("WebSocket service already running")
            return
        
        try:
            # Start Stocks WebSocket
            self._start_market_client("stocks", Market.Stocks, self.TOP_STOCKS)
            
            # Start Crypto WebSocket
            self._start_market_client("crypto", Market.Crypto, self.TOP_CRYPTO)
            
            # Start Forex WebSocket (forex and commodities use the same market)
            self._start_market_client("forex", Market.Forex, self.TOP_FOREX + self.TOP_COMMODITIES)
            
            self._running = True
            print("All WebSocket services started")
            
        except Exception as e:
            print(f"Error starting WebSocket service: {e}")
            self._running = False
    
    def _start_market_client(self, market_name: str, market_type: Market, subscriptions: List[str]):
        """Start a WebSocket client for a specific market type"""
        try:
            api_key = None
            if market_name == "forex" or market_name == "crypto":
                api_key = self.currencies_api_key
            else:
                api_key = self.stocks_api_key

            if market_name == "stocks":
                ws_client = WebSocketClient(
                    api_key=api_key,
                    feed=Feed.Delayed,
                    market=market_type
                )
            else:
                ws_client = WebSocketClient(
                    api_key=api_key,
                    feed=Feed.RealTime,
                    market=market_type
                )
            
            # Subscribe to all symbols for this market
            if subscriptions:
                ws_client.subscribe(*subscriptions)

            
            self.ws_clients[market_name] = ws_client
            
            # Create handler for this market
            handler = self._create_message_handler(market_name)
            
            # Run in background thread
            thread = threading.Thread(
                target=self._run_websocket,
                args=(market_name, ws_client, handler),
                daemon=True
            )
            thread.start()
            self._threads[market_name] = thread
            
            print(f"Started WebSocket client for {market_name} with {len(subscriptions)} subscriptions")
            
        except Exception as e:
            print(f"Error starting {market_name} WebSocket client: {e}")
    
    def _run_websocket(self, market_name: str, ws_client: WebSocketClient, handler: Callable):
        """Run WebSocket client in blocking mode"""
        try:
            ws_client.run(handle_msg=handler)
        except Exception as e:
            print(f"WebSocket connection error for {market_name}: {e}")
            # Mark as not running if all clients fail
            if market_name in self.ws_clients:
                del self.ws_clients[market_name]
    
    def stop(self):
        """Stop all WebSocket connections"""
        self._running = False
        for market_name, ws_client in self.ws_clients.items():
            try:
                # Close connection if possible
                # Note: WebSocketClient may have a close method
                if hasattr(ws_client, 'close'):
                    ws_client.close()
            except Exception as e:
                print(f"Error stopping {market_name} WebSocket service: {e}")
        
        self.ws_clients.clear()
        self._threads.clear()
    
    def subscribe(self, callback: Callable):
        """Subscribe to market data updates"""
        self.subscribers.add(callback)
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from market data updates"""
        self.subscribers.discard(callback)
    
    def get_current_data(self) -> Dict:
        """Get current market data snapshot"""
        return {
            "stocks": [
                self.current_data.get("stocks", {}).get(symbol.replace("AM.", ""), {
                    "symbol": symbol.replace("AM.", ""),
                    "price": 0,
                    "change": 0
                })
                for symbol in self.TOP_STOCKS
            ],
            "crypto": [
                self.current_data.get("crypto", {}).get(symbol.replace("XA.", ""), {
                    "symbol": symbol.replace("XA.", ""),
                    "price": 0,
                    "change": 0
                })
                for symbol in self.TOP_CRYPTO
            ],
            "forex": [
                self.current_data.get("forex", {}).get(symbol.replace("CA.", ""), {
                    "symbol": symbol.replace("CA.", ""),
                    "price": 0,
                    "change": 0
                })
                for symbol in self.TOP_FOREX
            ],
            "commodities": [
                self.current_data.get("commodities", {}).get(symbol.replace("CA.", ""), {
                    "symbol": symbol.replace("CA.", ""),
                    "price": 0,
                    "change": 0
                })
                for symbol in self.TOP_COMMODITIES
            ]
        }

# Global instance
_websocket_service: MarketWebSocketService = None

def get_websocket_service() -> MarketWebSocketService:
    """Get or create WebSocket service instance"""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = MarketWebSocketService()
        _websocket_service.start()
    return _websocket_service

