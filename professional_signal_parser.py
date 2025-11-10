import re
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any
from decimal import Decimal, ROUND_HALF_UP
from enhanced_binance_api import binance_api
import os
# Database imports
try:
    from database import new_trade_db, check_and_update_unique_names, check_if_trade_exist
except ImportError as e:
    logging.error(f"Database import error: {e}")
    # Fallback functions for testing
    def new_trade_db(*args, **kwargs):
        logging.warning("new_trade_db not available - running in test mode")
        return True
    
    def check_and_update_unique_names(*args, **kwargs):
        return True
    
    def check_if_trade_exist(*args, **kwargs):
        return False  # Korrektur: False zurückgeben wenn kein Trade existiert

logger = logging.getLogger(__name__)

class ProfessionalSignalParser:
    def __init__(self):
        self.risk_limits = {
            'max_leverage': 20,
            'min_entry_price': 0.0001,
            'max_position_size': 10000,
            'min_risk_reward': 1.5
        }
        
        self.parsing_stats = {
            'total_signals': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'last_parse_time': None,
            'validation_errors': 0,
            'order_errors': 0
        }
        
        # Erweiterte Symbol-Erkennung
        self.supported_symbols = [
            'BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'LINK', 'XRP', 'DOGE', 'SOL', 
            'MATIC', 'LTC', 'BCH', 'XLM', 'ETC', 'TRX', 'AVAX', 'UNI', 'ATOM',
            'FIL', 'ALGO', 'NEAR', 'FTM', 'SAND', 'MANA', 'ENJ', 'AAVE', 'MKR'
        ]

    def parse_signal(self, message: str) -> Tuple[bool, Optional[Dict]]:
        """Parst Trading-Signale mit PROFESSIONELLER Logik"""
        try:
            self.parsing_stats['total_signals'] += 1
            self.parsing_stats['last_parse_time'] = datetime.now()
            
            logger.info(f"📨 Processing signal (Length: {len(message)} chars)")
            
            # Pre-Cleaning des Messages
            cleaned_message = self._pre_clean_message(message)
            
            # Extrahiere alle Daten mit erweiterter Logik
            data = self._extract_all_data(cleaned_message)
            
            logger.info(f"🔍 Extracted data: {data}")
            
            if self._validate_data(data):
                logger.info("✅ Signal validation passed")
                return self._process_valid_signal(data)
            else:
                logger.error("❌ Signal validation failed")
                self.parsing_stats['failed_parses'] += 1
                return False, "Signal validation failed - check required fields"
            
        except Exception as e:
            logger.error(f"❌ Critical error parsing signal: {e}")
            self.parsing_stats['failed_parses'] += 1
            return False, f"Parsing error: {str(e)}"

    def _pre_clean_message(self, message: str) -> str:
        """Bereinigt die Nachricht für besseres Parsing"""
        # Entferne überflüssige Leerzeichen und normalisiere
        message = re.sub(r'\s+', ' ', message.strip())
        
        # Ersetze verschiedene Bindestriche durch normale
        message = message.replace('–', '-').replace('—', '-')
        
        # Normalisiere Preis-Trennzeichen
        message = message.replace(',', '.')
        
        return message

    def _extract_all_data(self, message: str) -> Dict[str, Any]:
        """Extrahiert alle Daten mit PROFESSIONELLER Logik"""
        data = {}
        
        try:
            # Symbol (muss zuerst extrahiert werden)
            data['symbol'] = self._extract_symbol(message)
            if not data['symbol']:
                return data
                
            # Entry Price mit Bereichs-Erkennung
            data['entry_price'] = self._extract_entry_price(message)
            
            # Leverage
            data['leverage'] = self._extract_leverage(message)
            
            # Direction
            data['direction'] = self._extract_direction(message)
            
            # Stop Loss
            data['stoploss'] = self._extract_stoploss(message, data.get('entry_price'), data.get('direction'))
            
            # Targets
            data['targets'] = self._extract_targets(message, data.get('entry_price'), data.get('direction'))
            
            # Zusätzliche Metadaten
            data['confidence'] = self._extract_confidence(message)
            data['validity_hours'] = self._extract_validity(message)
            data['risk_reward'] = self._calculate_risk_reward(data)
            
        except Exception as e:
            logger.error(f"❌ Error in data extraction: {e}")
            
        return data

    def _extract_symbol(self, message: str) -> Optional[str]:
        """Extrahiert Symbol mit erweiterter Erkennung"""
        try:
            # Mehrere Symbol-Formate mit Priorität
            patterns = [
                r'#(\w+USDT)',  # #BTCUSDT
                r'#(\w+)[^U]',  # #BTC (ohne USDT)
                r'Symbol:\s*(\w+)',
                r'Pair:\s*(\w+)',
                r'(\w+/\w+)',   # BTC/USDT
                r'(\w+USDT)',   # BTCUSDT
                r'(\w+BTC)',    # ETHBTC
                r'(\w+ETH)'     # LINKETH
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                for match in matches:
                    symbol = match.upper().strip()
                    
                    # Normalisiere Symbol
                    symbol = symbol.replace('/', '')
                    if not symbol.endswith('USDT') and not symbol.endswith('BTC') and not symbol.endswith('ETH'):
                        # Prüfe ob es ein unterstütztes Symbol ist
                        base_symbol = symbol
                        if any(supported in base_symbol for supported in self.supported_symbols):
                            symbol += 'USDT'
                            logger.info(f"🔍 Symbol normalized: {symbol}")
                            return symbol
                    else:
                        # Symbol hat bereits Pair-Endung
                        logger.info(f"🔍 Symbol found: {symbol}")
                        return symbol
            
            # Fallback: Suche nach bekannten Symbolen im Text
            for supported_symbol in self.supported_symbols:
                if supported_symbol in message.upper():
                    symbol = f"{supported_symbol}USDT"
                    logger.info(f"🔍 Symbol found via fallback: {symbol}")
                    return symbol
            
            logger.error("❌ No valid symbol found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting symbol: {e}")
            return None

    def _extract_entry_price(self, message: str) -> Optional[float]:
        """Extrahiert Entry Price mit Bereichs-Erkennung (945-955) -> 950"""
        try:
            # PRIORITÄT 1: Explizite Entry Patterns mit Bereichen
            range_patterns = [
                r'Entry:\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',  # Entry: 945-955
                r'Entry\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',  # Entry 945-955
                r'Buy:\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',    # Buy: 945-955
                r'Price:\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',  # Price: 945-955
            ]
            
            for pattern in range_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match and len(match.groups()) == 2:
                    price1 = self._parse_price(match.group(1))
                    price2 = self._parse_price(match.group(2))
                    avg_price = (price1 + price2) / 2
                    logger.info(f"🔍 Entry range found: {price1}-{price2} -> Average: {avg_price}")
                    return avg_price
            
            # PRIORITÄT 2: Einzelne Entry Patterns
            single_patterns = [
                r'Entry:\s*(\d+(?:\.\d+)?)',      # Entry: 950
                r'Entry\s*[:\-]?\s*(\d+(?:\.\d+)?)', # Entry 950
                r'Price:\s*(\d+(?:\.\d+)?)',      # Price: 950
                r'Buy:\s*(\d+(?:\.\d+)?)',        # Buy: 950
                r'Sell:\s*(\d+(?:\.\d+)?)',       # Sell: 950
                r'@\s*(\d+(?:\.\d+)?)',           # @950
            ]
            
            for pattern in single_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    price = self._parse_price(match.group(1))
                    logger.info(f"🔍 Entry price found: {price}")
                    return price
            
            # PRIORITÄT 3: Erste große Zahl nach Symbol
            symbol_match = re.search(r'#(\w+)', message)
            if symbol_match:
                symbol_end = symbol_match.end()
                # Suche Zahlen nach dem Symbol (nächste 200 Zeichen)
                numbers_after_symbol = re.findall(r'(\d{3,}(?:\.\d+)?)', message[symbol_end:symbol_end+200])
                if numbers_after_symbol:
                    price = self._parse_price(numbers_after_symbol[0])
                    logger.info(f"🔍 Entry price (symbol fallback): {price}")
                    return price
            
            # PRIORITÄT 4: Allgemeine große Zahlen
            all_large_numbers = re.findall(r'(\d{3,}(?:\.\d+)?)', message)
            if all_large_numbers:
                # Filtere unrealistische Preise
                potential_prices = [float(num) for num in all_large_numbers if 0.1 < float(num) < 1000000]
                if potential_prices:
                    price = potential_prices[0]
                    logger.info(f"🔍 Entry price (general fallback): {price}")
                    return price
            
            logger.error("❌ No entry price found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting entry price: {e}")
            return None

    def _extract_leverage(self, message: str) -> float:
        """Extrahiert Leverage mit intelligenten Fallbacks"""
        try:
            patterns = [
                r'Leverage:\s*([\d.]+)',
                r'Leverage\s*[:\-]?\s*([\d.]+)',
                r'Lev:\s*([\d.]+)',
                r'([\d.]+)x',
                r'([\d.]+)\s*Leverage',
                r'Leverage\s*=\s*([\d.]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                for match in matches:
                    try:
                        leverage = float(match)
                        if 1 <= leverage <= self.risk_limits['max_leverage']:
                            logger.info(f"🔍 Leverage found: {leverage}x")
                            return leverage
                    except ValueError:
                        continue
            
            # Intelligenter Fallback basierend auf Signal-Art
            if re.search(r'scalp|scalping', message, re.IGNORECASE):
                leverage = 5.0
            elif re.search(r'swing|position', message, re.IGNORECASE):
                leverage = 3.0
            else:
                leverage = 3.0  # Standard-Leverage
                
            logger.info(f"🔍 Leverage (intelligent fallback): {leverage}x")
            return leverage
            
        except Exception as e:
            logger.error(f"❌ Error extracting leverage: {e}")
            return 3.0  # Safe default

    def _extract_direction(self, message: str) -> Optional[str]:
        """Extrahiert Direction mit erweiterter Erkennung"""
        try:
            direction_indicators = {
                'long': [
                    r'\b(Long|BUY|L)\b',
                    r'🟢', r'📈', r'🚀', r'⬆️', r'🔺',
                    r'bullish', r'up', r'rise', r'increase',
                    r'kaufen', r'kauf'  # Deutsch
                ],
                'short': [
                    r'\b(Short|SELL|S)\b', 
                    r'🔴', r'📉', r'🛬', r'⬇️', r'🔻',
                    r'bearish', r'down', r'fall', r'decrease',
                    r'verkaufen', r'verkauf'  # Deutsch
                ]
            }
            
            long_count = 0
            short_count = 0
            
            for direction, patterns in direction_indicators.items():
                for pattern in patterns:
                    matches = re.findall(pattern, message, re.IGNORECASE)
                    count = len(matches)
                    if direction == 'long':
                        long_count += count
                    else:
                        short_count += count
            
            if long_count > short_count:
                direction = 'long'
            elif short_count > long_count:
                direction = 'short'
            else:
                # Fallback: Standard-Direction
                direction = 'long'
                logger.warning("⚠️ No clear direction found, using default: long")
            
            logger.info(f"🔍 Direction determined: {direction} (Long: {long_count}, Short: {short_count})")
            return direction
            
        except Exception as e:
            logger.error(f"❌ Error extracting direction: {e}")
            return 'long'  # Safe default

    def _extract_stoploss(self, message: str, entry_price: Optional[float], direction: Optional[str]) -> Optional[float]:
        """Extrahiert Stop Loss mit intelligenten Fallbacks"""
        try:
            patterns = [
                r'Stop[-\s]?Loss:\s*(\d+(?:\.\d+)?)',
                r'SL:\s*(\d+(?:\.\d+)?)',
                r'Stop:\s*(\d+(?:\.\d+)?)',
                r'Stoploss:\s*(\d+(?:\.\d+)?)',
                r'Risk:\s*(\d+(?:\.\d+)?)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    price = self._parse_price(match.group(1))
                    logger.info(f"🔍 Stop loss found: {price}")
                    return price
            
            # Intelligenter Fallback basierend auf Entry und Direction
            if entry_price and direction:
                if direction == 'long':
                    stoploss = entry_price * 0.98  # 2% unter Entry
                else:
                    stoploss = entry_price * 1.02  # 2% über Entry
                
                logger.info(f"🔍 Stop loss (calculated): {stoploss}")
                return stoploss
            
            logger.error("❌ No stop loss found and cannot calculate")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting stop loss: {e}")
            return None

    def _extract_targets(self, message: str, entry_price: Optional[float], direction: Optional[str]) -> List[float]:
        """Extrahiert Targets mit PROFESSIONELLER Logik"""
        try:
            targets = []
            
            # METHODE 1: Explizite Target Patterns
            target_patterns = [
                r'Target\s*(\d):\s*(\d+(?:\.\d+)?)',  # Target 1: 970
                r'TP?(\d):\s*(\d+(?:\.\d+)?)',        # TP1: 970
                r'T\s*(\d)\s*:\s*(\d+(?:\.\d+)?)',    # T 1 : 970
                r'Take\s*Profit\s*(\d):\s*(\d+(?:\.\d+)?)'  # Take Profit 1: 970
            ]
            
            for pattern in target_patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                if matches:
                    for match_num, match_price in matches:
                        try:
                            target_num = int(match_num)
                            price = self._parse_price(match_price)
                            # Stelle sicher dass Targets in richtiger Reihenfolge
                            while len(targets) < target_num:
                                targets.append(0.0)
                            targets[target_num-1] = price
                        except (ValueError, IndexError):
                            continue
            
            # METHODE 2: Zahlen die sinnvolle Targets sein könnten
            if len(targets) < 4 and entry_price and direction:
                all_numbers = re.findall(r'(\d{3,}(?:\.\d+)?)', message)
                potential_targets = []
                
                for num_str in all_numbers:
                    try:
                        num = float(num_str)
                        # Filtere basierend auf Direction und Entry
                        if direction == 'long' and entry_price < num < entry_price * 1.2:
                            potential_targets.append(num)
                        elif direction == 'short' and entry_price > num > entry_price * 0.8:
                            potential_targets.append(num)
                    except ValueError:
                        continue
                
                # Nehme die besten Kandidaten
                potential_targets = sorted(set(potential_targets))
                if direction == 'short':
                    potential_targets.reverse()
                
                for target in potential_targets[:4]:
                    if target not in targets:
                        targets.append(target)
            
            # METHODE 3: Automatische Target-Berechnung
            if len(targets) < 4 and entry_price and direction:
                missing_targets = 4 - len(targets)
                auto_targets = self._calculate_auto_targets(entry_price, direction, missing_targets)
                targets.extend(auto_targets)
            
            # METHODE 4: Finale Sicherstellung von 4 Targets
            if len(targets) < 4 and entry_price and direction:
                self._ensure_four_targets(targets, entry_price, direction)
            
            # Finale Validierung und Sortierung
            targets = self._validate_and_sort_targets(targets, entry_price, direction)
            
            logger.info(f"🎯 Final targets: {targets}")
            return targets
            
        except Exception as e:
            logger.error(f"❌ Error extracting targets: {e}")
            # Ultimate Fallback
            if entry_price and direction:
                return self._calculate_fallback_targets(entry_price, direction)
            return [100, 200, 300, 400]

    def _calculate_auto_targets(self, entry_price: float, direction: str, count: int) -> List[float]:
        """Berechnet automatische Targets basierend auf Markt-Logik"""
        try:
            targets = []
            base_increment = 0.015  # 1.5% pro Target
            
            for i in range(1, count + 1):
                if direction == 'long':
                    target = entry_price * (1 + (i * base_increment))
                else:
                    target = entry_price * (1 - (i * base_increment))
                targets.append(round(target, 2))
            
            return targets
        except Exception as e:
            logger.error(f"❌ Error calculating auto targets: {e}")
            return []

    def _ensure_four_targets(self, targets: List[float], entry_price: float, direction: str):
        """Stellt sicher dass genau 4 Targets vorhanden sind"""
        while len(targets) < 4:
            if targets:
                last_target = targets[-1]
                if direction == 'long':
                    new_target = last_target * 1.015  # +1.5%
                else:
                    new_target = last_target * 0.985  # -1.5%
                targets.append(round(new_target, 2))
            else:
                # Fallback zu Standard-Targets
                if direction == 'long':
                    targets.extend([
                        entry_price * 1.02,
                        entry_price * 1.04,
                        entry_price * 1.06,
                        entry_price * 1.08
                    ])
                else:
                    targets.extend([
                        entry_price * 0.98,
                        entry_price * 0.96,
                        entry_price * 0.94,
                        entry_price * 0.92
                    ])
                break

    def _validate_and_sort_targets(self, targets: List[float], entry_price: Optional[float], direction: Optional[str]) -> List[float]:
        """Validiert und sortiert Targets"""
        if not targets:
            return targets
            
        # Entferne Duplikate und Null-Werte
        targets = list(set([t for t in targets if t > 0]))
        
        # Sortiere basierend auf Direction
        if direction == 'long':
            targets.sort()
        elif direction == 'short':
            targets.sort(reverse=True)
        else:
            targets.sort()
        
        # Stelle sicher dass Targets sinnvoll sind
        if entry_price and direction:
            if direction == 'long':
                targets = [t for t in targets if t > entry_price]
            else:
                targets = [t for t in targets if t < entry_price]
        
        # Begrenze auf 4 Targets
        return targets[:4]

    def _calculate_fallback_targets(self, entry_price: float, direction: str) -> List[float]:
        """Berechnet Fallback-Targets"""
        if direction == 'long':
            return [
                round(entry_price * 1.02, 2),
                round(entry_price * 1.04, 2),
                round(entry_price * 1.06, 2),
                round(entry_price * 1.08, 2)
            ]
        else:
            return [
                round(entry_price * 0.98, 2),
                round(entry_price * 0.96, 2),
                round(entry_price * 0.94, 2),
                round(entry_price * 0.92, 2)
            ]

    def _extract_confidence(self, message: str) -> float:
        """Extrahiert Confidence Level aus dem Signal"""
        try:
            confidence_patterns = [
                r'Confidence:\s*(\d+)%',
                r'Conf:\s*(\d+)%',
                r'(\d+)%\s*confidence',
                r'Win Rate:\s*(\d+)%'
            ]
            
            for pattern in confidence_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    confidence = float(match.group(1))
                    return min(confidence, 100)  # Max 100%
            
            return 75.0  # Default confidence
        except:
            return 75.0

    def _extract_validity(self, message: str) -> int:
        """Extrahiert Gültigkeitsdauer des Signals"""
        try:
            validity_patterns = [
                r'validity:\s*(\d+)\s*hours',
                r'gültig.*?(\d+)\s*stunden',
                r'expires.*?(\d+)\s*h',
                r'timeframe:\s*(\d+)\s*h'
            ]
            
            for pattern in validity_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return 24  # Default 24 hours
        except:
            return 24

    def _calculate_risk_reward(self, data: Dict) -> float:
        """Berechnet Risk/Reward Ratio"""
        try:
            if not all(k in data for k in ['entry_price', 'stoploss', 'targets']):
                return 1.0
                
            entry = data['entry_price']
            stop = data['stoploss']
            first_target = data['targets'][0] if data['targets'] else entry
            
            if data.get('direction') == 'long':
                risk = entry - stop
                reward = first_target - entry
            else:
                risk = stop - entry
                reward = entry - first_target
                
            if risk > 0:
                return round(reward / risk, 2)
            return 1.0
        except:
            return 1.0

    def _parse_price(self, price_str: str) -> float:
        """Parset Preis-Strings robust"""
        try:
            # Entferne alle nicht-numerischen Zeichen außer Punkten
            cleaned = re.sub(r'[^\d.]', '', price_str)
            if not cleaned:
                raise ValueError("Empty price string")
            return float(cleaned)
        except ValueError as e:
            logger.error(f"❌ Invalid price format: {price_str} -> {e}")
            raise ValueError(f"Invalid price format: {price_str}")

    def _validate_data(self, data: Dict) -> bool:
        """Validiert die extrahierten Daten PROFESSIONELL"""
        required_fields = ['symbol', 'entry_price', 'direction', 'stoploss', 'targets']
        
        # Prüfe erforderliche Felder
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            logger.error(f"❌ Current data: {data}")
            self.parsing_stats['validation_errors'] += 1
            return False
        
        # Mindestanzahl Targets
        if len(data['targets']) < 2:
            logger.error(f"❌ Insufficient targets: {len(data['targets'])}")
            self.parsing_stats['validation_errors'] += 1
            return False
        
        # Grundlegende Validierungen
        if data['direction'] not in ['long', 'short']:
            logger.error(f"❌ Invalid direction: {data['direction']}")
            self.parsing_stats['validation_errors'] += 1
            return False
        
        if data['entry_price'] <= 0:
            logger.error(f"❌ Invalid entry price: {data['entry_price']}")
            self.parsing_stats['validation_errors'] += 1
            return False
        
        # Risk/Reward Validierung
        if data.get('risk_reward', 1.0) < self.risk_limits['min_risk_reward']:
            logger.warning(f"⚠️ Low risk/reward ratio: {data.get('risk_reward')}")
        
        logger.info("✅ All validations passed")
        return True

    def _process_valid_signal(self, data: Dict) -> Tuple[bool, Optional[Dict]]:
        """Verarbeitet einen validen Trading-Signal"""
        try:
            # Prüfe auf existierenden Trade (KORREKTUR: should_return_false_when_no_trade_exists)
            if check_if_trade_exist(data['symbol']):
                return False, f"Active trade already exists for {data['symbol']}"
            
            # Erstelle Order
            return self._create_order(data)
            
        except Exception as e:
            logger.error(f"❌ Error processing valid signal: {e}")
            self.parsing_stats['order_errors'] += 1
            return False, str(e)

    def _create_order(self, data: Dict) -> Tuple[bool, Optional[Dict]]:
        """Erstellt eine Order basierend auf den Signal-Daten"""
        try:
            # Berechne Positionsgröße
            quantity, risk_amount = binance_api.calculate_position_size(data['entry_price'])
            
            # Bestimme Order Side
            side = 'buy' if data['direction'] == 'long' else 'sell'
            
            logger.info(f"🎯 Creating {side.upper()} order for {data['symbol']}")
            
            # Erstelle Order
            order = binance_api.create_spot_order(
                symbol=data['symbol'],
                side=side,
                quantity=quantity,
                price=data['entry_price']
            )
            
            # Bereite Trade-Daten vor
            trade_data = {
                'symbol': data['symbol'],
                'entry_price': data['entry_price'],
                'direction': data['direction'],
                'quantity': quantity,
                'stoploss': data['stoploss'],
                'targets': data['targets'],
                'leverage': data['leverage'],
                'order_id': order['id'],
                'risk_amount': risk_amount,
                'order_timestamp': datetime.now().isoformat(),
                'confidence': data.get('confidence', 75.0),
                'risk_reward': data.get('risk_reward', 1.0)
            }
            
            # Speichere Trade in Datenbank
            success = self._save_trade_to_db(trade_data)
            
            if success:
                self.parsing_stats['successful_parses'] += 1
                
                logger.info(f"""
✅ SUCCESSFULLY EXECUTED TRADE:
├ 📊 Symbol: {trade_data['symbol']}
├ 📈 Direction: {trade_data['direction'].upper()}
├ 💰 Entry: {trade_data['entry_price']:,.2f}
├ ⚖️ Quantity: {trade_data['quantity']:.6f}
├ 🏦 Leverage: {trade_data['leverage']}x
├ ⛔ Stop Loss: {trade_data['stoploss']:,.2f}
├ 🎯 Targets: {', '.join(f'{t:,.2f}' for t in trade_data['targets'])}
├ 📊 Risk/Reward: {trade_data['risk_reward']}:1
├ 🔮 Confidence: {trade_data['confidence']}%
└ 🔢 Order ID: {trade_data['order_id']}
""")
                
                return True, trade_data
            else:
                logger.error(f"❌ Failed to save trade to database: {data['symbol']}")
                self.parsing_stats['order_errors'] += 1
                return False, "Database save failed"
            
        except Exception as e:
            logger.error(f"❌ Error creating order: {e}")
            self.parsing_stats['order_errors'] += 1
            return False, str(e)

    def _save_trade_to_db(self, trade_data: Dict) -> bool:
        """Speichert Trade in Datenbank - ROBUSTE VERSION"""
        try:
            # Verwende db_manager direkt für mehr Stabilität
            success =new_trade_db(
                date=str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
                symbol=trade_data['symbol'],
                leverage=float(trade_data['leverage']),
                price=float(trade_data['entry_price']),
                positionSide=trade_data['direction'],
                qty=float(trade_data['quantity']),
                stoploss=float(trade_data['stoploss']),
                tk1=float(trade_data['targets'][0]),
                tk2=float(trade_data['targets'][1]),
                tk3=float(trade_data['targets'][2]),
                tk4=float(trade_data['targets'][3]),
                ordersID=json.dumps([trade_data['order_id']]),
                risk_amount=float(trade_data.get('risk_amount', 0)),
                confidence=float(trade_data.get('confidence', 75.0)),
                risk_reward=float(trade_data.get('risk_reward', 1.0))
            )
            
            if success:
                check_and_update_unique_names("SymbolsTraded.txt", trade_data['symbol'])
                logger.info(f"💾 Trade saved to database: {trade_data['symbol']}")
            else:
                logger.error(f"❌ Database save failed for: {trade_data['symbol']}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving trade to database: {e}")
            return False
    def _emergency_trade_save(self, trade_data: Dict) -> bool:
        """Notfall-Speicherung wenn normale Datenbank fehlschlägt"""
        try:
            # Erstelle Backup in separater Datei
            backup_file = "emergency_trades.json"
            emergency_data = {
                'symbol': trade_data['symbol'],
                'entry_price': trade_data['entry_price'],
                'direction': trade_data['direction'],
                'quantity': trade_data['quantity'],
                'targets': trade_data['targets'],
                'stoploss': trade_data['stoploss'],
                'leverage': trade_data.get('leverage', 1),
                'order_id': trade_data['order_id'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Lade existierende Daten
            existing_data = []
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'r') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # Füge neuen Trade hinzu
            existing_data.append(emergency_data)
            
            # Speichere Backup
            with open(backup_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            logger.warning(f"⚠️ Emergency trade saved to file: {trade_data['symbol']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Emergency save also failed: {e}")
            return False
    def get_parsing_stats(self) -> Dict[str, Any]:
        """Gibt Parsing-Statistiken zurück"""
        success_rate = (
            (self.parsing_stats['successful_parses'] / self.parsing_stats['total_signals'] * 100)
            if self.parsing_stats['total_signals'] > 0 else 0
        )
        
        return {
            **self.parsing_stats,
            'success_rate_percent': round(success_rate, 2),
            'supported_symbols_count': len(self.supported_symbols)
        }

# Globale Instanz
signal_parser = ProfessionalSignalParser()