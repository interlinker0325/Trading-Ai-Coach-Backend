from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from app.models.backtest import BacktestStrategy, BacktestStatus
from app.crud import backtest as crud
from app.services.polygon_service import PolygonService
import math
import json


class BacktestService:
    """Service for running backtests and calculating performance metrics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.polygon_service = PolygonService()
    
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
            print("historical data", historical_data)
            
            if not historical_data:
                raise ValueError("Failed to fetch historical data")
            
            # Calculate indicators
            data_with_indicators = self._calculate_indicators(historical_data, strategy.indicators or [])

            # Execute strategy
            # trades, final_position = self._execute_strategy(data_with_indicators, strategy)
            
            # # Calculate performance metrics
            # metrics = self._calculate_metrics(trades, strategy.initial_capital)
            
            # # Generate equity curve
            # equity_curve = self._generate_equity_curve(trades, strategy.initial_capital, data_with_indicators, final_position)
            
            # # Save trades to database
            # if trades:
            #     trade_data = [
            #         {
            #             "entry_date": trade["entry_date"],
            #             "exit_date": trade.get("exit_date"),
            #             "entry_price": trade["entry_price"],
            #             "exit_price": trade.get("exit_price"),
            #             "quantity": trade["quantity"],
            #             "trade_type": trade["trade_type"],
            #             "pnl": trade.get("pnl"),
            #             "pnl_percentage": trade.get("pnl_percentage"),
            #             "duration_days": trade.get("duration_days"),
            #             "stop_loss_price": trade.get("stop_loss_price"),
            #             "take_profit_price": trade.get("take_profit_price"),
            #             "exit_reason": trade.get("exit_reason"),
            #         }
            #         for trade in trades
            #     ]
            #     crud.bulk_create_backtest_trades(self.db, result_id, trade_data)
            
            # # Update result with metrics
            # crud.update_backtest_result(
            #     self.db, result_id, {
            #         **metrics,
            #         "equity_curve": equity_curve,
            #         "status": BacktestStatus.COMPLETED,
            #         "completed_at": datetime.now(timezone.utc)
            #     }
            # )
            
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
        # Extract all needed values from strategy object immediately
        # to avoid DetachedInstanceError when accessing attributes
        timeframe = str(strategy.timeframe).lower()
        start_date = strategy.start_date
        end_date = strategy.end_date
        symbol_str = str(strategy.symbol)
        
        # Handle asset_type enum - get the value directly
        asset_type_value = str(strategy.asset_type.value) if hasattr(strategy.asset_type, 'value') else str(strategy.asset_type)
        
        multiplier = 1
        timespan = timeframe
        
        # Format dates
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Format symbol based on asset type
        symbol = self._format_symbol_for_polygon(symbol_str, asset_type_value)
        
        # Build Polygon aggregates API URL
        url = f"https://api.massive.com/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date_str}/{end_date_str}?adjusted=true&sort=asc&limit=50000"
        
        try:
            # Make request (PolygonService uses async, so we need to handle it)
            # Use asset type to determine API type (stocks, crypto, forex, options)
            api_type = asset_type_value
            response = await self.polygon_service._make_request(url, api_type)
            
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
        
        if asset_type == "crypto":
            # Crypto: Convert to X:BTCUSD format
            return f"X:{symbol_upper}"
        elif asset_type == "forex":
            # Forex: Convert to C:EURUSD format
            return f"C:{symbol_upper}"
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
            print("indicator", indicator)
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
            elif indicator_name == "stochastic":
                period = period or 14
                k_period = period
                d_period = 3  # Default smoothing period
                result = self._calculate_stochastic(result, k_period=k_period, d_period=d_period)
                calculated.add(indicator_key)
            elif indicator_name == "williams" or indicator_name == "williamsr":
                period = period or 14
                result = self._calculate_williams_r(result, period=period)
                calculated.add(indicator_key)
            elif indicator_name == "cci":
                period = period or 20
                result = self._calculate_cci(result, period=period)
                calculated.add(indicator_key)
            elif indicator_name == "adx":
                period = period or 14
                result = self._calculate_adx(result, period=period)
                calculated.add(indicator_key)
        
        return result
    
    def _execute_strategy(
        self, data: List[Dict[str, Any]], strategy: BacktestStrategy
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
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
                    if self._evaluate_rules(strategy.exit_rules, bar, position, prev_bar):
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
                    
                    # Update capital - add back exit value (exit_price * quantity)
                    available_capital += exit_price * position["quantity"]
                    position = None
            
            # Check entry conditions (if we don't have a position)
            if not position and strategy.entry_rules:
                if self._evaluate_rules(strategy.entry_rules, bar, None, prev_bar):
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
            # Update capital for final position closure
            available_capital += exit_price * position["quantity"]
            position = None
        
        return trades, position
    
    def _evaluate_rules(self, rules_json: str, bar: Dict[str, Any], position: Optional[Dict] = None, prev_bar: Optional[Dict] = None) -> bool:
        """
        Evaluate structured trading rules from JSON.
        Rules format: [{"indicator": "rsi", "operator": "<", "value": "30", "logic": "AND"}, ...]
        """
        if not rules_json:
            return False
        
        try:
            rules = json.loads(rules_json) if isinstance(rules_json, str) else rules_json
            if not isinstance(rules, list) or len(rules) == 0:
                return False
            
            # Evaluate first rule
            result = self._evaluate_single_structured_rule(rules[0], bar, position, prev_bar)
            
            # Evaluate remaining rules with their logic operators
            for i in range(1, len(rules)):
                rule = rules[i]
                rule_result = self._evaluate_single_structured_rule(rule, bar, position, prev_bar)
                logic = rule.get("logic", "AND").upper()
                
                if logic == "AND":
                    result = result and rule_result
                elif logic == "OR":
                    result = result or rule_result
                else:
                    # Default to AND if unknown logic
                    result = result and rule_result
            
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error evaluating rules: {e}")
            return False
    
    def _evaluate_single_structured_rule(self, rule: Dict[str, Any], bar: Dict[str, Any], position: Optional[Dict] = None, prev_bar: Optional[Dict] = None) -> bool:
        """Evaluate a single structured rule"""
        indicator = rule.get("indicator", "").lower()
        operator = rule.get("operator", "")
        value = rule.get("value", "")
        
        if not indicator or not operator:
            return False
        
        # Get indicator value from bar
        indicator_value = self._get_indicator_value(indicator, bar)
        if indicator_value is None:
            return False
        
        # Handle crossover operators
        if operator == "crosses_above":
            if prev_bar:
                # Special handling for MACD crossovers (MACD crosses above signal)
                if indicator == "macd" and value.lower() == "signal":
                    prev_macd = self._get_indicator_value("macd", prev_bar)
                    prev_signal = self._get_indicator_value("macd_signal", prev_bar)
                    curr_signal = self._get_indicator_value("macd_signal", bar)
                    if prev_macd is not None and prev_signal is not None and curr_signal is not None:
                        return prev_macd <= prev_signal and indicator_value > curr_signal
                else:
                    # Price/indicator crosses above another indicator
                    prev_indicator_value = self._get_indicator_value(indicator, prev_bar)
                    prev_compare_value = self._get_indicator_value(value.lower(), prev_bar) if value else None
                    curr_compare_value = self._get_indicator_value(value.lower(), bar) if value else None
                    if prev_indicator_value is not None and prev_compare_value is not None and curr_compare_value is not None:
                        return prev_indicator_value <= prev_compare_value and indicator_value > curr_compare_value
            return False
        elif operator == "crosses_below":
            if prev_bar:
                # Special handling for MACD crossovers (MACD crosses below signal)
                if indicator == "macd" and value.lower() == "signal":
                    prev_macd = self._get_indicator_value("macd", prev_bar)
                    prev_signal = self._get_indicator_value("macd_signal", prev_bar)
                    curr_signal = self._get_indicator_value("macd_signal", bar)
                    if prev_macd is not None and prev_signal is not None and curr_signal is not None:
                        return prev_macd >= prev_signal and indicator_value < curr_signal
                else:
                    # Price/indicator crosses below another indicator
                    prev_indicator_value = self._get_indicator_value(indicator, prev_bar)
                    prev_compare_value = self._get_indicator_value(value.lower(), prev_bar) if value else None
                    curr_compare_value = self._get_indicator_value(value.lower(), bar) if value else None
                    if prev_indicator_value is not None and prev_compare_value is not None and curr_compare_value is not None:
                        return prev_indicator_value >= prev_compare_value and indicator_value < curr_compare_value
            return False
        
        # Handle comparison operators
        # Check if value is an indicator name (not a number)
        compare_indicator_value = self._get_indicator_value(value.lower(), bar) if value else None
        
        if compare_indicator_value is not None:
            # Indicator-to-indicator comparison
            if operator == ">":
                return indicator_value > compare_indicator_value
            elif operator == "<":
                return indicator_value < compare_indicator_value
            elif operator == ">=":
                return indicator_value >= compare_indicator_value
            elif operator == "<=":
                return indicator_value <= compare_indicator_value
            elif operator == "==":
                return abs(indicator_value - compare_indicator_value) < 0.0001  # Float comparison
        else:
            # Indicator-to-numeric comparison
            try:
                compare_value = float(value)
            except (ValueError, TypeError):
                return False
            
            if operator == ">":
                return indicator_value > compare_value
            elif operator == "<":
                return indicator_value < compare_value
            elif operator == ">=":
                return indicator_value >= compare_value
            elif operator == "<=":
                return indicator_value <= compare_value
            elif operator == "==":
                return abs(indicator_value - compare_value) < 0.0001  # Float comparison
        
        return False
    
    def _get_indicator_value(self, indicator: str, bar: Dict[str, Any]) -> Optional[float]:
        """Get the indicator value from bar data"""
        indicator_lower = indicator.lower()
        
        # RSI
        if indicator_lower == "rsi":
            return bar.get("rsi") or bar.get("rsi_14")
        
        # SMA
        if indicator_lower == "sma":
            return bar.get("sma") or bar.get("sma_20")
        
        # EMA
        if indicator_lower == "ema":
            return bar.get("ema") or bar.get("ema_20")
        
        # MACD
        if indicator_lower == "macd":
            return bar.get("macd")
        
        # MACD Signal
        if indicator_lower == "macd_signal":
            return bar.get("macd_signal")
        
        # Bollinger Bands
        if indicator_lower == "bb_upper":
            return bar.get("bb_upper")
        if indicator_lower == "bb_lower":
            return bar.get("bb_lower")
        if indicator_lower == "bb_middle":
            return bar.get("bb_middle")
        
        # ATR
        if indicator_lower == "atr":
            return bar.get("atr") or bar.get("atr_14")
        
        # Stochastic
        if indicator_lower == "stochastic" or indicator_lower == "stochastic_k":
            return bar.get("stochastic_k") or bar.get("stochastic_k_14")
        if indicator_lower == "stochastic_d":
            return bar.get("stochastic_d") or bar.get("stochastic_d_3")
        
        # Williams %R
        if indicator_lower == "williams" or indicator_lower == "williamsr":
            return bar.get("williams_r") or bar.get("williams_r_14")
        
        # CCI
        if indicator_lower == "cci":
            return bar.get("cci") or bar.get("cci_20")
        
        # ADX
        if indicator_lower == "adx":
            return bar.get("adx") or bar.get("adx_14")
        
        # Price
        if indicator_lower == "price":
            return bar.get("close")
        
        return None
    
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
        self, trades: List[Dict[str, Any]], initial_capital: float, data: List[Dict[str, Any]], final_position: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate equity curve data points.
        Tracks portfolio value over time with drawdown calculation.
        Accounts for open positions by including their current value.
        """
        if not data:
            return []
        
        equity_curve = []
        peak = initial_capital
        
        # Create maps for trades by entry and exit dates
        trades_by_exit_date = {}
        trades_by_entry_date = {}
        for trade in trades:
            entry_date = trade.get("entry_date")
            exit_date = trade.get("exit_date")
            if entry_date:
                entry_key = entry_date.date() if hasattr(entry_date, 'date') else entry_date
                if entry_key not in trades_by_entry_date:
                    trades_by_entry_date[entry_key] = []
                trades_by_entry_date[entry_key].append(trade)
            if exit_date:
                exit_key = exit_date.date() if hasattr(exit_date, 'date') else exit_date
                if exit_key not in trades_by_exit_date:
                    trades_by_exit_date[exit_key] = []
                trades_by_exit_date[exit_key].append(trade)
        
        # Track current open positions and cumulative PnL
        open_positions = {}  # {entry_date_key: trade}
        cumulative_pnl = 0.0
        
        # Generate equity curve points
        for i, bar in enumerate(data):
            bar_date = bar["date"]
            date_key = bar_date.date() if hasattr(bar_date, 'date') else bar_date
            current_price = bar["close"]
            
            # Check if any trades closed on this date
            if date_key in trades_by_exit_date:
                for trade in trades_by_exit_date[date_key]:
                    pnl = trade.get("pnl", 0)
                    cumulative_pnl += pnl
                    # Remove from open positions
                    entry_key = trade.get("entry_date")
                    if entry_key:
                        entry_key = entry_key.date() if hasattr(entry_key, 'date') else entry_key
                        if entry_key in open_positions:
                            del open_positions[entry_key]
            
            # Check if any trades opened on this date
            if date_key in trades_by_entry_date:
                for trade in trades_by_entry_date[date_key]:
                    entry_key = trade.get("entry_date")
                    if entry_key:
                        entry_key = entry_key.date() if hasattr(entry_key, 'date') else entry_key
                        open_positions[entry_key] = trade
            
            # Calculate current equity = initial capital + cumulative PnL + unrealized PnL from open positions
            unrealized_pnl = 0.0
            for trade in open_positions.values():
                entry_price = trade.get("entry_price", 0)
                quantity = trade.get("quantity", 0)
                trade_type = trade.get("trade_type", "long")
                if trade_type == "long":
                    unrealized_pnl += (current_price - entry_price) * quantity
                else:  # short
                    unrealized_pnl += (entry_price - current_price) * quantity
            
            # Also account for final position if it exists and hasn't been closed
            if final_position and i == len(data) - 1:
                entry_price = final_position.get("entry_price", 0)
                quantity = final_position.get("quantity", 0)
                trade_type = final_position.get("type", "long")
                if trade_type == "long":
                    unrealized_pnl += (current_price - entry_price) * quantity
                else:  # short
                    unrealized_pnl += (entry_price - current_price) * quantity
            
            current_equity = initial_capital + cumulative_pnl + unrealized_pnl
            
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
    
    def _calculate_stochastic(self, data: List[Dict], k_period: int = 14, d_period: int = 3) -> List[Dict]:
        """Calculate Stochastic Oscillator (%K and %D)"""
        if len(data) < k_period + d_period:
            return data
        
        result = data.copy()
        
        for i in range(k_period - 1, len(data)):
            # Get the period's high and low
            period_data = data[i - k_period + 1:i + 1]
            highest_high = max(bar["high"] for bar in period_data)
            lowest_low = min(bar["low"] for bar in period_data)
            current_close = data[i]["close"]
            
            if highest_high == lowest_low:
                k_value = 50.0  # Neutral value when no range
            else:
                k_value = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
            
            result[i]["stochastic_k"] = k_value
            result[i][f"stochastic_k_{k_period}"] = k_value
            
            # Calculate %D (smoothed %K) if we have enough data
            if i >= k_period + d_period - 2:
                k_values = [result[j].get("stochastic_k", 50.0) for j in range(i - d_period + 1, i + 1)]
                d_value = sum(k_values) / d_period
                result[i]["stochastic_d"] = d_value
                result[i][f"stochastic_d_{d_period}"] = d_value
        
        return result
    
    def _calculate_williams_r(self, data: List[Dict], period: int = 14) -> List[Dict]:
        """Calculate Williams %R"""
        if len(data) < period:
            return data
        
        result = data.copy()
        
        for i in range(period - 1, len(data)):
            # Get the period's high and low
            period_data = data[i - period + 1:i + 1]
            highest_high = max(bar["high"] for bar in period_data)
            lowest_low = min(bar["low"] for bar in period_data)
            current_close = data[i]["close"]
            
            if highest_high == lowest_low:
                williams_r = -50.0  # Neutral value when no range
            else:
                williams_r = ((highest_high - current_close) / (highest_high - lowest_low)) * -100
            
            result[i]["williams_r"] = williams_r
            result[i][f"williams_r_{period}"] = williams_r
        
        return result
    
    def _calculate_cci(self, data: List[Dict], period: int = 20) -> List[Dict]:
        """Calculate Commodity Channel Index (CCI)"""
        if len(data) < period:
            return data
        
        result = data.copy()
        
        # Calculate Typical Price (TP) = (High + Low + Close) / 3
        for i in range(len(data)):
            tp = (data[i]["high"] + data[i]["low"] + data[i]["close"]) / 3.0
            result[i]["typical_price"] = tp
        
        # Calculate CCI
        for i in range(period - 1, len(data)):
            # Get SMA of TP
            tp_values = [result[j]["typical_price"] for j in range(i - period + 1, i + 1)]
            sma_tp = sum(tp_values) / period
            
            # Calculate Mean Deviation
            mean_deviation = sum(abs(tp - sma_tp) for tp in tp_values) / period
            
            # Calculate CCI
            current_tp = result[i]["typical_price"]
            if mean_deviation == 0:
                cci = 0.0
            else:
                cci = (current_tp - sma_tp) / (0.015 * mean_deviation)
            
            result[i]["cci"] = cci
            result[i][f"cci_{period}"] = cci
        
        return result
    
    def _calculate_adx(self, data: List[Dict], period: int = 14) -> List[Dict]:
        """Calculate Average Directional Index (ADX)"""
        if len(data) < period + 1:
            return data
        
        result = data.copy()
        
        # Calculate True Range (TR) and Directional Movement (+DM and -DM)
        for i in range(1, len(data)):
            # True Range
            tr1 = data[i]["high"] - data[i]["low"]
            tr2 = abs(data[i]["high"] - data[i - 1]["close"])
            tr3 = abs(data[i]["low"] - data[i - 1]["close"])
            tr = max(tr1, tr2, tr3)
            result[i]["tr"] = tr
            
            # Directional Movement
            up_move = data[i]["high"] - data[i - 1]["high"]
            down_move = data[i - 1]["low"] - data[i]["low"]
            
            if up_move > down_move and up_move > 0:
                plus_dm = up_move
                minus_dm = 0.0
            elif down_move > up_move and down_move > 0:
                plus_dm = 0.0
                minus_dm = down_move
            else:
                plus_dm = 0.0
                minus_dm = 0.0
            
            result[i]["plus_dm"] = plus_dm
            result[i]["minus_dm"] = minus_dm
        
        # Calculate smoothed TR, +DM, -DM (using Wilder's smoothing)
        # First period: simple average
        if len(data) >= period + 1:
            tr_sum = sum(result[i]["tr"] for i in range(1, period + 1))
            plus_dm_sum = sum(result[i]["plus_dm"] for i in range(1, period + 1))
            minus_dm_sum = sum(result[i]["minus_dm"] for i in range(1, period + 1))
            
            result[period]["atr_adx"] = tr_sum / period
            result[period]["plus_di"] = (plus_dm_sum / tr_sum * 100) if tr_sum > 0 else 0.0
            result[period]["minus_di"] = (minus_dm_sum / tr_sum * 100) if tr_sum > 0 else 0.0
            
            # Calculate DX and ADX
            di_sum = result[period]["plus_di"] + result[period]["minus_di"]
            if di_sum > 0:
                dx = abs(result[period]["plus_di"] - result[period]["minus_di"]) / di_sum * 100
            else:
                dx = 0.0
            
            result[period]["dx"] = dx
            result[period]["adx"] = dx  # First ADX value is DX
        
        # Subsequent periods: Wilder's smoothing
        for i in range(period + 1, len(data)):
            # Smooth TR, +DM, -DM
            prev_atr = result[i - 1].get("atr_adx", result[period]["atr_adx"])
            result[i]["atr_adx"] = (prev_atr * (period - 1) + result[i]["tr"]) / period
            
            prev_plus_dm_sum = result[i - 1].get("plus_dm_sum", plus_dm_sum)
            prev_minus_dm_sum = result[i - 1].get("minus_dm_sum", minus_dm_sum)
            plus_dm_sum = (prev_plus_dm_sum * (period - 1) + result[i]["plus_dm"]) / period
            minus_dm_sum = (prev_minus_dm_sum * (period - 1) + result[i]["minus_dm"]) / period
            
            result[i]["plus_dm_sum"] = plus_dm_sum
            result[i]["minus_dm_sum"] = minus_dm_sum
            
            # Calculate +DI and -DI
            if result[i]["atr_adx"] > 0:
                result[i]["plus_di"] = (plus_dm_sum / result[i]["atr_adx"] * 100)
                result[i]["minus_di"] = (minus_dm_sum / result[i]["atr_adx"] * 100)
            else:
                result[i]["plus_di"] = 0.0
                result[i]["minus_di"] = 0.0
            
            # Calculate DX
            di_sum = result[i]["plus_di"] + result[i]["minus_di"]
            if di_sum > 0:
                dx = abs(result[i]["plus_di"] - result[i]["minus_di"]) / di_sum * 100
            else:
                dx = 0.0
            
            result[i]["dx"] = dx
            
            # Calculate ADX (smoothed DX)
            prev_adx = result[i - 1].get("adx", dx)
            result[i]["adx"] = (prev_adx * (period - 1) + dx) / period
            result[i][f"adx_{period}"] = result[i]["adx"]
        
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

