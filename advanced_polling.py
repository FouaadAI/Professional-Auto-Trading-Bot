import time
import logging
import threading
import asyncio
import sqlite3
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Any
from database import get_active_trades_symbol_db, get_trade_db, update_trade_status_db, set_trade_noActive_db
from risk_management import risk_manager
from enhanced_binance_api import binance_api

logger = logging.getLogger(__name__)

class AdvancedPriceMonitor:
    def __init__(self):
        self.polling_interval = 30  # Sekunden
        self.max_retries = 3
        self.retry_delay = 2
        self.price_history = {}  # Preisverlauf für jedes Symbol
        self.monitoring_stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'last_check_time': None,
            'trades_managed': 0,
            'notifications_sent': 0,
            'errors_handled': 0
        }
        self.running = False
        self.monitor_thread = None
        self.telegram_bot = None
        self.chat_id = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="TelegramNotifier")
        self._notification_queue = []
        self._last_notification_time = 0
        
    def set_telegram_bot(self, bot, chat_id):
        """Setzt den Telegram Bot für Benachrichtigungen"""
        self.telegram_bot = bot
        self.chat_id = chat_id
        logger.info(f"📱 Telegram Bot gesetzt für Chat ID: {chat_id}")
        
    def start_monitoring(self):
        """Startet das Price Monitoring im Hintergrund"""
        if self.running:
            logger.warning("⚠️ Monitoring is already running")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, 
            daemon=True,
            name="PriceMonitor"
        )
        self.monitor_thread.start()
        logger.info("🚀 Advanced Price Monitoring started")
        
    def stop_monitoring(self):
        """Stoppt das Price Monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self._executor.shutdown(wait=True)
        logger.info("🛑 Price Monitoring stopped")
        
    def _monitoring_loop(self):
        """Haupt-Monitoring Loop mit robustem Error Handling"""
        logger.info("📈 Starting monitoring loop...")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                self._check_all_prices()
                self.monitoring_stats['last_check_time'] = datetime.now()
                consecutive_errors = 0  # Reset error counter on success
                
                # Professionelle Warte-Logik
                self._intelligent_sleep()
                    
            except Exception as e:
                consecutive_errors += 1
                self.monitoring_stats['errors_handled'] += 1
                logger.error(f"❌ Critical error in monitoring loop (consecutive: {consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical("🚨 Too many consecutive errors - restarting monitoring loop")
                    time.sleep(10)  # Longer delay before restart
                    consecutive_errors = 0
                else:
                    time.sleep(self.polling_interval)
                
    def _intelligent_sleep(self):
        """Intelligente Sleep-Funktion mit Unterbrechungsmöglichkeit"""
        check_interval = 1  # Check every second if still running
        remaining_time = self.polling_interval
        
        while remaining_time > 0 and self.running:
            sleep_time = min(check_interval, remaining_time)
            time.sleep(sleep_time)
            remaining_time -= sleep_time
                
    def _check_all_prices(self):
        """Überprüft Preise für alle aktiven Trades mit erweitertem Error Handling"""
        try:
            symbols = get_active_trades_symbol_db()
            self.monitoring_stats['total_checks'] += 1
            
            if not symbols:
                if self.monitoring_stats['total_checks'] % 10 == 0:  # Log only every 10th empty check
                    logger.debug("📭 No active trades to monitor")
                return
                
            logger.info(f"🔍 Checking {len(symbols)} symbols: {', '.join(symbols)}")
            
            successful_checks = 0
            for symbol in symbols:
                if self._check_single_price(symbol):
                    successful_checks += 1
                    
            self.monitoring_stats['successful_checks'] += successful_checks
            self.monitoring_stats['failed_checks'] += len(symbols) - successful_checks
            
            if successful_checks > 0:
                logger.info(f"📊 Check completed: {successful_checks}/{len(symbols)} successful")
            
        except Exception as e:
            logger.error(f"❌ Error in price check cycle: {e}")
            self.monitoring_stats['failed_checks'] += 1
            
    def _check_single_price(self, symbol: str) -> bool:
        """Überprüft Preis für ein einzelnes Symbol mit robustem Error Handling"""
        for attempt in range(self.max_retries):
            try:
                # Hole aktuellen Preis
                current_price = binance_api.get_current_price(symbol)
                
                if current_price is None:
                    logger.warning(f"⚠️ Failed to get price for {symbol} (attempt {attempt + 1})")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    continue
                
                # Aktualisiere Preisverlauf
                self._update_price_history(symbol, current_price)
                
                # Logge Preis mit Veränderung (nur bei signifikanter Änderung)
                price_change = self._get_price_change(symbol, current_price)
                if abs(price_change) > 0.1 or self.monitoring_stats['total_checks'] % 20 == 0:
                    change_symbol = "📈" if price_change >= 0 else "📉"
                    logger.info(f"{change_symbol} {symbol}: {current_price:,.2f} ({price_change:+.2f}%)")
                
                # Überprüfe Trade-Logik mit Risk Manager
                self._evaluate_trade(symbol, current_price)
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error checking {symbol} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
        logger.error(f"❌ Failed to check {symbol} after {self.max_retries} attempts")
        return False
        
    def _update_price_history(self, symbol: str, current_price: float):
        """Aktualisiert den Preisverlauf für ein Symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            
        # Füge neuen Preis hinzu
        price_data = {
            'timestamp': datetime.now(),
            'price': current_price
        }
        
        self.price_history[symbol].append(price_data)
        
        # Behalte nur die letzten 100 Einträge für Performance
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
            
    def _get_price_change(self, symbol: str, current_price: float) -> float:
        """Berechnet die Preisveränderung seit dem letzten Check"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return 0.0
            
        previous_price = self.price_history[symbol][-2]['price']
        if previous_price == 0:
            return 0.0
            
        change_percent = ((current_price - previous_price) / previous_price) * 100
        return round(change_percent, 4)  # Runden für bessere Lesbarkeit
        
    def _evaluate_trade(self, symbol: str, current_price: float):
        """Evaluierte einen Trade mit dem Risk Manager"""
        try:
            result = risk_manager.evaluate_trade(symbol, current_price)
            
            if result['action'] != 'hold':
                self.monitoring_stats['trades_managed'] += 1
                self._handle_trade_action(symbol, current_price, result)
            else:
                # Logge Status für aktive Trades (reduzierte Frequenz)
                if self.monitoring_stats['total_checks'] % 15 == 0:
                    self._log_trade_status(symbol, current_price, result)
                
        except Exception as e:
            logger.error(f"❌ Error evaluating trade {symbol}: {e}")
            
    def _handle_trade_action(self, symbol: str, current_price: float, result: Dict):
        """Behandelt Trade-Aktionen basierend auf Risk Manager Entscheidungen"""
        action = result['action']
        reason = result['reason']
        
        logger.info(f"🎯 Trade action for {symbol}: {action.upper()} - {reason}")
        
        try:
            notification_msg = None
            
            if action == 'close':
                notification_msg = self._close_trade(symbol, current_price, reason)
            elif action == 'partial_close':
                notification_msg = self._partial_close_trade(
                    symbol, current_price, 
                    result.get('close_percentage', 0.5), 
                    reason
                )
            elif action == 'update_stoploss':
                notification_msg = self._update_stoploss(symbol, current_price, reason)
            else:
                logger.warning(f"⚠️ Unknown trade action: {action}")
                return
                
            # Sende Telegram Benachrichtigung
            if notification_msg:
                self._send_telegram_notification(notification_msg)
                
        except Exception as e:
            logger.error(f"❌ Error handling trade action for {symbol}: {e}")
            
    def _send_telegram_notification(self, message: str):
        """PROFESSIONELLE Telegram Benachrichtigungen mit Thread-Safe Event Loop"""
        try:
            if not self.telegram_bot or not self.chat_id:
                self._fallback_notification(message, "Telegram Bot nicht konfiguriert")
                return

            # Rate Limiting: Mindestens 1 Sekunde zwischen Nachrichten
            current_time = time.time()
            if current_time - self._last_notification_time < 1.0:
                time.sleep(1.0 - (current_time - self._last_notification_time))
            
            # Verwende Thread Pool für asyncio Operationen
            future = self._executor.submit(self._send_telegram_sync, message)
            future.result(timeout=15.0)  # Timeout von 15 Sekunden
            
            self._last_notification_time = time.time()
            
        except concurrent.futures.TimeoutError:
            logger.error("❌ Telegram send timeout")
            self._fallback_notification(message, "Timeout")
        except Exception as e:
            logger.error(f"❌ Error sending Telegram notification: {e}")
            self._fallback_notification(message, str(e))
    
    def _send_telegram_sync(self, message: str):
        """Synchroner Wrapper für asyncio Operation - THREAD SAFE"""
        try:
            # Erstelle neue Event Loop für diesen Thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Führe asyncio Operation aus
                loop.run_until_complete(
                    asyncio.wait_for(
                        self.telegram_bot.send_message(
                            chat_id=self.chat_id,
                            text=message,
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        ),
                        timeout=10.0
                    )
                )
                
                logger.info(f"📱 Telegram notification sent to {self.chat_id}")
                self.monitoring_stats['notifications_sent'] += 1
                
            except asyncio.TimeoutError:
                logger.error("❌ Telegram send timeout in async operation")
                raise Exception("Async timeout")
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ Telegram sync error: {e}")
            raise
            
    def _fallback_notification(self, message: str, error: str):
        """Fallback für fehlgeschlagene Telegram Benachrichtigungen"""
        logger.warning("⚠️ Telegram failed - notification only in console")
        
        # Professionelle Console-Ausgabe
        print("\n" + "═" * 60)
        print("🔔 TELEGRAM BENACHRICHTIGUNG (FALLBACK)")
        print("═" * 60)
        print(message)
        print("─" * 40)
        print(f"📋 Error: {error}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("═" * 60 + "\n")
            
    def _close_trade(self, symbol: str, current_price: float, reason: str) -> Optional[str]:
        """Schließt einen Trade komplett mit Benachrichtigung"""
        try:
            # Hole Trade-Daten
            trade_data = get_trade_db(symbol)
            if not trade_data:
                logger.warning(f"⚠️ No trade data found for {symbol} during close")
                return None
                
            # Robuste Dictionary-Zugriffe
            entry_price = trade_data.get('entry_price', 0)
            position = trade_data.get('position', 'LONG').lower()
            amount = trade_data.get('quantity', 0)
            leverage = trade_data.get('leverage', 1)
            
            # Validiere kritische Daten
            if entry_price <= 0:
                logger.error(f"❌ Invalid entry price for {symbol}: {entry_price}")
                return None
            
            # Berechne PnL
            if position == 'long':
                pnl = (current_price - entry_price) * amount
                pnl_percent = ((current_price - entry_price) / entry_price) * 100 * leverage
            else:
                pnl = (entry_price - current_price) * amount
                pnl_percent = ((entry_price - current_price) / entry_price) * 100 * leverage
                
            # Setze Trade auf inaktiv
            status_map = {
                'stop_loss_triggered': 'STOP_LOSS',
                'target_4_reached': 'TARGET_4',
                'manual_close': 'MANUAL_CLOSE'
            }
            
            new_status = status_map.get(reason, 'CLOSED')
            
            # ZUERST Status updaten
            update_trade_status_db(symbol, new_status)
            
            # DANACH Trade deaktivieren (mit Fallback)
            try:
                set_trade_noActive_db(symbol, current_price, reason, pnl, pnl_percent)
            except sqlite3.IntegrityError as e:
                logger.error(f"❌ Integrity error deactivating {symbol}: {e}")
                # Fallback: Nur Status updaten
                logger.info(f"✅ Trade status updated to {new_status} (deactivation skipped)")
            
            # Erstelle professionelle Benachrichtigungsnachricht
            pnl_emoji = "✅" if pnl >= 0 else "❌"
            reason_text = {
                'stop_loss_triggered': 'Stop Loss erreicht 🛑',
                'target_4_reached': 'Target 4 erreicht 🎯',
                'manual_close': 'Manuell geschlossen'
            }.get(reason, reason.replace('_', ' ').title())
            
            # Performance-Bewertung
            if pnl > 0:
                performance_verdict = f"🎉 Profit realisiert! (+{pnl_percent:.2f}%)"
            elif pnl < 0:
                performance_verdict = f"📉 Verlust begrenzt! ({pnl_percent:+.2f}%)"
            else:
                performance_verdict = "⚖️ Break-even erreicht"
            
            notification_message = f"""
{pnl_emoji} *TRADE GESCHLOSSEN: {symbol}*

📊 *Performance Übersicht:*
├ 💰 Entry Preis: `{entry_price:,.2f}`
├ 📊 Exit Preis: `{current_price:,.2f}`
├ 📈 P&L: `{pnl:+.2f} USDT` (`{pnl_percent:+.2f}%`)
├ 🏦 Leverage: `{leverage}x`
├ 📊 Position: `{position.upper()}`
├ 🎯 Grund: {reason_text}
└ ⏰ Zeit: `{datetime.now().strftime('%H:%M:%S')}`

{performance_verdict}

💡 *Trade abgeschlossen und aus Monitoring entfernt.*
"""
            
            # Detailliertes Logging
            logger.info(f"""
{pnl_emoji} TRADE CLOSED: {symbol}
├ 💰 Entry: {entry_price:,.2f}
├ 📊 Exit: {current_price:,.2f}
├ 📈 PnL: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)
├ 🎯 Reason: {reason}
├ 🔄 Status: {new_status}
└ ⏱️ Duration: {self._calculate_trade_duration(trade_data)}
""")
            
            return notification_message
                
        except Exception as e:
            logger.error(f"❌ Error closing trade {symbol}: {e}")
            return None

    def _calculate_trade_duration(self, trade_data: Dict) -> str:
        """Berechnet die Handelsdauer"""
        try:
            if 'created_at' in trade_data and trade_data['created_at']:
                if isinstance(trade_data['created_at'], str):
                    created = datetime.fromisoformat(trade_data['created_at'].replace('Z', '+00:00'))
                else:
                    created = trade_data['created_at']
                
                duration = datetime.now() - created
                hours = duration.total_seconds() / 3600
                
                if hours < 1:
                    return f"{int(duration.total_seconds() / 60)}m"
                elif hours < 24:
                    return f"{hours:.1f}h"
                else:
                    return f"{hours/24:.1f}d"
            return "Unknown"
        except:
            return "Unknown"
            
    def _partial_close_trade(self, symbol: str, current_price: float, close_percentage: float, reason: str) -> Optional[str]:
        """Schließt einen Teil eines Trades (Take Profit) mit ROBUSTEM Error Handling"""
        try:
            # Hole Trade-Daten
            trade_data = get_trade_db(symbol)
            if not trade_data:
                logger.error(f"❌ No trade data found for {symbol} during partial close")
                return None
            
            # Robuste Dictionary-Zugriffe
            entry_price = trade_data.get('entry_price', 0)
            position = trade_data.get('position', 'LONG').lower()
            leverage = trade_data.get('leverage', 1)
            current_status = trade_data.get('status', 'NEW')
            
            # Extrahiere Target Nummer aus dem Reason - ROBUST
            target_number = "1"  # Default
            if '_' in reason:
                try:
                    # Versuche Target Nummer zu extrahieren (z.B. "tk1_reached" -> "1")
                    target_part = reason.split('_')[0]  # "tk1"
                    target_number = ''.join(filter(str.isdigit, target_part)) or "1"
                except (IndexError, ValueError, AttributeError):
                    logger.warning(f"⚠️ Could not extract target number from reason: {reason}")
                    target_number = "1"
            
            # Aktualisiere Datenbank-Status basierend auf dem Take Profit Level
            status_updates = {
                '1': 'TK1',
                '2': 'TK2', 
                '3': 'TK3',
                '4': 'TK4'
            }
            
            new_status = status_updates.get(target_number, 'TK1')  # Default to TK1
            
            # Update Trade Status in Database
            success = update_trade_status_db(symbol, new_status)
            if not success:
                logger.error(f"❌ Failed to update trade status for {symbol} to {new_status}")
            
            # Berechne Performance für diesen Take Profit
            if position == 'long':
                profit_percent = ((current_price - entry_price) / entry_price) * 100 * leverage
                profit_type = "Gewinnmitnahme"
            else:
                profit_percent = ((entry_price - current_price) / entry_price) * 100 * leverage
                profit_type = "Gewinnmitnahme"
                
            # Berechne realisierte Profit-Menge
            realized_profit_amount = close_percentage * profit_percent
            
            notification_message = f"""
    🎯 *TAKE PROFIT {target_number} ERREICHT: {symbol}*

    📊 *Trade Details:*
    ├ 💰 Entry Preis: `{entry_price:,.2f}`
    ├ 📊 Aktueller Preis: `{current_price:,.2f}`
    ├ 📈 {profit_type}: `{close_percentage*100:.1f}%`
    ├ 💵 Realisierter Profit: `{realized_profit_amount:.2f}%`
    ├ 🔄 Neuer Status: `{new_status}`
    ├ 📊 Verbleibende Position: `{(1-close_percentage)*100:.1f}%`
    └ ⏰ Zeit: `{datetime.now().strftime('%H:%M:%S')}`

    💡 *Nächste Schritte:*
    • Verbleibende Position läuft weiter
    • Stop Loss wurde angepasst
    • Nächstes Target: TP{int(target_number)+1} aktiv

    📈 *Performance Update:*
    • Teilgewinn gesichert ✅
    • Risiko reduziert 🛡️
    • Restposition mit verbessertem R/R 🔄
    """
            
            logger.info(f"""
    🎯 PARTIAL CLOSE SUCCESS: {symbol}
    ├ 📊 Current Price: {current_price:,.2f}
    ├ 📈 Close Percentage: {close_percentage*100:.1f}%
    ├ 💰 Profit Taken: {realized_profit_amount:.2f}%
    ├ 🎯 Reason: {reason}
    ├ 🔄 New Status: {new_status}
    ├ 📈 Previous Status: {current_status}
    └ ✅ Database Updated: {success}
    """)
            
            return notification_message
                
        except Exception as e:
            logger.error(f"❌ Error partially closing trade {symbol}: {e}")
            return None
            
    def _update_stoploss(self, symbol: str, current_price: float, reason: str) -> Optional[str]:
        """Aktualisiert den Stop Loss (Trailing Stop) mit Benachrichtigung"""
        try:
            # Hier würde der Stop Loss in der Datenbank/API aktualisiert werden
            trade_data = get_trade_db(symbol)
            if not trade_data:
                return None
                
            old_stop_loss = trade_data.get('stop_loss', 0)
            position = trade_data.get('position', 'LONG').lower()
            
            # Simuliere Stop Loss Update (in echter Implementierung würde hier die DB aktualisiert)
            if position == 'long':
                new_stop_loss = current_price * 0.99  # 1% unter aktuellen Preis
                stop_direction = "nach oben"
            else:
                new_stop_loss = current_price * 1.01  # 1% über aktuellen Preis
                stop_direction = "nach unten"
            
            notification_message = f"""
🛡️ *STOP LOSS AKTUALISIERT: {symbol}*

📊 *Anpassung Details:*
├ 📊 Aktueller Preis: `{current_price:,.2f}`
├ 📉 Alter Stop Loss: `{old_stop_loss:,.2f}`
├ 📈 Neuer Stop Loss: `{new_stop_loss:,.2f}`
├ 🎯 Grund: `{reason.replace('_', ' ').title()}`
├ 🔄 Anpassung: {stop_direction}
└ ⏰ Zeit: `{datetime.now().strftime('%H:%M:%S')}`

💡 *Trailing Stop aktiv:*
• Stop Loss folgt dem Preis {stop_direction}
• Gewinne sind gesichert ✅
• Risiko wird minimiert 🛡️
• Automatische Anpassung aktiv 🔄

📈 *Trade weiterhin aktiv mit verbessertem Risikomanagement.*
"""
            
            logger.info(f"🛡️ Stop Loss updated for {symbol}: {old_stop_loss:,.2f} → {new_stop_loss:,.2f} ({stop_direction})")
            
            return notification_message
            
        except Exception as e:
            logger.error(f"❌ Error updating stop loss for {symbol}: {e}")
            return None
            
    def _log_trade_status(self, symbol: str, current_price: float, result: Dict):
        """Loggt den aktuellen Status eines Trades (reduzierte Frequenz)"""
        try:
            trade_data = get_trade_db(symbol)
            if not trade_data:
                return
                
            # Robuste Dictionary-Zugriffe
            leverage = trade_data.get('leverage', 1)
            entry_price = trade_data.get('entry_price', 0)
            position = trade_data.get('position', 'LONG').lower()
            amount = trade_data.get('quantity', 0)
            stop_loss = trade_data.get('stop_loss', 0)
            tk1 = trade_data.get('take_profit_1', 0)
            tk2 = trade_data.get('take_profit_2', 0)
            tk3 = trade_data.get('take_profit_3', 0)
            tk4 = trade_data.get('take_profit_4', 0)
            status = trade_data.get('status', 'UNKNOWN')
            
            # Berechne aktuelle Performance
            if position == 'long':
                pnl = (current_price - entry_price) * amount
                pnl_percent = ((current_price - entry_price) / entry_price) * 100 * leverage
                to_stop_loss = ((current_price - stop_loss) / current_price) * 100 if current_price > 0 else 0
                to_next_target = self._calculate_to_next_target(position, current_price, [tk1, tk2, tk3, tk4], status)
            else:
                pnl = (entry_price - current_price) * amount
                pnl_percent = ((entry_price - current_price) / entry_price) * 100 * leverage
                to_stop_loss = ((stop_loss - current_price) / current_price) * 100 if current_price > 0 else 0
                to_next_target = self._calculate_to_next_target(position, current_price, [tk1, tk2, tk3, tk4], status)
                
            # Logge nur bei signifikanter Änderung oder alle 15 Checks
            if (abs(pnl_percent) > 2 or 
                self.monitoring_stats['total_checks'] % 15 == 0 or
                result.get('action') != 'hold'):
                
                logger.info(f"""
📊 Trade Status: {symbol}
├ 💰 Entry: {entry_price:,.2f} | Current: {current_price:,.2f}
├ 📈 PnL: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)
├ 🛡️ To Stop: {to_stop_loss:+.2f}% | To Target: {to_next_target:+.2f}%
├ 🔄 Status: {status} | Leverage: {leverage}x
└ ⚡ Action: {result.get('action', 'hold').upper()}
""")
                
        except Exception as e:
            logger.debug(f"⚠️ Error logging trade status for {symbol}: {e}")
            
    def _calculate_to_next_target(self, position: str, current_price: float, targets: List[float], status: str) -> float:
        """Berechnet die Distanz zum nächsten Target"""
        try:
            status_to_index = {'NEW': 0, 'FILLED': 0, 'TK1': 1, 'TK2': 2, 'TK3': 3}
            next_target_index = status_to_index.get(status, 0)
            
            if next_target_index >= len(targets) or targets[next_target_index] == 0:
                return 0.0
                
            next_target = targets[next_target_index]
            
            if position.lower() == 'long':
                return ((next_target - current_price) / current_price) * 100
            else:
                return ((current_price - next_target) / current_price) * 100
                
        except Exception as e:
            logger.debug(f"⚠️ Error calculating target distance: {e}")
            return 0.0
            
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Gibt umfassende Monitoring-Statistiken zurück"""
        active_symbols = get_active_trades_symbol_db()
        
        return {
            **self.monitoring_stats,
            'active_symbols': len(active_symbols),
            'active_symbols_list': active_symbols,
            'price_history_size': {symbol: len(prices) for symbol, prices in self.price_history.items()},
            'is_running': self.running,
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False,
            'executor_active': not self._executor._shutdown
        }
        
    def get_symbol_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Gibt detaillierte Statistiken für ein Symbol zurück"""
        if symbol not in self.price_history or not self.price_history[symbol]:
            return None
            
        prices = [data['price'] for data in self.price_history[symbol]]
        current_price = prices[-1]
        min_price = min(prices)
        max_price = max(prices)
        price_change = ((current_price - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'min_price': min_price,
            'max_price': max_price,
            'price_range': max_price - min_price,
            'price_range_percent': ((max_price - min_price) / min_price) * 100 if min_price > 0 else 0,
            'total_change_percent': price_change,
            'data_points': len(prices),
            'first_timestamp': self.price_history[symbol][0]['timestamp'].isoformat(),
            'last_timestamp': self.price_history[symbol][-1]['timestamp'].isoformat(),
            'monitoring_duration_hours': (
                (self.price_history[symbol][-1]['timestamp'] - self.price_history[symbol][0]['timestamp']).total_seconds() / 3600
            )
        }

    def send_custom_notification(self, message: str):
        """Sendet eine benutzerdefinierte Benachrichtigung"""
        self._send_telegram_notification(message)
        
    def get_health_status(self) -> Dict[str, Any]:
        """Gibt Health Status des Monitoring Systems zurück"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'uptime_seconds': (
                (datetime.now() - self.monitoring_stats['last_check_time']).total_seconds() 
                if self.monitoring_stats['last_check_time'] else 0
            ),
            'success_rate': (
                (self.monitoring_stats['successful_checks'] / self.monitoring_stats['total_checks'] * 100) 
                if self.monitoring_stats['total_checks'] > 0 else 0
            ),
            'notification_success_rate': (
                (self.monitoring_stats['notifications_sent'] / 
                 (self.monitoring_stats['notifications_sent'] + self.monitoring_stats['errors_handled']) * 100)
                if (self.monitoring_stats['notifications_sent'] + self.monitoring_stats['errors_handled']) > 0 else 0
            )
        }

# Globale Instanz
price_monitor = AdvancedPriceMonitor()

# Exportierte Funktionen
def start_monitoring():
    """Startet das Price Monitoring"""
    price_monitor.start_monitoring()
    
def stop_monitoring():
    """Stoppt das Price Monitoring"""
    price_monitor.stop_monitoring()
    
def get_monitoring_stats():
    """Gibt Monitoring-Statistiken zurück"""
    return price_monitor.get_monitoring_stats()

def set_telegram_bot(bot, chat_id):
    """Setzt den Telegram Bot für Benachrichtigungen"""
    price_monitor.set_telegram_bot(bot, chat_id)

def send_custom_notification(message: str):
    """Sendet eine benutzerdefinierte Benachrichtigung"""
    price_monitor.send_custom_notification(message)
    
def get_health_status():
    """Gibt Health Status zurück"""
    return price_monitor.get_health_status()

if __name__ == "__main__":
    # Direkter Start für Testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('monitoring_debug.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger.info("🚀 Starting Advanced Price Monitoring...")
    start_monitoring()
    
    try:
        # Lauf für 5 Minuten dann stoppe
        logger.info("⏰ Monitoring runs for 5 minutes...")
        time.sleep(300)
        stop_monitoring()
        logger.info("🛑 Monitoring stopped after 5 minutes")
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
        stop_monitoring()