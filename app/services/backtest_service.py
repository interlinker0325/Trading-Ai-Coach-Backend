from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from app.models.backtest import BacktestStrategy, BacktestResult, BacktestStatus, AssetType
from app.crud import backtest as crud
from app.services.polygon_service import PolygonService
from app.core.config import settings
from openai import OpenAI
import json
import math


class BacktestService:
    """Service for running backtests and calculating performance metrics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.polygon_service = PolygonService()
        self.openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
    
    def create_strategy_from_natural_language(
        self,
        query: str,
        user_id: int,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 100000.0
    ) -> Optional[BacktestStrategy]:
        """
        Parse natural language query using AI and create a strategy.
        
        Example queries:
        - "Backtest buying AAPL when RSI < 30, sell when RSI > 70, last 5 years with 2% position sizing and 5% stop loss"
        - "Test a MACD crossover strategy on BTC/USD for the past year with 10% take profit"
        - "Backtest gold when price crosses above SMA(50), exit when price crosses below SMA(50), last 3 years"
        """
        if not self.openai_client:
            print("OpenAI API key not configured. Cannot parse natural language queries.")
            return None
        
        try:
            # Parse the query with AI
            parsed_strategy = self._parse_natural_language_with_ai(
                query,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital
            )
            
            if not parsed_strategy:
                return None
            
            # Create strategy name if not provided
            strategy_name = parsed_strategy.get("name") or f"AI Strategy: {query[:50]}..."
            
            # Create the strategy in database
            strategy_data = {
                "name": strategy_name,
                "symbol": parsed_strategy["symbol"],
                "asset_type": AssetType(parsed_strategy["asset_type"]),
                "timeframe": parsed_strategy["timeframe"],
                "start_date": parsed_strategy["start_date"],
                "end_date": parsed_strategy["end_date"],
                "initial_capital": parsed_strategy.get("initial_capital", initial_capital),
                "indicators": parsed_strategy.get("indicators", []),
                "entry_rules": parsed_strategy.get("entry_rules"),
                "exit_rules": parsed_strategy.get("exit_rules"),
                "stop_loss": parsed_strategy.get("stop_loss"),
                "take_profit": parsed_strategy.get("take_profit"),
                "position_size": parsed_strategy.get("position_size"),
                "natural_language_query": query
            }
            
            from app.schemas.backtest import BacktestStrategyCreate
            strategy_create = BacktestStrategyCreate(**strategy_data)
            strategy = crud.create_backtest_strategy(self.db, strategy_create, user_id)
            
            return strategy
            
        except Exception as e:
            print(f"Error parsing natural language query: {str(e)}")
            return None
    
    def _parse_natural_language_with_ai(
        self,
        query: str,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 100000.0
    ) -> Optional[Dict[str, Any]]:
        """Use OpenAI to parse natural language and extract strategy parameters"""
        
        # Build the prompt
        system_prompt = """You are an expert trading strategy parser. Extract trading strategy parameters from natural language queries.

Extract the following information:
1. **symbol**: Trading symbol (e.g., "AAPL", "BTC/USD", "EUR/USD", "gold", "XAU/USD"). If not mentioned, infer from context.
2. **asset_type**: One of: "stocks", "crypto", "forex", "commodities", "options", "futures"
3. **timeframe**: Chart timeframe (e.g., "1m", "5m", "15m", "1h", "4h", "1d", "1w"). Default to "1d" if not specified.
4. **start_date**: Start date in ISO format (YYYY-MM-DD). If relative (e.g., "last 5 years", "past year"), calculate from today.
5. **end_date**: End date in ISO format (YYYY-MM-DD). Default to today if not specified.
6. **indicators**: List of technical indicators mentioned (e.g., ["RSI", "MACD", "SMA", "EMA", "BB", "ATR"])
7. **entry_rules**: Entry conditions in rule format (e.g., "RSI < 30", "PRICE CROSSES ABOVE SMA(50)", "MACD CROSSES ABOVE SIGNAL")
8. **exit_rules**: Exit conditions in rule format (e.g., "RSI > 70", "PRICE CROSSES BELOW SMA(50)", "MACD CROSSES BELOW SIGNAL")
9. **stop_loss**: Stop loss percentage (e.g., 5 means 5%). Extract if mentioned.
10. **take_profit**: Take profit percentage (e.g., 10 means 10%). Extract if mentioned.
11. **position_size**: Position size percentage (e.g., 2 means 2% of capital per trade). Extract if mentioned.
12. **initial_capital**: Initial capital amount. Use provided value if not mentioned.
13. **name**: A short descriptive name for the strategy (max 100 chars)

Rule format examples:
- "RSI < 30" → RSI indicator is less than 30
- "RSI > 70" → RSI indicator is greater than 70
- "PRICE CROSSES ABOVE SMA(50)" → Price crosses above 50-period SMA
- "PRICE CROSSES BELOW SMA(50)" → Price crosses below 50-period SMA
- "MACD CROSSES ABOVE SIGNAL" → MACD line crosses above signal line
- "MACD CROSSES BELOW SIGNAL" → MACD line crosses below signal line
- "PRICE > EMA(20)" → Price is above 20-period EMA
- "BB_UPPER" → Bollinger Band upper band
- "BB_LOWER" → Bollinger Band lower band

Return ONLY valid JSON in this exact format:
{
  "symbol": "AAPL",
  "asset_type": "stocks",
  "timeframe": "1d",
  "start_date": "2019-01-01T00:00:00Z",
  "end_date": "2024-01-01T00:00:00Z",
  "indicators": ["RSI"],
  "entry_rules": "RSI < 30",
  "exit_rules": "RSI > 70",
  "stop_loss": 5.0,
  "take_profit": null,
  "position_size": 2.0,
  "initial_capital": 100000.0,
  "name": "RSI Oversold/Overbought Strategy"
}"""

        user_prompt = f"""Parse this trading strategy query:

"{query}"

Additional context:
- Symbol (if provided): {symbol or "not specified"}
- Start date (if provided): {start_date.isoformat() if start_date else "not specified"}
- End date (if provided): {end_date.isoformat() if end_date else "not specified"}
- Initial capital: ${initial_capital:,.2f}

Extract all parameters and return valid JSON only."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Validate and normalize the parsed data
            return self._normalize_parsed_strategy(parsed, symbol, start_date, end_date, initial_capital)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            print(f"Response content: {content}")
            return None
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None
    
    def _normalize_parsed_strategy(
        self,
        parsed: Dict[str, Any],
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 100000.0
    ) -> Dict[str, Any]:
        """Normalize and validate parsed strategy data"""
        
        # Use provided values as fallback
        final_symbol = parsed.get("symbol") or symbol or "AAPL"
        final_start_date = self._parse_date(parsed.get("start_date"), start_date, default_days_ago=365*5)
        final_end_date = self._parse_date(parsed.get("end_date"), end_date, default_days_ago=0)
        final_asset_type = parsed.get("asset_type", "stocks").lower()
        final_timeframe = parsed.get("timeframe", "1d")
        
        # Normalize asset type
        asset_type_map = {
            "stock": "stocks",
            "equity": "stocks",
            "cryptocurrency": "crypto",
            "currency": "forex",
            "forex": "forex",
            "commodity": "commodities",
            "option": "options",
            "future": "futures"
        }
        final_asset_type = asset_type_map.get(final_asset_type, final_asset_type)
        
        # Ensure asset_type is valid
        valid_asset_types = ["stocks", "crypto", "forex", "commodities", "options", "futures"]
        if final_asset_type not in valid_asset_types:
            final_asset_type = "stocks"
        
        # Normalize timeframe
        timeframe_map = {
            "1 minute": "1m",
            "5 minutes": "5m",
            "15 minutes": "15m",
            "30 minutes": "30m",
            "1 hour": "1h",
            "4 hours": "4h",
            "1 day": "1d",
            "daily": "1d",
            "1 week": "1w",
            "weekly": "1w"
        }
        final_timeframe = timeframe_map.get(final_timeframe.lower(), final_timeframe)
        
        # Normalize indicators (uppercase, remove duplicates)
        indicators = parsed.get("indicators", [])
        if isinstance(indicators, str):
            indicators = [indicators]
        indicators = [ind.upper() for ind in indicators if ind]
        indicators = list(set(indicators))  # Remove duplicates
        
        # Normalize entry/exit rules
        entry_rules = parsed.get("entry_rules") or ""
        exit_rules = parsed.get("exit_rules") or ""
        
        return {
            "symbol": final_symbol.upper().replace(" ", ""),
            "asset_type": final_asset_type,
            "timeframe": final_timeframe,
            "start_date": final_start_date,
            "end_date": final_end_date,
            "indicators": indicators,
            "entry_rules": entry_rules.strip(),
            "exit_rules": exit_rules.strip(),
            "stop_loss": parsed.get("stop_loss"),
            "take_profit": parsed.get("take_profit"),
            "position_size": parsed.get("position_size"),
            "initial_capital": parsed.get("initial_capital", initial_capital),
            "name": parsed.get("name", f"AI Strategy: {final_symbol}")
        }
    
    def _parse_date(self, date_str: Optional[str], provided_date: Optional[datetime], default_days_ago: int) -> datetime:
        """Parse date string or use provided date or calculate from default"""
        if provided_date:
            return provided_date
        
        if not date_str:
            return datetime.now(timezone.utc) - timedelta(days=default_days_ago)
        
        try:
            # Try ISO format
            if "T" in date_str:
                parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                # Ensure timezone-aware
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            else:
                # Try date only format
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
                return parsed.replace(tzinfo=timezone.utc)
        except:
            # If parsing fails, use default
            return datetime.now(timezone.utc) - timedelta(days=default_days_ago)
    
    async def run_backtest(self, strategy_id: int, result_id: int):
        """
        Main backtest execution function.
        This runs the strategy against historical data and calculates results.
        """
        try:
            # Update status to running
            crud.update_backtest_result(
                self.db, result_id, {
                    "status": BacktestStatus.RUNNING,
                    "started_at": datetime.now(timezone.utc)
                }
            )
            
            # Get strategy
            strategy = crud.get_backtest_strategy(self.db, strategy_id)
            if not strategy:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            # Fetch historical data
            historical_data = await self._fetch_historical_data(strategy)
            
            if not historical_data:
                raise ValueError("Failed to fetch historical data")
            
            # Calculate indicators
            data_with_indicators = self._calculate_indicators(historical_data, strategy.indicators or [])
            
            # Execute strategy
            trades = self._execute_strategy(data_with_indicators, strategy)
            
            # Calculate performance metrics
            metrics = self._calculate_metrics(trades, strategy.initial_capital)
            
            # Generate equity curve
            equity_curve = self._generate_equity_curve(trades, strategy.initial_capital, historical_data)
            
            # Save trades to database
            if trades:
                trade_data = [
                    {
                        "entry_date": trade["entry_date"],
                        "exit_date": trade.get("exit_date"),
                        "entry_price": trade["entry_price"],
                        "exit_price": trade.get("exit_price"),
                        "quantity": trade["quantity"],
                        "trade_type": trade["trade_type"],
                        "pnl": trade.get("pnl"),
                        "pnl_percentage": trade.get("pnl_percentage"),
                        "duration_days": trade.get("duration_days"),
                        "stop_loss_price": trade.get("stop_loss_price"),
                        "take_profit_price": trade.get("take_profit_price"),
                        "exit_reason": trade.get("exit_reason"),
                    }
                    for trade in trades
                ]
                crud.bulk_create_backtest_trades(self.db, result_id, trade_data)
            
            # Update result with metrics
            crud.update_backtest_result(
                self.db, result_id, {
                    **metrics,
                    "equity_curve": equity_curve,
                    "status": BacktestStatus.COMPLETED,
                    "completed_at": datetime.now(timezone.utc)
                }
            )
            
        except Exception as e:
            # Update result with error
            crud.update_backtest_result(
                self.db, result_id, {
                    "status": BacktestStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.now(timezone.utc)
                }
            )
            raise
    
    async def _fetch_historical_data(self, strategy: BacktestStrategy) -> List[Dict[str, Any]]:
        """
        Fetch historical price data for the symbol using Polygon API.
        Returns list of OHLCV bars.
        """
        # Convert timeframe to Polygon multiplier and timespan
        timeframe_map = {
            "1m": ("minute", 1),
            "5m": ("minute", 5),
            "15m": ("minute", 15),
            "1h": ("hour", 1),
            "4h": ("hour", 4),
            "1d": ("day", 1),
            "1w": ("week", 1),
        }
        
        timespan, multiplier = timeframe_map.get(strategy.timeframe.lower(), ("day", 1))
        
        # Format dates
        start_date_str = strategy.start_date.strftime("%Y-%m-%d")
        end_date_str = strategy.end_date.strftime("%Y-%m-%d")
        
        # Format symbol based on asset type
        symbol = self._format_symbol_for_polygon(strategy.symbol, strategy.asset_type.value)
        
        # Build Polygon aggregates API URL
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date_str}/{end_date_str}"
        
        try:
            # Make request (PolygonService uses async, so we need to handle it)
            response = await self.polygon_service._make_request(url, "stocks")
            
            if response.get("status") == "ERROR" or not response.get("results"):
                return []
            
            # Convert Polygon response to our format
            bars = []
            for bar in response.get("results", []):
                # Convert timestamp (ms) to datetime with timezone
                timestamp_ms = bar["t"]
                bar_date = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                
                bars.append({
                    "date": bar_date,
                    "open": bar.get("o", 0),
                    "high": bar.get("h", 0),
                    "low": bar.get("l", 0),
                    "close": bar.get("c", 0),
                    "volume": bar.get("v", 0),
                })
            
            return bars
            
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return []
    
    def _format_symbol_for_polygon(self, symbol: str, asset_type: str) -> str:
        """Format symbol for Polygon API based on asset type"""
        symbol_upper = symbol.upper()
        
        if asset_type == "stocks":
            # Stocks: just return uppercase (e.g., "AAPL")
            return symbol_upper
        elif asset_type == "crypto":
            # Crypto: Convert BTC/USD to X:BTCUSD format
            if "/" in symbol:
                base, quote = symbol_upper.split("/")
                return f"X:{base}{quote}"
            return f"X:{symbol_upper}USD"
        elif asset_type == "forex":
            # Forex: Convert EUR/USD to C:EURUSD format
            if "/" in symbol:
                base, quote = symbol_upper.split("/")
                return f"C:{base}{quote}"
            return f"C:{symbol_upper}USD"
        else:
            # Default: return as is
            return symbol_upper
    
    def _calculate_indicators(
        self, data: List[Dict[str, Any]], indicators: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Calculate technical indicators for the data.
        Supports multiple periods for same indicator type.
        """
        result = data.copy()
        
        # Track which indicators we've calculated to avoid duplicates
        calculated = set()
        
        for indicator in indicators:
            indicator_lower = indicator.lower()
            
            # Handle indicators with period specification (e.g., "sma_50", "rsi_21")
            if "_" in indicator_lower:
                parts = indicator_lower.split("_")
                indicator_name = parts[0]
                try:
                    period = int(parts[1])
                except (ValueError, IndexError):
                    period = None
            else:
                indicator_name = indicator_lower
                period = None
            
            # Skip if already calculated with same parameters
            indicator_key = f"{indicator_name}_{period}" if period else indicator_name
            if indicator_key in calculated:
                continue
            
            if indicator_name == "sma":
                period = period or 20
                result = self._calculate_sma(result, period=period)
                calculated.add(indicator_key)
            elif indicator_name == "ema":
                period = period or 20
                result = self._calculate_ema(result, period=period)
                calculated.add(indicator_key)
            elif indicator_name == "rsi":
                period = period or 14
                result = self._calculate_rsi(result, period=period)
                calculated.add(indicator_key)
            elif indicator_name == "macd":
                # MACD can have custom periods, but we'll use defaults for now
                result = self._calculate_macd(result)
                calculated.add("macd")
            elif indicator_name == "bollinger" or indicator_name == "bb":
                period = period or 20
                result = self._calculate_bollinger_bands(result, period=period)
                calculated.add(indicator_key)
            elif indicator_name == "atr":
                period = period or 14
                result = self._calculate_atr(result, period=period)
                calculated.add(indicator_key)
        
        return result
    
    def _execute_strategy(
        self, data: List[Dict[str, Any]], strategy: BacktestStrategy
    ) -> List[Dict[str, Any]]:
        """
        Execute the trading strategy on historical data.
        Parses entry/exit rules and executes trades.
        """
        trades = []
        position = None  # Current position: {"type": "long"/"short", "entry_price": float, "entry_date": datetime, "quantity": float, "stop_loss": float, "take_profit": float}
        capital = strategy.initial_capital
        available_capital = capital
        
        # Position size calculation
        position_size_pct = strategy.position_size or 100.0  # Percentage of capital per trade
        
        for i, bar in enumerate(data):
            current_price = bar["close"]
            current_date = bar["date"]
            prev_bar = data[i - 1] if i > 0 else None
            
            # Check exit conditions first (if we have a position)
            if position:
                exit_reason = None
                exit_price = None
                
                # Check stop loss (using high/low for intraday hits)
                if strategy.stop_loss:
                    stop_loss_price = position["stop_loss"]
                    high = bar["high"]
                    low = bar["low"]
                    
                    if position["type"] == "long":
                        # Long position: stop loss hit if low touches stop loss price
                        if low <= stop_loss_price:
                            exit_reason = "stop_loss"
                            exit_price = stop_loss_price
                    else:  # short
                        # Short position: stop loss hit if high touches stop loss price
                        if high >= stop_loss_price:
                            exit_reason = "stop_loss"
                            exit_price = stop_loss_price
                
                # Check take profit (using high/low for intraday hits)
                if not exit_reason and strategy.take_profit:
                    take_profit_price = position["take_profit"]
                    high = bar["high"]
                    low = bar["low"]
                    
                    if position["type"] == "long":
                        # Long position: take profit hit if high touches take profit price
                        if high >= take_profit_price:
                            exit_reason = "take_profit"
                            exit_price = take_profit_price
                    else:  # short
                        # Short position: take profit hit if low touches take profit price
                        if low <= take_profit_price:
                            exit_reason = "take_profit"
                            exit_price = take_profit_price
                
                # Check exit rules
                if not exit_reason and strategy.exit_rules:
                    if self._evaluate_condition(strategy.exit_rules, bar, position, prev_bar):
                        exit_reason = "signal"
                        exit_price = current_price
                
                # Execute exit if condition met
                if exit_reason:
                    pnl = self._calculate_pnl(position, exit_price)
                    pnl_pct = (pnl / (position["entry_price"] * position["quantity"])) * 100
                    duration = (current_date - position["entry_date"]).total_seconds() / 86400  # days
                    
                    trades.append({
                        "entry_date": position["entry_date"],
                        "exit_date": current_date,
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "quantity": position["quantity"],
                        "trade_type": position["type"],
                        "pnl": pnl,
                        "pnl_percentage": pnl_pct,
                        "duration_days": duration,
                        "stop_loss_price": position.get("stop_loss"),
                        "take_profit_price": position.get("take_profit"),
                        "exit_reason": exit_reason,
                    })
                    
                    # Update capital
                    available_capital += (position["entry_price"] * position["quantity"]) + pnl
                    position = None
            
            # Check entry conditions (if we don't have a position)
            if not position and strategy.entry_rules:
                if self._evaluate_condition(strategy.entry_rules, bar, None, prev_bar):
                    # Determine trade type (default to long)
                    trade_type = "long"  # Could be determined from rules
                    
                    # Calculate position size
                    position_value = (available_capital * position_size_pct) / 100.0
                    quantity = position_value / current_price
                    
                    # Calculate stop loss and take profit prices
                    stop_loss_price = None
                    take_profit_price = None
                    
                    if strategy.stop_loss:
                        if trade_type == "long":
                            stop_loss_price = current_price * (1 - strategy.stop_loss / 100.0)
                        else:  # short
                            stop_loss_price = current_price * (1 + strategy.stop_loss / 100.0)
                    
                    if strategy.take_profit:
                        if trade_type == "long":
                            take_profit_price = current_price * (1 + strategy.take_profit / 100.0)
                        else:  # short
                            take_profit_price = current_price * (1 - strategy.take_profit / 100.0)
                    
                    # Open position
                    position = {
                        "type": trade_type,
                        "entry_price": current_price,
                        "entry_date": current_date,
                        "quantity": quantity,
                        "stop_loss": stop_loss_price,
                        "take_profit": take_profit_price,
                    }
                    
                    # Deduct capital
                    available_capital -= position_value
        
        # Close any remaining position at the end
        if position and len(data) > 0:
            last_bar = data[-1]
            exit_price = last_bar["close"]
            exit_date = last_bar["date"]
            
            pnl = self._calculate_pnl(position, exit_price)
            pnl_pct = (pnl / (position["entry_price"] * position["quantity"])) * 100
            duration = (exit_date - position["entry_date"]).total_seconds() / 86400
            
            trades.append({
                "entry_date": position["entry_date"],
                "exit_date": exit_date,
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "quantity": position["quantity"],
                "trade_type": position["type"],
                "pnl": pnl,
                "pnl_percentage": pnl_pct,
                "duration_days": duration,
                "stop_loss_price": position.get("stop_loss"),
                "take_profit_price": position.get("take_profit"),
                "exit_reason": "end_of_period",
            })
        
        return trades
    
    def _evaluate_condition(self, condition_text: str, bar: Dict[str, Any], position: Optional[Dict] = None, prev_bar: Optional[Dict] = None) -> bool:
        """
        Evaluate a trading condition rule.
        Supports simple conditions like:
        - "RSI < 30"
        - "price > SMA(20)"
        - "MACD crosses above signal"
        - "RSI < 30 AND price > SMA(20)"
        """
        if not condition_text:
            return False
        
        condition_text = condition_text.strip().upper()
        
        # Handle AND/OR logic
        if " AND " in condition_text:
            parts = condition_text.split(" AND ")
            return all(self._evaluate_single_condition(part.strip(), bar, position, prev_bar) for part in parts)
        elif " OR " in condition_text:
            parts = condition_text.split(" OR ")
            return any(self._evaluate_single_condition(part.strip(), bar, position, prev_bar) for part in parts)
        else:
            return self._evaluate_single_condition(condition_text, bar, position, prev_bar)
    
    def _evaluate_single_condition(self, condition: str, bar: Dict[str, Any], position: Optional[Dict] = None, prev_bar: Optional[Dict] = None) -> bool:
        """Evaluate a single condition"""
        condition = condition.strip()
        
        # Price comparisons
        if "PRICE" in condition:
            price = bar["close"]
            if "PRICE >" in condition:
                # Extract value after >
                try:
                    value = float(condition.split("PRICE >")[1].strip())
                    return price > value
                except:
                    pass
            elif "PRICE <" in condition:
                try:
                    value = float(condition.split("PRICE <")[1].strip())
                    return price < value
                except:
                    pass
        
        # RSI conditions
        if "RSI" in condition:
            rsi = bar.get("rsi") or bar.get("rsi_14")
            if rsi is None:
                return False
            
            if "RSI <" in condition:
                try:
                    value = float(condition.split("RSI <")[1].strip())
                    return rsi < value
                except:
                    pass
            elif "RSI >" in condition:
                try:
                    value = float(condition.split("RSI >")[1].strip())
                    return rsi > value
                except:
                    pass
        
        # SMA conditions
        if "SMA" in condition or "SMA(" in condition:
            # Extract period from SMA(20) or use default
            period = 20
            if "SMA(" in condition:
                try:
                    period_str = condition.split("SMA(")[1].split(")")[0]
                    period = int(period_str)
                except:
                    pass
            
            sma_key = f"sma_{period}" if period != 20 else "sma"
            sma = bar.get(sma_key) or bar.get("sma")
            price = bar["close"]
            
            if sma is None:
                return False
            
            if "PRICE > SMA" in condition or f"PRICE > SMA({period})" in condition:
                return price > sma
            elif "PRICE < SMA" in condition or f"PRICE < SMA({period})" in condition:
                return price < sma
            elif "PRICE CROSSES ABOVE SMA" in condition or "CROSSES ABOVE SMA" in condition:
                # Check crossover: price was below SMA, now above
                if prev_bar:
                    prev_sma_key = f"sma_{period}" if period != 20 else "sma"
                    prev_sma = prev_bar.get(prev_sma_key) or prev_bar.get("sma")
                    prev_price = prev_bar["close"]
                    if prev_sma is not None:
                        return prev_price <= prev_sma and price > sma
                return False
            elif "PRICE CROSSES BELOW SMA" in condition or "CROSSES BELOW SMA" in condition:
                # Check crossover: price was above SMA, now below
                if prev_bar:
                    prev_sma_key = f"sma_{period}" if period != 20 else "sma"
                    prev_sma = prev_bar.get(prev_sma_key) or prev_bar.get("sma")
                    prev_price = prev_bar["close"]
                    if prev_sma is not None:
                        return prev_price >= prev_sma and price < sma
                return False
        
        # EMA conditions (similar to SMA)
        if "EMA" in condition or "EMA(" in condition:
            period = 20
            if "EMA(" in condition:
                try:
                    period_str = condition.split("EMA(")[1].split(")")[0]
                    period = int(period_str)
                except:
                    pass
            
            ema_key = f"ema_{period}" if period != 20 else "ema"
            ema = bar.get(ema_key) or bar.get("ema")
            price = bar["close"]
            
            if ema is None:
                return False
            
            if "PRICE > EMA" in condition:
                return price > ema
            elif "PRICE < EMA" in condition:
                return price < ema
            elif "PRICE CROSSES ABOVE EMA" in condition or "CROSSES ABOVE EMA" in condition:
                # Check crossover: price was below EMA, now above
                if prev_bar:
                    prev_ema_key = f"ema_{period}" if period != 20 else "ema"
                    prev_ema = prev_bar.get(prev_ema_key) or prev_bar.get("ema")
                    prev_price = prev_bar["close"]
                    if prev_ema is not None:
                        return prev_price <= prev_ema and price > ema
                return False
            elif "PRICE CROSSES BELOW EMA" in condition or "CROSSES BELOW EMA" in condition:
                # Check crossover: price was above EMA, now below
                if prev_bar:
                    prev_ema_key = f"ema_{period}" if period != 20 else "ema"
                    prev_ema = prev_bar.get(prev_ema_key) or prev_bar.get("ema")
                    prev_price = prev_bar["close"]
                    if prev_ema is not None:
                        return prev_price >= prev_ema and price < ema
                return False
        
        # MACD conditions
        if "MACD" in condition:
            macd = bar.get("macd")
            macd_signal = bar.get("macd_signal")
            
            if macd is None or macd_signal is None:
                return False
            
            if "MACD > SIGNAL" in condition:
                return macd > macd_signal
            elif "MACD < SIGNAL" in condition:
                return macd < macd_signal
            elif "MACD CROSSES ABOVE SIGNAL" in condition or "CROSSES ABOVE SIGNAL" in condition:
                # Check crossover: MACD was below signal, now above
                if prev_bar:
                    prev_macd = prev_bar.get("macd")
                    prev_signal = prev_bar.get("macd_signal")
                    if prev_macd is not None and prev_signal is not None:
                        return prev_macd <= prev_signal and macd > macd_signal
                return False
            elif "MACD CROSSES BELOW SIGNAL" in condition or "CROSSES BELOW SIGNAL" in condition:
                # Check crossover: MACD was above signal, now below
                if prev_bar:
                    prev_macd = prev_bar.get("macd")
                    prev_signal = prev_bar.get("macd_signal")
                    if prev_macd is not None and prev_signal is not None:
                        return prev_macd >= prev_signal and macd < macd_signal
                return False
        
        # Bollinger Bands conditions
        if "BOLLINGER" in condition or "BB" in condition:
            bb_upper = bar.get("bb_upper")
            bb_lower = bar.get("bb_lower")
            price = bar["close"]
            
            if bb_upper is None or bb_lower is None:
                return False
            
            if "PRICE < BB_LOWER" in condition or "PRICE < LOWER BAND" in condition:
                return price < bb_lower
            elif "PRICE > BB_UPPER" in condition or "PRICE > UPPER BAND" in condition:
                return price > bb_upper
        
        # Default: return False if condition not recognized
        return False
    
    def _calculate_pnl(self, position: Dict[str, Any], exit_price: float) -> float:
        """Calculate profit/loss for a position"""
        if position["type"] == "long":
            return (exit_price - position["entry_price"]) * position["quantity"]
        else:  # short
            return (position["entry_price"] - exit_price) * position["quantity"]
    
    def _calculate_metrics(
        self, trades: List[Dict[str, Any]], initial_capital: float
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics from trades.
        """
        if not trades:
            return {
                "total_return": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
            }
        
        # Filter completed trades
        completed_trades = [t for t in trades if t.get("exit_price") is not None]
        
        if not completed_trades:
            return {
                "total_return": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
            }
        
        # Calculate basic metrics
        total_trades = len(completed_trades)
        winning_trades = [t for t in completed_trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in completed_trades if t.get("pnl", 0) <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
        
        # Calculate PnL metrics
        total_pnl = sum(t.get("pnl", 0) for t in completed_trades)
        total_return = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0
        
        avg_win = sum(t.get("pnl", 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.get("pnl", 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        largest_win = max((t.get("pnl", 0) for t in winning_trades), default=0.0)
        largest_loss = min((t.get("pnl", 0) for t in losing_trades), default=0.0)
        
        # Profit factor
        gross_profit = sum(t.get("pnl", 0) for t in winning_trades)
        gross_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Consecutive wins/losses
        consecutive_wins = self._calculate_consecutive(completed_trades, "win")
        consecutive_losses = self._calculate_consecutive(completed_trades, "loss")
        
        # Calculate advanced metrics
        # Calculate returns for each trade
        trade_returns = [t.get("pnl_percentage", 0) / 100.0 for t in completed_trades]
        
        # Annualized return
        if completed_trades:
            first_trade_date = completed_trades[0]["entry_date"]
            last_trade_date = completed_trades[-1]["exit_date"]
            days_diff = (last_trade_date - first_trade_date).total_seconds() / 86400
            years = max(days_diff / 365.25, 1/365.25)  # At least 1 day
            annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
        else:
            annualized_return = 0.0
        
        # Volatility (standard deviation of returns)
        if len(trade_returns) > 1:
            mean_return = sum(trade_returns) / len(trade_returns)
            variance = sum((r - mean_return) ** 2 for r in trade_returns) / (len(trade_returns) - 1)
            volatility = math.sqrt(variance) * math.sqrt(252) * 100  # Annualized volatility
        else:
            volatility = 0.0
        
        # Sharpe ratio (assuming risk-free rate of 0 for simplicity)
        risk_free_rate = 0.0
        if volatility > 0:
            sharpe_ratio = (annualized_return - risk_free_rate) / (volatility / 100)
        else:
            sharpe_ratio = 0.0
        
        # Sortino ratio (downside deviation)
        if len(trade_returns) > 1:
            downside_returns = [r for r in trade_returns if r < 0]
            if downside_returns:
                downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
                downside_deviation = math.sqrt(downside_variance) * math.sqrt(252) * 100
                if downside_deviation > 0:
                    sortino_ratio = (annualized_return - risk_free_rate) / (downside_deviation / 100)
                else:
                    sortino_ratio = 0.0
            else:
                sortino_ratio = float('inf') if annualized_return > 0 else 0.0
        else:
            sortino_ratio = 0.0
        
        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(completed_trades, initial_capital)
        
        # Calmar ratio
        if abs(max_drawdown) > 0:
            calmar_ratio = annualized_return / abs(max_drawdown)
        else:
            calmar_ratio = float('inf') if annualized_return > 0 else 0.0
        
        return {
            "total_return": round(total_return, 2),
            "annualized_return": round(annualized_return, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2) if sortino_ratio != float('inf') else 999.99,
            "calmar_ratio": round(calmar_ratio, 2) if calmar_ratio != float('inf') else 999.99,
            "max_drawdown": round(max_drawdown, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "consecutive_wins": consecutive_wins,
            "consecutive_losses": consecutive_losses,
            "volatility": round(volatility, 2),
        }
    
    def _calculate_max_drawdown(self, trades: List[Dict[str, Any]], initial_capital: float) -> float:
        """Calculate maximum drawdown percentage"""
        if not trades:
            return 0.0
        
        # Calculate equity curve
        equity = initial_capital
        peak = initial_capital
        max_dd = 0.0
        
        for trade in trades:
            pnl = trade.get("pnl", 0)
            equity += pnl
            
            if equity > peak:
                peak = equity
            
            drawdown = ((equity - peak) / peak) * 100
            if drawdown < max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _generate_equity_curve(
        self, trades: List[Dict[str, Any]], initial_capital: float, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate equity curve data points.
        Tracks portfolio value over time with drawdown calculation.
        """
        if not trades or not data:
            return []
        
        equity_curve = []
        equity = initial_capital
        peak = initial_capital
        
        # Create a map of trades by date for quick lookup
        trades_by_date = {}
        for trade in trades:
            exit_date = trade.get("exit_date")
            if exit_date:
                # Use date as key (without time)
                date_key = exit_date.date() if hasattr(exit_date, 'date') else exit_date
                if date_key not in trades_by_date:
                    trades_by_date[date_key] = []
                trades_by_date[date_key].append(trade)
        
        # Track cumulative PnL
        cumulative_pnl = 0.0
        
        # Generate equity curve points
        for bar in data:
            bar_date = bar["date"]
            date_key = bar_date.date() if hasattr(bar_date, 'date') else bar_date
            
            # Check if any trades closed on this date
            if date_key in trades_by_date:
                for trade in trades_by_date[date_key]:
                    pnl = trade.get("pnl", 0)
                    cumulative_pnl += pnl
            
            # Calculate current equity
            current_equity = initial_capital + cumulative_pnl
            
            # Update peak
            if current_equity > peak:
                peak = current_equity
            
            # Calculate drawdown
            drawdown = ((current_equity - peak) / peak) * 100 if peak > 0 else 0.0
            
            equity_curve.append({
                "date": bar_date.isoformat() if hasattr(bar_date, 'isoformat') else str(bar_date),
                "value": round(current_equity, 2),
                "drawdown": round(drawdown, 2),
            })
        
        return equity_curve
    
    # Indicator calculation methods
    def _calculate_sma(self, data: List[Dict], period: int = 20) -> List[Dict]:
        """Calculate Simple Moving Average"""
        if len(data) < period:
            return data
        
        result = data.copy()
        closes = [bar["close"] for bar in data]
        
        for i in range(period - 1, len(data)):
            sma = sum(closes[i - period + 1:i + 1]) / period
            result[i]["sma"] = sma
            result[i][f"sma_{period}"] = sma
        
        return result
    
    def _calculate_ema(self, data: List[Dict], period: int = 20) -> List[Dict]:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return data
        
        result = data.copy()
        closes = [bar["close"] for bar in data]
        
        # Calculate multiplier
        multiplier = 2.0 / (period + 1)
        
        # First EMA value is SMA
        first_sma = sum(closes[:period]) / period
        result[period - 1]["ema"] = first_sma
        result[period - 1][f"ema_{period}"] = first_sma
        
        # Calculate subsequent EMA values
        for i in range(period, len(data)):
            ema = (closes[i] - result[i - 1].get("ema", first_sma)) * multiplier + result[i - 1].get("ema", first_sma)
            result[i]["ema"] = ema
            result[i][f"ema_{period}"] = ema
        
        return result
    
    def _calculate_rsi(self, data: List[Dict], period: int = 14) -> List[Dict]:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return data
        
        result = data.copy()
        closes = [bar["close"] for bar in data]
        
        # Calculate price changes
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        
        # Calculate initial average gain and loss
        gains = [change if change > 0 else 0 for change in changes[:period]]
        losses = [-change if change < 0 else 0 for change in changes[:period]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        # Calculate RSI for first period
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        result[period]["rsi"] = rsi
        result[period][f"rsi_{period}"] = rsi
        
        # Calculate subsequent RSI values using Wilder's smoothing
        for i in range(period + 1, len(data)):
            change = changes[i - 1]
            gain = change if change > 0 else 0
            loss = -change if change < 0 else 0
            
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            result[i]["rsi"] = rsi
            result[i][f"rsi_{period}"] = rsi
        
        return result
    
    def _calculate_macd(self, data: List[Dict], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> List[Dict]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(data) < slow_period + signal_period:
            return data
        
        result = data.copy()
        
        # First calculate EMAs
        result = self._calculate_ema(result, fast_period)
        result = self._calculate_ema(result, slow_period)
        
        # Calculate MACD line (fast EMA - slow EMA)
        for i in range(slow_period - 1, len(result)):
            fast_ema = result[i].get(f"ema_{fast_period}", 0)
            slow_ema = result[i].get(f"ema_{slow_period}", 0)
            macd = fast_ema - slow_ema
            result[i]["macd"] = macd
        
        # Calculate Signal line (EMA of MACD)
        macd_values = [result[i].get("macd", 0) for i in range(slow_period - 1, len(result))]
        
        # Calculate EMA of MACD for signal line
        multiplier = 2.0 / (signal_period + 1)
        first_signal = sum(macd_values[:signal_period]) / signal_period
        result[slow_period + signal_period - 2]["macd_signal"] = first_signal
        
        for i in range(slow_period + signal_period - 1, len(result)):
            macd_value = result[i].get("macd", 0)
            prev_signal = result[i - 1].get("macd_signal", first_signal)
            signal = (macd_value - prev_signal) * multiplier + prev_signal
            result[i]["macd_signal"] = signal
            result[i]["macd_histogram"] = macd_value - signal
        
        return result
    
    def _calculate_bollinger_bands(self, data: List[Dict], period: int = 20, std_dev: float = 2.0) -> List[Dict]:
        """Calculate Bollinger Bands"""
        if len(data) < period:
            return data
        
        result = data.copy()
        closes = [bar["close"] for bar in data]
        
        for i in range(period - 1, len(data)):
            # Calculate SMA
            sma = sum(closes[i - period + 1:i + 1]) / period
            
            # Calculate standard deviation
            variance = sum((closes[j] - sma) ** 2 for j in range(i - period + 1, i + 1)) / period
            std = math.sqrt(variance)
            
            # Calculate bands
            upper_band = sma + (std_dev * std)
            lower_band = sma - (std_dev * std)
            
            result[i]["bb_upper"] = upper_band
            result[i]["bb_middle"] = sma
            result[i]["bb_lower"] = lower_band
            result[i]["bb_width"] = (upper_band - lower_band) / sma * 100  # Percentage width
        
        return result
    
    def _calculate_atr(self, data: List[Dict], period: int = 14) -> List[Dict]:
        """Calculate Average True Range"""
        if len(data) < period + 1:
            return data
        
        result = data.copy()
        
        # Calculate True Range for each bar
        true_ranges = []
        for i in range(1, len(data)):
            high = data[i]["high"]
            low = data[i]["low"]
            prev_close = data[i - 1]["close"]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
            result[i]["tr"] = tr
        
        # Calculate ATR (SMA of True Range)
        for i in range(period, len(true_ranges) + 1):
            atr = sum(true_ranges[i - period:i]) / period
            result[i]["atr"] = atr
            result[i][f"atr_{period}"] = atr
        
        return result
    
    def _calculate_consecutive(self, trades: List[Dict], type: str) -> int:
        """Calculate consecutive wins or losses"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            pnl = trade.get("pnl", 0)
            is_win = pnl > 0
            
            if (type == "win" and is_win) or (type == "loss" and not is_win):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive

