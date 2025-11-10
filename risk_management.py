import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from database import get_trade_db, update_trade_status_db, set_trade_noActive_db, update_trade_amount_db

logger = logging.getLogger(__name__)

class AdvancedRiskManager:
    def __init__(self):
        # PROFESSIONELLE Take Profit Level Konfiguration
        self.take_profit_levels = {
            'TK1': {'close_percentage': 0.5, 'move_sl_to_entry': True, 'description': 'First Profit Take'},
            'TK2': {'close_percentage': 0.3, 'move_sl_to_tk1': True, 'description': 'Second Profit Take'},
            'TK3': {'close_percentage': 0.2, 'move_sl_to_tk2': True, 'description': 'Third Profit Take'}
        }
        
        # ERWEITERTE Risk Parameter mit dynamischen Anpassungen
        self.risk_parameters = {
            'max_drawdown_per_trade': 0.02,           # 2% max loss per trade
            'trailing_stop_activation': 0.05,         # 5% profit activates trailing stop
            'trailing_stop_distance': 0.02,           # 2% trailing distance
            'breakeven_activation': 0.03,             # 3% profit activates breakeven
            'volatility_multiplier': 1.5,             # Multiplier for volatile markets
            'max_trade_duration_hours': 168,          # 7 days maximum trade duration
            'partial_profit_activation': 0.10,        # 10% profit for partial profit taking
            'emergency_stop_activation': 0.15,        # 15% loss triggers emergency stop
        }
        
        # UM FASSENDE Performance Tracking
        self.performance_metrics = {
            'trades_evaluated': 0,
            'stop_loss_triggers': 0,
            'take_profit_triggers': 0,
            'trailing_stop_activations': 0,
            'breakeven_activations': 0,
            'partial_profit_taken': 0,
            'emergency_stops': 0,
            'time_based_exits': 0,
            'total_pnl': 0.0,
            'successful_trades': 0,
            'failed_trades': 0
        }
        
        # Dynamische Trade-Historie für erweiterte Analyse
        self.trade_history = {}
        self.volatility_cache = {}
        self.market_conditions = {}
        
        # Risk Management State
        self.breakeven_activated = set()
        self.trailing_stop_activated = set()
        self.partial_profit_taken = set()

    def evaluate_trade(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Evaluierte einen Trade mit PROFESSIONELLEM Risk Management"""
        try:
            self.performance_metrics['trades_evaluated'] += 1
            
            # Hole Trade-Daten mit robustem Error Handling
            trade_data = get_trade_db(symbol)
            if not trade_data:
                logger.warning(f"⚠️ No trade data found for {symbol}")
                return self._create_result('none', 'no_trade_found')
            
            # ROBUSTE Dictionary-Zugriffe mit Fallbacks
            entry_price = trade_data.get('entry_price', 0)
            position = trade_data.get('position', 'LONG').lower()
            amount = trade_data.get('quantity', 0)
            stop_loss = trade_data.get('stop_loss', 0)
            tk1 = trade_data.get('take_profit_1', 0)
            tk2 = trade_data.get('take_profit_2', 0)
            tk3 = trade_data.get('take_profit_3', 0)
            tk4 = trade_data.get('take_profit_4', 0)
            status = trade_data.get('status', 'NEW')
            leverage = trade_data.get('leverage', 1)
            created_at = trade_data.get('created_at', datetime.now())
            
            # Validiere kritische Daten
            if entry_price <= 0:
                logger.error(f"❌ Invalid entry price for {symbol}: {entry_price}")
                return self._create_result('none', 'invalid_trade_data')
            
            # Berechne aktuelle Performance
            current_pnl, pnl_percentage = self._calculate_pnl(
                entry_price, current_price, amount, position, leverage
            )
            
            # Erstelle umfassendes Result-Objekt
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'entry_price': entry_price,
                'position': position,
                'status': status,
                'current_pnl': current_pnl,
                'pnl_percentage': pnl_percentage,
                'leverage': leverage,
                'trade_duration': self._calculate_trade_duration(created_at),
                'risk_reward_ratio': self._calculate_risk_reward_ratio(entry_price, stop_loss, tk1, position),
                'volatility_level': self._calculate_volatility(symbol),
                'action': 'hold',
                'reason': '',
                'recommendations': [],
                'confidence_score': self._calculate_confidence_score(current_pnl, pnl_percentage),
                'timestamp': datetime.now().isoformat()
            }
            
            # Führe PROFESSIONELLE Risk Management Checks durch
            checks = [
                self._check_emergency_stop,
                self._check_stop_loss,
                self._check_take_profits,
                self._check_trailing_stop,
                self._check_breakeven,
                self._check_partial_profit,
                self._check_time_based_exit,
                self._check_volatility_adjustment
            ]
            
            for check in checks:
                try:
                    check_result = check(result, trade_data)
                    if check_result and check_result.get('action') != 'hold':
                        self._update_performance_metrics(check_result['action'], check_result['reason'])
                        return {**result, **check_result}
                except Exception as check_error:
                    logger.error(f"❌ Error in {check.__name__} for {symbol}: {check_error}")
                    continue
            
            # Generiere proaktive Empfehlungen
            result['recommendations'] = self._generate_recommendations(result, trade_data)
            
            # Logge Trade-Status bei signifikanten Ereignissen
            self._log_trade_status(result)
            
            return result
                
        except Exception as e:
            logger.error(f"❌ Critical error evaluating trade {symbol}: {e}")
            return self._create_result('none', f'evaluation_error: {str(e)}')

    def _calculate_pnl(self, entry_price: float, current_price: float, 
                      amount: float, position: str, leverage: float) -> Tuple[float, float]:
        """Berechnet PnL mit Leverage-Berücksichtigung und Rounding"""
        try:
            if position == 'long':
                pnl = (current_price - entry_price) * amount
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100 * leverage
            else:
                pnl = (entry_price - current_price) * amount
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100 * leverage
            
            # Runde für bessere Lesbarkeit
            return round(pnl, 2), round(pnl_percentage, 2)
        except Exception as e:
            logger.error(f"❌ Error calculating PnL: {e}")
            return 0.0, 0.0

    def _calculate_trade_duration(self, created_at) -> int:
        """Berechnet Trade-Dauer in Stunden"""
        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            duration = datetime.now() - created_at
            return int(duration.total_seconds() / 3600)  # Stunden
        except:
            return 0

    def _calculate_risk_reward_ratio(self, entry: float, stop_loss: float, take_profit: float, position: str) -> float:
        """Berechnet Risk/Reward Ratio"""
        try:
            if position == 'long':
                risk = entry - stop_loss
                reward = take_profit - entry
            else:
                risk = stop_loss - entry
                reward = entry - take_profit
            
            if risk > 0:
                return round(reward / risk, 2)
            return 1.0
        except:
            return 1.0

    def _calculate_confidence_score(self, pnl: float, pnl_percentage: float) -> float:
        """Berechnet Confidence Score basierend auf Performance"""
        try:
            base_score = 50.0  # Neutral starting point
            
            # PnL-basierte Anpassung
            if pnl > 0:
                base_score += min(pnl_percentage * 2, 30)  # Max +30 für Profit
            else:
                base_score -= min(abs(pnl_percentage), 20)  # Max -20 für Loss
            
            return max(10.0, min(100.0, base_score))  # Clamp between 10-100
        except:
            return 50.0

    def _check_emergency_stop(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Notfall-Stop bei extremen Verlusten"""
        try:
            pnl_percentage = result['pnl_percentage']
            
            if pnl_percentage <= -self.risk_parameters['emergency_stop_activation'] * 100:
                logger.warning(f"🚨 EMERGENCY STOP triggered for {result['symbol']}: {pnl_percentage:.2f}%")
                return self._create_result('close', 'emergency_stop_triggered')
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in emergency stop check: {e}")
            return None

    def _check_stop_loss(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Überprüft Stop Loss mit Volatilitäts-Puffer und Slippage-Berücksichtigung"""
        try:
            position = result['position']
            current_price = result['current_price']
            stop_loss = trade_data.get('stop_loss', 0)
            entry_price = result['entry_price']
            
            if stop_loss <= 0:
                return None
            
            # Berechne dynamischen Volatilitäts-Puffer
            volatility_buffer = self._get_volatility_buffer(result['symbol'], entry_price)
            
            # Füge Slippage-Buffer hinzu
            slippage_buffer = 0.001  # 0.1% Slippage Protection
            
            total_buffer = volatility_buffer + slippage_buffer
            
            if position == 'long':
                # Für Long: Preis fällt unter Stop Loss mit Buffer
                if current_price <= stop_loss * (1 - total_buffer):
                    logger.info(f"🛑 Stop Loss triggered for {result['symbol']} at {current_price:.2f}")
                    return self._create_result('close', 'stop_loss_triggered')
            else:
                # Für Short: Preis steigt über Stop Loss mit Buffer
                if current_price >= stop_loss * (1 + total_buffer):
                    logger.info(f"🛑 Stop Loss triggered for {result['symbol']} at {current_price:.2f}")
                    return self._create_result('close', 'stop_loss_triggered')
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in stop loss check: {e}")
            return None

    def _check_take_profits(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Überprüft Take Profit Levels mit ROBUSTEM Error Handling"""
        try:
            position = result['position']
            current_price = result['current_price']
            status = result['status']
            
            # Hole Targets mit Fallbacks
            targets = [
                trade_data.get('take_profit_1', 0),
                trade_data.get('take_profit_2', 0), 
                trade_data.get('take_profit_3', 0),
                trade_data.get('take_profit_4', 0)
            ]
            
            # Filtere ungültige Targets
            valid_targets = [t for t in targets if t and t > 0]
            
            if not valid_targets:
                return None
            
            # Definiere Take Profit Konfiguration
            tp_configs = {
                'NEW': {'target_index': 0, 'action': 'tk1', 'description': 'First Target'},
                'FILLED': {'target_index': 0, 'action': 'tk1', 'description': 'First Target'},
                'TK1': {'target_index': 1, 'action': 'tk2', 'description': 'Second Target'},
                'TK2': {'target_index': 2, 'action': 'tk3', 'description': 'Third Target'},
                'TK3': {'target_index': 3, 'action': 'close_tp4', 'description': 'Final Target'}
            }
            
            if status in tp_configs:
                config = tp_configs[status]
                target_index = config['target_index']
                
                # Prüfe ob Target Index gültig ist
                if target_index < len(valid_targets):
                    target_price = valid_targets[target_index]
                    
                    # Überprüfe ob Target erreicht wurde
                    condition_met = (
                        (position == 'long' and current_price >= target_price) or
                        (position == 'short' and current_price <= target_price)
                    )
                    
                    if condition_met:
                        if config['action'] == 'close_tp4':
                            logger.info(f"🎯 Final Target reached for {result['symbol']} at {current_price:.2f}")
                            return self._create_result('close', 'target_4_reached')
                        else:
                            tp_settings = self.take_profit_levels.get(config['action'].upper(), 
                                                                    {'close_percentage': 0.5, 'move_sl_to_entry': True})
                            logger.info(f"🎯 {config['description']} reached for {result['symbol']}")
                            return {
                                'action': 'partial_close',
                                'reason': f'{config["action"]}_reached',
                                'close_percentage': tp_settings['close_percentage'],
                                'new_status': config['action'].upper(),
                                'move_stoploss': tp_settings.get('move_sl_to_entry', False),
                                'description': config['description']
                            }
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in take profit check for {result.get('symbol', 'unknown')}: {e}")
            return None

    def _check_trailing_stop(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Überprüft und aktualisiert Trailing Stop mit dynamischer Distanz"""
        try:
            symbol = result['symbol']
            current_price = result['current_price']
            position = result['position']
            pnl_percentage = result['pnl_percentage']
            
            # Aktiviere Trailing Stop nur bei ausreichendem Profit
            if abs(pnl_percentage) < self.risk_parameters['trailing_stop_activation'] * 100:
                return None
            
            # Dynamische Trailing Stop Distanz basierend auf Volatilität
            volatility = self._calculate_volatility(symbol)
            dynamic_distance = max(
                self.risk_parameters['trailing_stop_distance'],
                volatility * 0.8  # 80% der Volatilität als Mindestabstand
            )
            
            current_sl = trade_data.get('stop_loss', 0)
            
            # Initialisiere Trade-Historie
            if symbol not in self.trade_history:
                self.trade_history[symbol] = []
            
            # Füge aktuellen Preis zur Historie hinzu
            self.trade_history[symbol].append({
                'timestamp': datetime.now(),
                'price': current_price,
                'stop_loss': current_sl
            })
            
            # Behalte nur die letzten 100 Einträge für Performance
            if len(self.trade_history[symbol]) > 100:
                self.trade_history[symbol] = self.trade_history[symbol][-100:]
            
            # Berechne optimalen Trailing Stop
            new_stop_loss = self._calculate_trailing_stop(
                symbol, current_price, result['entry_price'], position, current_sl, dynamic_distance
            )
            
            if new_stop_loss != current_sl:
                logger.info(f"🔄 Trailing stop updated for {symbol}: {current_sl:.2f} → {new_stop_loss:.2f}")
                self.trailing_stop_activated.add(symbol)
                self.performance_metrics['trailing_stop_activations'] += 1
                return self._create_result('update_stoploss', 'trailing_stop_updated')
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in trailing stop check: {e}")
            return None

    def _calculate_trailing_stop(self, symbol: str, current_price: float, 
                               entry_price: float, position: str, current_sl: float, distance: float) -> float:
        """Berechnet neuen Trailing Stop Preis mit dynamischer Logik"""
        try:
            if position == 'long':
                new_sl = current_price * (1 - distance)
                # Stop Loss nur nach oben anpassen, niemals nach unten
                return max(new_sl, current_sl, entry_price * 0.99)  # Mindestens 1% unter Entry
            else:
                new_sl = current_price * (1 + distance)
                # Stop Loss nur nach unten anpassen, niemals nach oben
                return min(new_sl, current_sl, entry_price * 1.01)  # Mindestens 1% über Entry
        except Exception as e:
            logger.error(f"❌ Error calculating trailing stop: {e}")
            return current_sl

    def _check_breakeven(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Aktiviert Breakeven Stop Loss mit Progressivem Approach"""
        try:
            symbol = result['symbol']
            position = result['position']
            current_price = result['current_price']
            entry_price = result['entry_price']
            pnl_percentage = result['pnl_percentage']
            current_sl = trade_data.get('stop_loss', 0)
            
            # Prüfe ob Breakeven bereits aktiviert wurde
            if symbol in self.breakeven_activated:
                return None
            
            # Aktiviere Breakeven bei ausreichendem Profit
            if abs(pnl_percentage) >= self.risk_parameters['breakeven_activation'] * 100:
                if position == 'long':
                    new_sl = entry_price * 1.001  # Leicht über Entry für Puffer
                else:
                    new_sl = entry_price * 0.999  # Leicht unter Entry für Puffer
                
                if ((position == 'long' and new_sl > current_sl) or 
                    (position == 'short' and new_sl < current_sl)):
                    
                    self.breakeven_activated.add(symbol)
                    self.performance_metrics['breakeven_activations'] += 1
                    logger.info(f"⚖️ Breakeven activated for {symbol} at {new_sl:.2f}")
                    return self._create_result('update_stoploss', 'breakeven_activated')
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in breakeven check: {e}")
            return None

    def _check_partial_profit(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Proaktive Teilgewinn-Mitnahme bei hohem Profit"""
        try:
            symbol = result['symbol']
            pnl_percentage = result['pnl_percentage']
            
            # Vermeide mehrfache Teilgewinn-Mitnahme
            if symbol in self.partial_profit_taken:
                return None
            
            # Aktiviere Teilgewinn-Mitnahme bei sehr hohem Profit
            if pnl_percentage >= self.risk_parameters['partial_profit_activation'] * 100:
                self.partial_profit_taken.add(symbol)
                self.performance_metrics['partial_profit_taken'] += 1
                logger.info(f"💰 Partial profit taken for {symbol} at {pnl_percentage:.2f}%")
                return {
                    'action': 'partial_close',
                    'reason': 'partial_profit_taken',
                    'close_percentage': 0.25,  # 25% der Position
                    'new_status': result['status'],  # Status bleibt gleich
                    'description': 'Proactive partial profit taking'
                }
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in partial profit check: {e}")
            return None

    def _check_time_based_exit(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Time-based Exit nach maximaler Haltedauer"""
        try:
            trade_duration_hours = result.get('trade_duration', 0)
            max_duration = self.risk_parameters['max_trade_duration_hours']
            
            if trade_duration_hours >= max_duration:
                logger.info(f"⏰ Time-based exit for {result['symbol']} after {trade_duration_hours}h")
                self.performance_metrics['time_based_exits'] += 1
                return self._create_result('close', 'max_trade_duration_reached')
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in time based exit check: {e}")
            return None

    def _check_volatility_adjustment(self, result: Dict, trade_data: Dict) -> Optional[Dict]:
        """Passt Risk-Parameter basierend auf Marktvolatilität an"""
        try:
            symbol = result['symbol']
            current_volatility = result.get('volatility_level', 0.03)
            
            # Generiere Volatilitäts-basierte Empfehlungen
            if current_volatility > 0.08:  # Sehr hohe Volatilität
                result['recommendations'].append({
                    'type': 'high_volatility_warning',
                    'message': f'Very high volatility detected: {current_volatility:.2%}',
                    'suggestion': 'Consider reducing position size or widening stop loss',
                    'priority': 'high'
                })
            elif current_volatility > 0.05:  # Hohe Volatilität
                result['recommendations'].append({
                    'type': 'volatility_advisory',
                    'message': f'High volatility detected: {current_volatility:.2%}',
                    'suggestion': 'Monitor trade closely and consider tighter risk management',
                    'priority': 'medium'
                })
            
            return None
        except Exception as e:
            logger.error(f"❌ Error in volatility adjustment: {e}")
            return None

    def _get_volatility_buffer(self, symbol: str, price: float) -> float:
        """Berechnet dynamischen Volatilitäts-Puffer für Stop Loss"""
        try:
            volatility = self._calculate_volatility(symbol)
            # Puffer ist 1.5x Volatilität, aber maximal 3%
            buffer = min(volatility * self.risk_parameters['volatility_multiplier'], 0.03)
            return max(buffer, 0.005)  # Mindestens 0.5% Buffer
        except:
            return 0.01  # Default 1% Buffer

    def _calculate_volatility(self, symbol: str) -> float:
        """Berechnet die Volatilität eines Symbols mit erweiterter Logik"""
        try:
            # Cache für 10 Minuten
            if symbol in self.volatility_cache:
                cache_time, volatility = self.volatility_cache[symbol]
                if (datetime.now() - cache_time).total_seconds() < 600:
                    return volatility
            
            # Dynamische Volatilitäts-Berechnung basierend auf Symbol-Typ
            volatility_map = {
                'BTCUSDT': 0.025, 'ETHUSDT': 0.030, 'BNBUSDT': 0.035,
                'ADAUSDT': 0.045, 'DOTUSDT': 0.040, 'SOLUSDT': 0.050,
                'XRPUSDT': 0.038, 'DOGEUSDT': 0.055, 'LTCUSDT': 0.032,
                'default': 0.035
            }
            
            # Finde beste Übereinstimmung
            volatility = volatility_map['default']
            for key, value in volatility_map.items():
                if key in symbol:
                    volatility = value
                    break
            
            # Aktualisiere Cache
            self.volatility_cache[symbol] = (datetime.now(), volatility)
            
            return volatility
            
        except Exception as e:
            logger.error(f"❌ Error calculating volatility for {symbol}: {e}")
            return 0.03  # Default volatility

    def _generate_recommendations(self, result: Dict, trade_data: Dict) -> List[Dict]:
        """Generiert PROFESSIONELLE Handlungsempfehlungen"""
        recommendations = []
        
        # Profit-basierte Empfehlungen
        pnl_percentage = result['pnl_percentage']
        
        if pnl_percentage > 20:
            recommendations.append({
                'type': 'excellent_profit',
                'message': f'Exceptional profit achieved: {pnl_percentage:.2f}%',
                'suggestion': 'Consider taking significant profits or moving stop loss to lock in gains',
                'priority': 'high'
            })
        elif pnl_percentage > 10:
            recommendations.append({
                'type': 'good_profit',
                'message': f'Strong profit achieved: {pnl_percentage:.2f}%',
                'suggestion': 'Consider partial profit taking or trailing stop activation',
                'priority': 'medium'
            })
        elif pnl_percentage < -8:
            recommendations.append({
                'type': 'significant_drawdown',
                'message': f'Significant drawdown: {pnl_percentage:.2f}%',
                'suggestion': 'Monitor stop loss closely and consider early exit if trend continues',
                'priority': 'high'
            })
        
        # Time-basierte Empfehlungen
        trade_duration = result.get('trade_duration', 0)
        if trade_duration > 48:  # 2 Tage
            recommendations.append({
                'type': 'extended_trade_duration',
                'message': f'Trade active for {trade_duration}h',
                'suggestion': 'Review trade thesis and consider exit if original conditions changed',
                'priority': 'medium'
            })
        
        # Confidence-basierte Empfehlungen
        confidence = result.get('confidence_score', 50)
        if confidence < 30:
            recommendations.append({
                'type': 'low_confidence',
                'message': f'Low confidence score: {confidence:.1f}',
                'suggestion': 'Consider early exit or reducing position size',
                'priority': 'medium'
            })
        
        return recommendations

    def _log_trade_status(self, result: Dict):
        """Loggt detaillierten Trade-Status mit erweiterter Information"""
        try:
            # Logge nur bei signifikanten Ereignissen oder regelmäßig
            should_log = (
                result['action'] != 'hold' or 
                self.performance_metrics['trades_evaluated'] % 20 == 0 or
                abs(result['pnl_percentage']) > 5
            )
            
            if should_log:
                logger.info(f"""
📊 PROFESSIONAL TRADE EVALUATION: {result['symbol']}
├ 💰 Entry: {result['entry_price']:,.2f} | Current: {result['current_price']:,.2f}
├ 📈 PnL: {result['current_pnl']:+.2f} USDT ({result['pnl_percentage']:+.2f}%)
├ ⚖️ Leverage: {result['leverage']}x | R/R: {result.get('risk_reward_ratio', 1.0):.2f}
├ 🕒 Duration: {result.get('trade_duration', 0)}h | Confidence: {result.get('confidence_score', 50):.1f}
├ 🎯 Action: {result['action'].upper()} | Reason: {result['reason']}
├ 🔧 Status: {result['status']} | Volatility: {result.get('volatility_level', 0.03):.2%}
└ 💡 Recommendations: {len(result.get('recommendations', []))}
""")
                
        except Exception as e:
            logger.debug(f"⚠️ Error logging trade status: {e}")

    def _create_result(self, action: str, reason: str, **kwargs) -> Dict[str, Any]:
        """Erstellt ein standardisiertes Result-Dictionary"""
        base_result = {
            'action': action,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'description': self._get_action_description(action, reason)
        }
        base_result.update(kwargs)
        return base_result

    def _get_action_description(self, action: str, reason: str) -> str:
        """Gibt beschreibenden Text für Aktionen zurück"""
        descriptions = {
            'close': 'Close entire position',
            'partial_close': 'Close portion of position',
            'update_stoploss': 'Update stop loss level',
            'hold': 'Maintain current position',
            'none': 'No action required'
        }
        return descriptions.get(action, 'Unknown action')

    def _update_performance_metrics(self, action: str, reason: str):
        """Aktualisiert Performance-Metriken mit detailliertem Tracking"""
        if 'stop_loss' in reason:
            self.performance_metrics['stop_loss_triggers'] += 1
            self.performance_metrics['failed_trades'] += 1
        elif 'target' in reason or 'tp' in reason.lower():
            self.performance_metrics['take_profit_triggers'] += 1
            self.performance_metrics['successful_trades'] += 1
        elif 'emergency' in reason:
            self.performance_metrics['emergency_stops'] += 1
            self.performance_metrics['failed_trades'] += 1
        elif 'partial_profit' in reason:
            self.performance_metrics['partial_profit_taken'] += 1
        elif 'duration' in reason:
            self.performance_metrics['time_based_exits'] += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Gibt UM FASSENDE Performance-Metriken zurück"""
        total_trades = self.performance_metrics['successful_trades'] + self.performance_metrics['failed_trades']
        win_rate = (
            (self.performance_metrics['successful_trades'] / total_trades * 100)
            if total_trades > 0 else 0
        )
        
        return {
            **self.performance_metrics,
            'total_trades_evaluated': self.performance_metrics['trades_evaluated'],
            'win_rate_percent': round(win_rate, 2),
            'active_trades_monitored': len(self.trade_history),
            'volatility_cache_size': len(self.volatility_cache),
            'breakeven_activated_count': len(self.breakeven_activated),
            'trailing_stop_activated_count': len(self.trailing_stop_activated),
            'system_uptime_hours': int((datetime.now() - self._get_start_time()).total_seconds() / 3600)
        }

    def _get_start_time(self) -> datetime:
        """Gibt Startzeit des Risk Managers zurück"""
        if not hasattr(self, '_start_time'):
            self._start_time = datetime.now()
        return self._start_time

    def get_trade_recommendations(self, symbol: str) -> List[Dict[str, Any]]:
        """Gibt spezifische Empfehlungen für einen Trade"""
        try:
            # Verwende aktuellen Preis für realistische Bewertung
            from enhanced_binance_api import binance_api
            current_price = binance_api.get_current_price(symbol)
            result = self.evaluate_trade(symbol, current_price)
            return result.get('recommendations', [])
        except Exception as e:
            logger.error(f"❌ Error getting trade recommendations for {symbol}: {e}")
            return []

    def reset_trade_state(self, symbol: str):
        """Setzt den State für einen spezifischen Trade zurück"""
        try:
            if symbol in self.breakeven_activated:
                self.breakeven_activated.remove(symbol)
            if symbol in self.trailing_stop_activated:
                self.trailing_stop_activated.remove(symbol)
            if symbol in self.partial_profit_taken:
                self.partial_profit_taken.remove(symbol)
            if symbol in self.trade_history:
                del self.trade_history[symbol]
            
            logger.info(f"🔄 Reset trade state for {symbol}")
        except Exception as e:
            logger.error(f"❌ Error resetting trade state for {symbol}: {e}")

    def get_risk_parameters(self) -> Dict[str, Any]:
        """Gibt aktuelle Risk Parameter zurück"""
        return self.risk_parameters.copy()

    def update_risk_parameters(self, new_parameters: Dict[str, Any]):
        """Aktualisiert Risk Parameter mit Validierung"""
        try:
            for key, value in new_parameters.items():
                if key in self.risk_parameters:
                    # Validiere Werte
                    if key.endswith('_activation') or key.endswith('_distance'):
                        if 0 < value <= 0.5:  # Max 50%
                            self.risk_parameters[key] = value
                        else:
                            logger.warning(f"⚠️ Invalid value for {key}: {value}")
                    else:
                        self.risk_parameters[key] = value
            
            logger.info("✅ Risk parameters updated successfully")
        except Exception as e:
            logger.error(f"❌ Error updating risk parameters: {e}")

# Globale Instanz
risk_manager = AdvancedRiskManager()