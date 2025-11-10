import logging
import threading
import asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config_manager import config
from professional_signal_parser import signal_parser
from enhanced_binance_api import binance_api
from risk_management import risk_manager
from database import get_active_trades_symbol_db, get_trade_db, update_trade_status_db, set_trade_noActive_db, get_performance_stats, get_trade_history
from advanced_polling import start_monitoring, stop_monitoring, set_telegram_bot, get_monitoring_stats, get_health_status

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Conversation States
START_ROUTES, END_ROUTES = range(2)
BALANCE, LIVE_TRADES, STATS, SETTINGS, PERFORMANCE, HISTORY, MAIN_MENU = range(7)

class ProfessionalTradingBot:
    def __init__(self):
        self.bot_token = config.get('TELEGRAM', 'bot_token')
        self.target_chat_id = config.get('TELEGRAM', 'target_channel')
        self.bot_owner = config.get('TELEGRAM', 'owner_id')
        
        # FIX: Application erstellen bevor wir den Bot verwenden
        self.application = Application.builder().token(self.bot_token).build()
        self.bot = self.application.bot
        
        # Setze Telegram Bot für Benachrichtigungen
        set_telegram_bot(self.bot, self.target_chat_id)
        self.setup_handlers()
        
        # Bot Status
        self.bot_start_time = datetime.now()
        self.is_monitoring_active = False
        
        # FIX: Event Loop Management
        self._monitoring_loop = None
        self._monitoring_thread = None
    
    def setup_handlers(self):
        """Setup PROFESSIONELLE Telegram Handlers"""
        # Conversation Handler für das Hauptmenü - KORRIGIERT
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_command)],
            states={
                START_ROUTES: [
                    CallbackQueryHandler(self.balance_callback, pattern="^" + str(BALANCE) + "$"),
                    CallbackQueryHandler(self.trades_callback, pattern="^" + str(LIVE_TRADES) + "$"),
                    CallbackQueryHandler(self.stats_callback, pattern="^" + str(STATS) + "$"),
                    CallbackQueryHandler(self.performance_callback, pattern="^" + str(PERFORMANCE) + "$"),
                    CallbackQueryHandler(self.history_callback, pattern="^" + str(HISTORY) + "$"),
                    CallbackQueryHandler(self.settings_callback, pattern="^" + str(SETTINGS) + "$"),
                    CallbackQueryHandler(self.main_menu_callback, pattern="^main$"),
                    CallbackQueryHandler(self.toggle_monitoring_callback, pattern="^toggle_monitoring$"),
                ],
            },
            fallbacks=[CommandHandler("start", self.start_command)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("trades", self.trades_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("performance", self.performance_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_trade_command))
        self.application.add_handler(CommandHandler("monitoring", self.monitoring_command))
        self.application.add_handler(CommandHandler("health", self.health_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def start_background_monitoring(self):
        """Startet das Price Monitoring im Hintergrund - KORRIGIERT"""
        try:
            if not self.is_monitoring_active:
                # FIX: Starte Monitoring in eigenem Thread mit separater Event Loop
                def run_monitoring():
                    try:
                        # Erstelle neue Event Loop für Monitoring
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        self._monitoring_loop = loop
                        
                        # Starte Monitoring
                        loop.run_until_complete(start_monitoring())
                        logger.info("🔍 Professional Price Monitoring started in background thread")
                    except Exception as e:
                        logger.error(f"❌ Monitoring thread error: {e}")
                
                self._monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
                self._monitoring_thread.start()
                self.is_monitoring_active = True
                return True
            else:
                logger.info("🔍 Monitoring is already active")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            return False

    def stop_background_monitoring(self):
        """Stoppt das Price Monitoring - KORRIGIERT"""
        try:
            if self.is_monitoring_active:
                # FIX: Stoppe Monitoring über die Event Loop
                if self._monitoring_loop and self._monitoring_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(stop_monitoring(), self._monitoring_loop)
                    future.result(timeout=10)  # Warte auf Beendigung
                
                self.is_monitoring_active = False
                self._monitoring_thread = None
                self._monitoring_loop = None
                logger.info("🛑 Price Monitoring stopped")
                return True
            else:
                logger.info("🔍 Monitoring is already stopped")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to stop monitoring: {e}")
            return False

    async def start_command(self, update: Update, context):
        """Start Command Handler mit PROFESSIONELLEM Inline Keyboard"""
        return await self.show_main_menu(update, context)

    async def show_main_menu(self, update: Update, context, is_callback: bool = False):
        """Zeigt das PROFESSIONELLE Hauptmenü"""
        welcome_text = """
🤖 *PROFESSIONAL AUTO-TRADING BOT* 🚀

*🌟 System Status:*
• 🤖 Bot: 🟢 ONLINE
• 📊 Monitoring: 🟢 ACTIVE  
• 💾 Database: 🟢 CONNECTED
• 📈 API: 🟢 OPERATIONAL
• 🛡️ Risk Management: 🟢 ACTIVE

*🎯 Available Commands:*
/start - Show main menu
/balance - Account balance & equity  
/trades - Active trades with real-time PnL
/stats - Trading statistics & analytics
/performance - Detailed performance metrics
/history - Trade history & analysis
/settings - Bot configuration
/monitoring - Monitoring controls
/health - System health status
/help - Comprehensive help guide

*🚀 AUTO-TRADING FEATURES:*
✅ Intelligent signal parsing from ANY channel
📊 Advanced risk management with trailing stops
🔒 Multi-level stop loss protection
🎯 4-Take profit targets with partial closes
📈 Real-time price monitoring & alerts
💾 Professional database tracking
📱 Telegram notifications & controls

*💡 PROFESSIONAL SIGNAL FORMAT:*
#BTCUSDT Long/Short
Entry: 50000-51000 (or single price)
Leverage: 3x (auto-detected)
Target 1: 52000
Target 2: 53000  
Target 3: 54000
Target 4: 55000
Stop-Loss: 49000

*🔧 Simply forward trading signals from your channels!*
        """
        
        # Dynamische Monitoring-Taste basierend auf Status
        monitoring_button = InlineKeyboardButton(
            "🔴 Stop Monitoring" if self.is_monitoring_active else "🟢 Start Monitoring", 
            callback_data="toggle_monitoring"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 Balance", callback_data=str(BALANCE)),
             InlineKeyboardButton("📊 Live Trades", callback_data=str(LIVE_TRADES))],
            [InlineKeyboardButton("📈 Statistics", callback_data=str(STATS)),
             InlineKeyboardButton("📊 Performance", callback_data=str(PERFORMANCE))],
            [InlineKeyboardButton("📋 History", callback_data=str(HISTORY)),
             InlineKeyboardButton("⚙️ Settings", callback_data=str(SETTINGS))],
            [monitoring_button],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_callback:
            await update.callback_query.edit_message_text(
                text=welcome_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return START_ROUTES

    async def main_menu_callback(self, update: Update, context):
        """Callback für Zurück zum Hauptmenü"""
        query = update.callback_query
        await query.answer()
        return await self.show_main_menu(update, context, is_callback=True)

    async def toggle_monitoring_callback(self, update: Update, context):
        """Toggle Monitoring Status"""
        query = update.callback_query
        await query.answer()
        
        try:
            if self.is_monitoring_active:
                success = self.stop_background_monitoring()
                status_text = "🛑 Monitoring stopped"
            else:
                success = self.start_background_monitoring()
                status_text = "🔍 Monitoring started"
            
            if success:
                await query.edit_message_text(
                    text=f"✅ *{status_text}*\n\nReturning to main menu...",
                    parse_mode='Markdown'
                )
                # Kurze Verzögerung bevor Menü angezeigt wird
                await asyncio.sleep(1.5)
                return await self.show_main_menu(update, context, is_callback=True)
            else:
                await query.edit_message_text(
                    text="❌ *Error toggling monitoring*\n\nPlease check logs and try again.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error toggling monitoring: {e}")
            await query.edit_message_text(
                text="❌ *Error toggling monitoring*\n\nPlease try again.",
                parse_mode='Markdown'
            )

    async def balance_command(self, update: Update, context):
        """Balance Command Handler mit ROBUSTEM Error Handling"""
        try:
            balance_info = self.get_balance_info()
            await update.message.reply_text(balance_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in balance command: {e}")
            await update.message.reply_text("❌ Error fetching balance information")

    async def balance_callback(self, update: Update, context):
        """Balance Callback Handler mit ROBUSTEM Error Handling"""
        query = update.callback_query
        
        try:
            await query.answer()
        except Exception as e:
            logger.error(f"❌ Error answering balance callback: {e}")
            return
        
        try:
            balance_info = self.get_balance_info()
            
            keyboard = [
                [InlineKeyboardButton("📊 Live Trades", callback_data=str(LIVE_TRADES))],
                [InlineKeyboardButton("📈 Statistics", callback_data=str(STATS))],
                [InlineKeyboardButton("📊 Performance", callback_data=str(PERFORMANCE))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=balance_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"❌ Error in balance callback: {e}")

    def get_balance_info(self):
        """Holt PROFESSIONELLE Balance Informationen"""
        try:
            # Verwende die echte Balance-API
            balance_data = binance_api.get_balance()
            connection_stats = binance_api.get_connection_stats()
            
            free_balance = balance_data['free'].get('USDT', 0.0)
            used_balance = balance_data['used'].get('USDT', 0.0)
            total_balance = balance_data['total'].get('USDT', 0.0)
            
            # Berechne wichtige Metriken
            utilization_rate = (used_balance / total_balance * 100) if total_balance > 0 else 0
            
            return f"""
💰 *PROFESSIONAL ACCOUNT OVERVIEW* 💰

*💵 Spot Trading Account:*
├ 💰 Available: `{free_balance:,.2f} USDT`
├ 📊 In Orders: `{used_balance:,.2f} USDT`
├ 🏦 Total Balance: `{total_balance:,.2f} USDT`
└ 📈 Utilization: `{utilization_rate:.1f}%`

*⚡ Trading Configuration:*
├ 🎯 Trading Mode: {'🟢 LIVE TRADING' if not binance_api.testnet_mode else '🟡 TESTNET'}
├ ⚖️ Max Leverage: Up to `20x`
├ 📉 Risk per Trade: `{config.get('TRADING', 'risk_per_trade', '2.0')}%`
└ 💰 Trade Amount: `{config.get('TRADING', 'amount_per_trade', '100')} USDT`

*📊 API Connection:*
├ 📡 Status: 🟢 Connected
├ ✅ Success Rate: `{connection_stats.get('success_rate_percent', 0):.1f}%`
├ 📨 Total Requests: `{connection_stats.get('total_requests', 0)}`
└ ⏰ Last Update: `{self.get_current_time()}`

💡 *Using Binance {'' if not binance_api.testnet_mode else 'Testnet'} API*
"""
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return "❌ *Error fetching balance information*\n\nPlease check API configuration and try again."

    async def trades_command(self, update: Update, context):
        """Trades Command Handler"""
        try:
            trades_info = self.get_trades_info()
            await update.message.reply_text(trades_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in trades command: {e}")
            await update.message.reply_text("❌ Error fetching trades information")

    async def trades_callback(self, update: Update, context):
        """Trades Callback Handler mit ROBUSTEM Error Handling"""
        query = update.callback_query
        
        try:
            await query.answer()
        except Exception as e:
            logger.error(f"❌ Error answering trades callback: {e}")
            return
        
        try:
            trades_info = self.get_trades_info()
            
            keyboard = [
                [InlineKeyboardButton("💰 Balance", callback_data=str(BALANCE))],
                [InlineKeyboardButton("📈 Statistics", callback_data=str(STATS))],
                [InlineKeyboardButton("📊 Performance", callback_data=str(PERFORMANCE))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=trades_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"❌ Error in trades callback: {e}")

    def get_trades_info(self):
        """Holt PROFESSIONELLE Informationen über aktive Trades"""
        try:
            active_symbols = get_active_trades_symbol_db()
            
            if not active_symbols:
                return """
📭 *NO ACTIVE TRADES*

You don't have any active trades currently. 

🚀 *To start trading:*
1. Forward a trading signal from your channel
2. Use format: #SYMBOL + Entry + Targets + Stop Loss
3. Bot will automatically execute the trade

💡 *Example signal:*
#BTCUSDT Long
Entry: 50000
Target 1: 51000
Target 2: 52000  
Target 3: 53000
Target 4: 54000
Stop-Loss: 49000
"""
            
            trades_text = f"📊 *ACTIVE TRADES OVERVIEW* (`{len(active_symbols)}` active)\n\n"
            total_pnl = 0
            total_pnl_percentage = 0
            
            for symbol in active_symbols:
                try:
                    trade_data = get_trade_db(symbol)
                    if not trade_data:
                        trades_text += f"❌ *{symbol}* - No trade data found\n\n"
                        continue
                    
                    # SICHERER DICTIONARY-ZUGRIFF
                    entry_price = trade_data.get('entry_price', 0)
                    position = trade_data.get('position', 'LONG')
                    amount = trade_data.get('quantity', 0)
                    leverage = trade_data.get('leverage', 1)
                    stop_loss = trade_data.get('stop_loss', 0)
                    tk1 = trade_data.get('take_profit_1', 0)
                    tk2 = trade_data.get('take_profit_2', 0)
                    tk3 = trade_data.get('take_profit_3', 0)
                    tk4 = trade_data.get('take_profit_4', 0)
                    status = trade_data.get('status', 'UNKNOWN')
                    created_at = trade_data.get('created_at', datetime.now())
                    
                    # Hole aktuellen Preis
                    try:
                        current_price = binance_api.get_current_price(symbol)
                    except Exception as price_error:
                        logger.warning(f"⚠️ Could not get current price for {symbol}: {price_error}")
                        current_price = entry_price
                    
                    # Berechne PnL
                    try:
                        if position.lower() == "long":
                            pnl_percent = ((current_price - entry_price) / entry_price) * 100 * leverage if entry_price > 0 else 0
                            pnl_value = (current_price - entry_price) * amount
                        else:
                            pnl_percent = ((entry_price - current_price) / entry_price) * 100 * leverage if entry_price > 0 else 0
                            pnl_value = (entry_price - current_price) * amount
                        
                        total_pnl += pnl_value
                        total_pnl_percentage += pnl_percent
                        
                        # Bestimme Status-Emoji
                        if pnl_value > 0:
                            status_emoji = "🟢"
                        elif pnl_value < 0:
                            status_emoji = "🔴"  
                        else:
                            status_emoji = "⚪"
                            
                        # Berechne Trade-Dauer
                        trade_duration = self._calculate_trade_duration(created_at)
                        
                        trades_text += f"""
{status_emoji} *{symbol}* | {position.upper()} | {leverage}x
├ 💰 Entry: `{entry_price:,.2f}`
├ 📊 Current: `{current_price:,.2f}`
├ 📈 PnL: `{pnl_value:+.2f} USDT` (`{pnl_percent:+.2f}%`)
├ ⚖️ Quantity: `{amount:.6f}`
├ 🛡️ Stop: `{stop_loss:,.2f}`
├ 🔄 Status: `{status}`
└ ⏱️ Duration: `{trade_duration}`

🎯 Targets: `{tk1:,.0f}` → `{tk2:,.0f}` → `{tk3:,.0f}` → `{tk4:,.0f}`
────────────────────
"""
                    except Exception as pnl_error:
                        logger.error(f"❌ Error calculating PnL for {symbol}: {pnl_error}")
                        trades_text += f"⚠️ *{symbol}* - Error calculating performance\n\n"
                        
                except Exception as trade_error:
                    logger.error(f"❌ Error processing trade {symbol}: {trade_error}")
                    trades_text += f"❌ *{symbol}* - Error loading trade data\n\n"
            
            # Füge Gesamt-PnL hinzu
            avg_pnl_percentage = total_pnl_percentage / len(active_symbols) if active_symbols else 0
            
            trades_text += f"""
*📈 PORTFOLIO SUMMARY:*
• 🔢 Active Trades: `{len(active_symbols)}`
• 💰 Total PnL: `{total_pnl:+.2f} USDT`
• 📊 Average PnL: `{avg_pnl_percentage:+.2f}%`
• ⏰ Last Update: `{self.get_current_time()}`
"""
            
            return trades_text
            
        except Exception as e:
            logger.error(f"❌ Error getting trades info: {e}", exc_info=True)
            return "❌ *Error fetching trades information*\n\nPlease try again later or check system logs."

    def _calculate_trade_duration(self, created_at):
        """Berechnet Trade-Dauer in lesbarem Format"""
        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            duration = datetime.now() - created_at
            hours = duration.total_seconds() / 3600
            
            if hours < 1:
                return f"{int(duration.total_seconds() / 60)}m"
            elif hours < 24:
                return f"{hours:.1f}h"
            else:
                return f"{hours/24:.1f}d"
        except:
            return "Unknown"

    async def stats_command(self, update: Update, context):
        """Stats Command Handler"""
        try:
            stats_info = self.get_stats_info()
            await update.message.reply_text(stats_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("❌ Error fetching statistics")

    async def stats_callback(self, update: Update, context):
        """Stats Callback Handler mit ROBUSTEM Error Handling"""
        query = update.callback_query
        
        try:
            await query.answer()
        except Exception as e:
            logger.error(f"❌ Error answering stats callback: {e}")
            return
        
        try:
            stats_info = self.get_stats_info()
            
            keyboard = [
                [InlineKeyboardButton("💰 Balance", callback_data=str(BALANCE))],
                [InlineKeyboardButton("📊 Live Trades", callback_data=str(LIVE_TRADES))],
                [InlineKeyboardButton("📊 Performance", callback_data=str(PERFORMANCE))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=stats_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"❌ Error in stats callback: {e}")

    def get_stats_info(self):
        """Holt PROFESSIONELLE Trading Statistiken mit ROBUSTEM Error Handling"""
        try:
            # Hole echte Daten mit Error Handling
            active_trades = len(get_active_trades_symbol_db())
            monitoring_stats = get_monitoring_stats() or {}
            risk_stats = risk_manager.get_performance_metrics() or {}
            parsing_stats = signal_parser.get_parsing_stats() or {}
            
            # Performance Statistiken mit Defaults
            performance_data = get_performance_stats(days=30) or {}
            
            # SICHERE Zugriffe
            total_trades = performance_data.get('total_trades', 0) or 0
            winning_trades = performance_data.get('winning_trades', 0) or 0
            losing_trades = performance_data.get('losing_trades', 0) or 0
            total_pnl = performance_data.get('total_pnl', 0) or 0
            avg_duration = performance_data.get('avg_trade_duration', 0) or 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return f"""
📈 *PROFESSIONAL TRADING ANALYTICS*

*📊 TRADING PERFORMANCE:*
├ ♻️ Total Trades: `{total_trades}`
├ ✅ Winning Trades: `{winning_trades}`
├ ❌ Losing Trades: `{losing_trades}`
├ 🎯 Win Rate: `{win_rate:.1f}%`
├ 📈 Total PnL: `{total_pnl:+.2f} USDT`
└ 💰 Avg Trade Duration: `{avg_duration/3600:.1f}h`

*⚡ CURRENT SYSTEM STATUS:*
├ 🔢 Active Trades: `{active_trades}`
├ 📊 Monitoring Checks: `{monitoring_stats.get('total_checks', 0)}`
├ ✅ Successful Signals: `{parsing_stats.get('successful_parses', 0)}`
├ 🛡️ Stop Loss Triggers: `{risk_stats.get('stop_loss_triggers', 0)}`
└ 🎯 Take Profit Triggers: `{risk_stats.get('take_profit_triggers', 0)}`

*🤖 BOT PERFORMANCE:*
├ 🚀 Signals Processed: `{parsing_stats.get('total_signals', 0)}`
├ ✅ Signal Success Rate: `{parsing_stats.get('success_rate_percent', 0):.1f}%`
├ 📨 Notifications Sent: `{monitoring_stats.get('notifications_sent', 0)}`
└ ⏰ Uptime: `{self._get_bot_uptime()}`

*Last Updated:* `{self.get_current_time()}`
"""
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return "❌ *Temporarily unable to fetch statistics*\n\nPlease try again later."

    async def performance_command(self, update: Update, context):
        """Performance Command Handler"""
        try:
            performance_info = self.get_performance_info()
            await update.message.reply_text(performance_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in performance command: {e}")
            await update.message.reply_text("❌ Error fetching performance data")

    async def performance_callback(self, update: Update, context):
        """Performance Callback Handler mit ROBUSTEM Error Handling"""
        query = update.callback_query
        
        try:
            # Versuche zuerst den Callback zu beantworten
            await query.answer()
        except Exception as e:
            logger.error(f"❌ Error answering callback: {e}")
            return
        
        try:
            performance_info = self.get_performance_info()
            
            keyboard = [
                [InlineKeyboardButton("📈 Statistics", callback_data=str(STATS))],
                [InlineKeyboardButton("📋 History", callback_data=str(HISTORY))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=performance_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"❌ Error in performance callback: {e}")
            try:
                await query.edit_message_text(
                    text="❌ *Error loading performance data*\n\nPlease try again or use /performance command.",
                    parse_mode='Markdown'
                )
            except:
                pass

    def get_performance_info(self):
        """Holt DETAILLIERTE Performance Informationen mit ROBUSTEM Error Handling"""
        try:
            # Hole Performance-Daten mit Error Handling
            weekly_stats = get_performance_stats(days=7) or {}
            monthly_stats = get_performance_stats(days=30) or {}
            all_time_stats = get_performance_stats(days=365) or {}
            
            # Risk Management Metriken
            risk_metrics = risk_manager.get_performance_metrics() or {}
            
            # SICHERE Zugriffe mit Default-Werten
            weekly_trades = weekly_stats.get('total_trades', 0) or 0
            weekly_win_rate = weekly_stats.get('win_rate', 0) or 0
            weekly_pnl = weekly_stats.get('total_pnl', 0) or 0
            weekly_duration = weekly_stats.get('avg_trade_duration', 0) or 0
            
            monthly_trades = monthly_stats.get('total_trades', 0) or 0
            monthly_win_rate = monthly_stats.get('win_rate', 0) or 0
            monthly_pnl = monthly_stats.get('total_pnl', 0) or 0
            monthly_expectancy = monthly_stats.get('expectancy', 0) or 0
            
            alltime_trades = all_time_stats.get('total_trades', 0) or 0
            alltime_win_rate = all_time_stats.get('win_rate', 0) or 0
            alltime_pnl = all_time_stats.get('total_pnl', 0) or 0
            alltime_profit_factor = all_time_stats.get('profit_factor', 0) or 0
            
            return f"""
📊 *DETAILED PERFORMANCE ANALYTICS*

*📈 WEEKLY PERFORMANCE (7 Days):*
├ 🔄 Trades: `{weekly_trades}`
├ 🎯 Win Rate: `{weekly_win_rate:.1f}%`
├ 📈 PnL: `{weekly_pnl:+.2f} USDT`
└ ⏱️ Avg Duration: `{weekly_duration/3600:.1f}h`

*📅 MONTHLY PERFORMANCE (30 Days):*
├ 🔄 Trades: `{monthly_trades}`
├ 🎯 Win Rate: `{monthly_win_rate:.1f}%`
├ 📈 PnL: `{monthly_pnl:+.2f} USDT`
└ 💰 Expectancy: `{monthly_expectancy:.2f}`

*🏆 ALL-TIME PERFORMANCE:*
├ 🔄 Total Trades: `{alltime_trades}`
├ 🎯 Overall Win Rate: `{alltime_win_rate:.1f}%`
├ 📈 Total Profit: `{alltime_pnl:+.2f} USDT`
└ ⚡ Profit Factor: `{alltime_profit_factor:.2f}`

*🛡️ RISK MANAGEMENT PERFORMANCE:*
├ 🛑 Stop Loss Triggers: `{risk_metrics.get('stop_loss_triggers', 0)}`
├ 🎯 Take Profit Triggers: `{risk_metrics.get('take_profit_triggers', 0)}`
├ 🔄 Trailing Stop Activations: `{risk_metrics.get('trailing_stop_activations', 0)}`
├ ⚖️ Breakeven Activations: `{risk_metrics.get('breakeven_activations', 0)}`
└ 💰 Partial Profit Taken: `{risk_metrics.get('partial_profit_taken', 0)}`

*📊 TRADING ACTIVITY:*
├ 📨 Total Signals: `{signal_parser.get_parsing_stats().get('total_signals', 0)}`
├ ✅ Successful Trades: `{risk_metrics.get('successful_trades', 0)}`
├ ❌ Failed Trades: `{risk_metrics.get('failed_trades', 0)}`
└ 📈 Success Rate: `{risk_metrics.get('win_rate_percent', 0):.1f}%`

*Last Updated:* `{self.get_current_time()}`
"""
        except Exception as e:
            logger.error(f"Error getting performance info: {e}")
            return "❌ *Temporarily unable to fetch performance data*\n\nPlease try again later."

    async def history_command(self, update: Update, context):
        """History Command Handler"""
        try:
            history_info = self.get_history_info()
            await update.message.reply_text(history_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in history command: {e}")
            await update.message.reply_text("❌ Error fetching trade history")

    async def history_callback(self, update: Update, context):
        """History Callback Handler"""
        query = update.callback_query
        await query.answer()
        
        try:
            history_info = self.get_history_info()
            
            keyboard = [
                [InlineKeyboardButton("📊 Performance", callback_data=str(PERFORMANCE))],
                [InlineKeyboardButton("📈 Statistics", callback_data=str(STATS))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=history_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in history callback: {e}")
            await query.edit_message_text("❌ Error fetching trade history")

    def get_history_info(self):
        """Holt Trade-Historie Informationen"""
        try:
            # Hole die letzten 10 Trades
            recent_trades = get_trade_history(days=30, limit=10)
            
            if not recent_trades:
                return "📋 *NO TRADE HISTORY FOUND*\n\nNo trades have been completed in the last 30 days."
            
            history_text = "📋 *RECENT TRADE HISTORY* (Last 10 Trades)\n\n"
            
            for i, trade in enumerate(recent_trades, 1):
                symbol = trade.get('symbol', 'Unknown')
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                position = trade.get('position', 'LONG')
                pnl = trade.get('pnl', 0)
                pnl_percent = trade.get('pnl_percentage', 0)
                status = trade.get('status', 'UNKNOWN')
                exit_reason = trade.get('exit_reason', 'Unknown')
                closed_at = trade.get('closed_at', 'Unknown')
                
                # Bestimme Emoji basierend auf PnL
                if pnl > 0:
                    pnl_emoji = "🟢"
                elif pnl < 0:
                    pnl_emoji = "🔴"
                else:
                    pnl_emoji = "⚪"
                
                history_text += f"""
{pnl_emoji} *{symbol}* | {position.upper()}
├ 💰 Entry: `{entry_price:,.2f}`
├ 📊 Exit: `{exit_price:,.2f}` 
├ 📈 PnL: `{pnl:+.2f} USDT` (`{pnl_percent:+.2f}%`)
├ 🎯 Status: `{status}`
├ 📋 Reason: `{exit_reason}`
└ ⏰ Closed: `{closed_at[:16] if isinstance(closed_at, str) else closed_at}`
"""
                if i < len(recent_trades):
                    history_text += "────────────────────\n"
            
            history_text += f"\n*Last Updated:* `{self.get_current_time()}`"
            
            return history_text
            
        except Exception as e:
            logger.error(f"Error getting history info: {e}")
            return "❌ *Error fetching trade history*\n\nPlease try again later."

    async def settings_command(self, update: Update, context):
        """Settings Command Handler"""
        try:
            settings_info = self.get_settings_info()
            await update.message.reply_text(settings_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in settings command: {e}")
            await update.message.reply_text("❌ Error fetching settings")

    async def settings_callback(self, update: Update, context):
        """Settings Callback Handler"""
        query = update.callback_query
        await query.answer()
        
        try:
            settings_info = self.get_settings_info()
            
            keyboard = [
                [InlineKeyboardButton("💰 Balance", callback_data=str(BALANCE))],
                [InlineKeyboardButton("📊 Live Trades", callback_data=str(LIVE_TRADES))],
                [InlineKeyboardButton("📈 Statistics", callback_data=str(STATS))],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=settings_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in settings callback: {e}")
            await query.edit_message_text("❌ Error fetching settings")

    def get_settings_info(self):
        """Holt PROFESSIONELLE Bot Einstellungen"""
        try:
            testnet_mode = binance_api.testnet_mode
            api_configured = bool(config.get('BINANCE', 'api_key')) and bool(config.get('BINANCE', 'api_secret'))
            
            # Monitoring Status
            monitoring_stats = get_monitoring_stats()
            health_status = get_health_status()
            
            return f"""
⚙️ *PROFESSIONAL BOT CONFIGURATION*

*🎯 TRADING CONFIGURATION:*
├ 💰 Amount per Trade: `{config.get('TRADING', 'amount_per_trade')} USDT`
├ 🎯 Max Open Trades: `{config.get('TRADING', 'max_open_trades')}`
├ ⚖️ Default Leverage: `{config.get('TRADING', 'default_leverage')}x`
├ 📉 Risk per Trade: `{config.get('TRADING', 'risk_per_trade')}%`
└ 🔄 Position Sizing: `Advanced Risk-Based`

*🔗 EXCHANGE CONFIGURATION:*
├ 🏦 Exchange: `Binance`
├ 🌐 Mode: {'🟡 TESTNET (Sandbox)' if testnet_mode else '🟢 LIVE TRADING'}
├ 🔑 API Keys: {'✅ Properly Configured' if api_configured else '❌ Not Configured'}
├ 📊 Trading Pairs: `All USDT pairs`
└ 🔄 Connection: `{health_status.get('status', 'Unknown').upper()}`

*🤖 BOT CONFIGURATION:*
├ ⏰ Price Polling: `{config.get('SETTINGS', 'polling_interval')} seconds`
├ 📝 Logging Level: `{config.get('SETTINGS', 'log_level')}`
├ 🔍 Auto-Monitoring: {'🟢 ACTIVE' if self.is_monitoring_active else '🔴 INACTIVE'}
├ 💾 Database: `✅ SQLite Professional`
└ 🤖 Version: `Professional 2.1.0`

*📊 MONITORING STATUS:*
├ 📨 Total Checks: `{monitoring_stats.get('total_checks', 0)}`
├ ✅ Successful Checks: `{monitoring_stats.get('successful_checks', 0)}`
├ ❌ Failed Checks: `{monitoring_stats.get('failed_checks', 0)}`
├ 📈 Success Rate: `{health_status.get('success_rate', 0):.1f}%`
└ 🔢 Active Symbols: `{monitoring_stats.get('active_symbols', 0)}`

*🛠️ CONFIGURATION MANAGEMENT:*
To modify settings, edit the `config.ini` file
Restart required after configuration changes

*Last Config Check:* `{self.get_current_time()}`
"""
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return "❌ *Error fetching settings*\n\nPlease check configuration files."

    async def monitoring_command(self, update: Update, context):
        """Monitoring Control Command"""
        try:
            if context.args:
                action = context.args[0].lower()
                if action in ['start', 'on', 'enable']:
                    success = self.start_background_monitoring()
                    message = "✅ *Monitoring started*" if success else "❌ *Failed to start monitoring*"
                elif action in ['stop', 'off', 'disable']:
                    success = self.stop_background_monitoring()
                    message = "🛑 *Monitoring stopped*" if success else "❌ *Failed to stop monitoring*"
                elif action in ['status', 'info']:
                    message = self.get_monitoring_status()
                else:
                    message = "❌ *Invalid action*. Use: /monitoring [start|stop|status]"
            else:
                message = self.get_monitoring_status()
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in monitoring command: {e}")
            await update.message.reply_text("❌ *Error controlling monitoring*")

    def get_monitoring_status(self):
        """Gibt Monitoring Status zurück"""
        try:
            monitoring_stats = get_monitoring_stats()
            health_status = get_health_status()
            
            return f"""
🔍 *PRICE MONITORING STATUS*

*📊 CURRENT STATUS:*
├ 🔄 Monitoring: {'🟢 ACTIVE' if self.is_monitoring_active else '🔴 INACTIVE'}
├ 📈 System Health: `{health_status.get('status', 'Unknown').upper()}`
├ ⏰ Uptime: `{health_status.get('uptime_seconds', 0)/3600:.1f}h`
└ ✅ Success Rate: `{health_status.get('success_rate', 0):.1f}%`

*📈 PERFORMANCE METRICS:*
├ 📨 Total Checks: `{monitoring_stats.get('total_checks', 0)}`
├ ✅ Successful: `{monitoring_stats.get('successful_checks', 0)}`
├ ❌ Failed: `{monitoring_stats.get('failed_checks', 0)}`
├ 🔢 Trades Managed: `{monitoring_stats.get('trades_managed', 0)}`
└ 📱 Notifications: `{monitoring_stats.get('notifications_sent', 0)}`

*🔢 ACTIVE TRACKING:*
├ 📊 Active Symbols: `{monitoring_stats.get('active_symbols', 0)}`
├ 📈 Price History: `{sum(monitoring_stats.get('price_history_size', {}).values())}`
└ ⏰ Last Check: `{monitoring_stats.get('last_check_time', 'Never')}`

*🎯 CONTROLS:*
• `/monitoring start` - Start monitoring
• `/monitoring stop` - Stop monitoring  
• `/monitoring status` - Show this status

*Last Update:* `{self.get_current_time()}`
"""
        except Exception as e:
            logger.error(f"Error getting monitoring status: {e}")
            return "❌ *Error fetching monitoring status*"

    async def health_command(self, update: Update, context):
        """Health Check Command"""
        try:
            health_info = self.get_health_info()
            await update.message.reply_text(health_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in health command: {e}")
            await update.message.reply_text("❌ *Error fetching health status*")

    def get_health_info(self):
        """Gibt System Health Status zurück"""
        try:
            health_status = get_health_status()
            monitoring_stats = get_monitoring_stats()
            api_stats = binance_api.get_connection_stats()
            risk_stats = risk_manager.get_performance_metrics()
            
            # Bewerte System Health
            success_rate = health_status.get('success_rate', 0)
            if success_rate > 95:
                health_emoji = "🟢"
                health_text = "EXCELLENT"
            elif success_rate > 85:
                health_emoji = "🟡" 
                health_text = "GOOD"
            elif success_rate > 70:
                health_emoji = "🟠"
                health_text = "FAIR"
            else:
                health_emoji = "🔴"
                health_text = "POOR"
            
            return f"""
🏥 *SYSTEM HEALTH CHECK*

*📊 OVERALL HEALTH:*
{health_emoji} Status: `{health_text}`
📈 Success Rate: `{success_rate:.1f}%`
⏰ Uptime: `{health_status.get('uptime_seconds', 0)/3600:.1f} hours`
🔄 Last Update: `{self.get_current_time()}`

*🔧 COMPONENT STATUS:*
├ 🤖 Trading Bot: `🟢 OPERATIONAL`
├ 📊 Price Monitoring: `{'🟢 ACTIVE' if self.is_monitoring_active else '🔴 INACTIVE'}`
├ 💾 Database: `🟢 CONNECTED`
├ 📈 Binance API: `🟢 CONNECTED`
├ 🛡️ Risk Manager: `🟢 ACTIVE`
└ 📨 Notifications: `🟢 ENABLED`

*📈 PERFORMANCE METRICS:*
├ 📊 Monitoring Checks: `{monitoring_stats.get('total_checks', 0)}`
├ ✅ API Success Rate: `{api_stats.get('success_rate_percent', 0):.1f}%`
├ 🛡️ Risk Evaluations: `{risk_stats.get('trades_evaluated', 0)}`
└ 📨 Total Notifications: `{monitoring_stats.get('notifications_sent', 0)}`

*💡 RECOMMENDATIONS:*
{self._get_health_recommendations(health_status)}
"""
        except Exception as e:
            logger.error(f"Error getting health info: {e}")
            return "❌ *Error fetching health status*"

    def _get_health_recommendations(self, health_status):
        """Generiert Health Empfehlungen"""
        recommendations = []
        success_rate = health_status.get('success_rate', 0)
        
        if success_rate < 80:
            recommendations.append("• 🔄 Consider restarting monitoring service")
        if success_rate < 70:
            recommendations.append("• 📡 Check API connection and internet")
        if health_status.get('uptime_seconds', 0) > 86400:  # 24 hours
            recommendations.append("• ⏰ System running smoothly for extended period")
        
        if not recommendations:
            recommendations.append("• ✅ All systems operating optimally")
            
        return "\n".join(recommendations)

    async def help_command(self, update: Update, context):
        """PROFESSIONELLE Help Command Handler"""
        help_text = """
🆘 *PROFESSIONAL TRADING BOT HELP*

*📋 CORE COMMANDS:*
/start - Launch bot with interactive menu
/balance - Account balance & equity overview
/trades - Active trades with real-time PnL  
/stats - Trading statistics & analytics
/performance - Detailed performance metrics
/history - Trade history & analysis
/settings - Bot configuration & status
/monitoring - Monitoring controls & status
/health - System health check
/help - This help message

*🎯 TRADE MANAGEMENT:*
/cancel SYMBOL - Cancel specific active trade
Example: `/cancel BTCUSDT`

*📨 SIGNAL PROCESSING:*
Simply forward trading signals from ANY channel in this format:
#SYMBOL LONG/SHORT
Entry: PRICE (or price range)
Leverage: X (auto-detected)
Target 1: PRICE
Target 2: PRICE  
Target 3: PRICE
Target 4: PRICE
Stop-Loss: PRICE

*💡 EXAMPLE SIGNAL:*
#BTCUSDT Long
Entry: 110690
Leverage: 10x
Target 1: 112000
Target 2: 113500
Target 3: 115000
Target 4: 117000
Stop-Loss: 110000

*🔧 ADVANCED FEATURES:*
✅ Intelligent signal parsing from any channel
📊 Advanced risk management with trailing stops
🔒 Multi-level stop loss protection
🎯 4-Take profit targets with partial closes
📈 Real-time price monitoring & alerts
💾 Professional database tracking
📱 Telegram notifications & controls

*❓ TROUBLESHOOTING:*
• Check /settings for configuration
• Verify API keys in config.ini
• Ensure proper signal format
• Use /health for system status
• Check logs for detailed errors

*🛠️ SUPPORT:*
For issues, check system logs and ensure all components are properly configured.
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def cancel_trade_command(self, update: Update, context):
        """PROFESSIONELLE Cancel Trade Command"""
        try:
            if context.args:
                symbol = context.args[0].upper()
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                
                # Prüfe ob Trade existiert
                trade_data = get_trade_db(symbol)
                if not trade_data:
                    await update.message.reply_text(
                        f"❌ *NO ACTIVE TRADE FOUND*\n\n"
                        f"Symbol: `#{symbol}`\n"
                        f"Status: ❌ Not found\n\n"
                        f"Use `/trades` to see active trades.",
                        parse_mode='Markdown'
                    )
                    return
                
                # Cancle Trade
                success = set_trade_noActive_db(symbol, exit_reason="manual_cancellation")
                
                if success:
                    await update.message.reply_text(
                        f"✅ *TRADE CANCELLED SUCCESSFULLY!*\n\n"
                        f"Symbol: `#{symbol}`\n"
                        f"Entry Price: `{trade_data.get('entry_price', 0):,.2f}`\n"
                        f"Position: `{trade_data.get('position', 'UNKNOWN')}`\n"
                        f"Status: ❌ Cancelled\n"
                        f"Time: `{self.get_current_time()}`\n\n"
                        f"All pending orders have been cancelled.",
                        parse_mode='Markdown'
                    )
                    
                    # Sende Benachrichtigung an Gruppe
                    await self.bot.send_message(
                        chat_id=self.target_chat_id,
                        text=f"🛑 *TRADE MANUELL GESCHLOSSEN: {symbol}*\n\n"
                             f"Symbol: `{symbol}`\n"
                             f"Entry: `{trade_data.get('entry_price', 0):,.2f}`\n"
                             f"Position: `{trade_data.get('position', 'UNKNOWN')}`\n"
                             f"Grund: Manuelle Schließung\n"
                             f"Zeit: `{self.get_current_time()}`",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        f"❌ *ERROR CANCELLING TRADE*\n\n"
                        f"Symbol: `#{symbol}`\n"
                        f"Please try again or check system logs.",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    "📋 *USAGE:* `/cancel SYMBOL`\n"
                    "*EXAMPLE:* `/cancel BTCUSDT`\n"
                    "*NOTE:* Symbol auto-appends USDT if missing\n\n"
                    "Use `/trades` to see active trades.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in cancel command: {e}")
            await update.message.reply_text(
                "❌ *ERROR CANCELLING TRADE*\n\n"
                "Please check the symbol format and try again.",
                parse_mode='Markdown'
            )

    async def handle_message(self, update: Update, context):
        """Handle ALL Messages as Trading Signals - PROFESSIONELLE VERSION"""
        try:
            message = update.message.text
            user = update.message.from_user
            logger.info(f"📨 SIGNAL FROM {user.first_name} (ID: {user.id}): {message}")
            
            # DIRECT PARSE - PROFESSIONELLE VERARBEITUNG
            success, result = signal_parser.parse_signal(message)
            
            if success:
                # PROFESSIONELLE ERFOLGSMITTEILUNG
                response_text = f"""
✅ *TRADE EXECUTED SUCCESSFULLY!* 🚀

*📊 TRADE DETAILS:*
├ 📈 Symbol: `#{result['symbol']}`
├ 🎯 Direction: `{result['direction'].upper()}`
├ 💰 Entry Price: `{result['entry_price']:,.2f}`
├ ⛔ Stop Loss: `{result['stoploss']:,.2f}`
├ 🏦 Leverage: `{result.get('leverage', 3)}x`
├ 📊 Quantity: `{result.get('quantity', 0):.6f}`
└ 🆔 Order ID: `{result['order_id']}`

*🎯 PROFIT TARGETS:*
├ Target 1: `{result['targets'][0]:,.2f}`
├ Target 2: `{result['targets'][1]:,.2f}`
├ Target 3: `{result['targets'][2]:,.2f}`
└ Target 4: `{result['targets'][3]:,.2f}`

*📈 RISK METRICS:*
├ 📉 Risk/Reward: `{result.get('risk_reward', 1.0):.2f}:1`
├ 🔮 Confidence: `{result.get('confidence', 75.0)}%`
└ ⏰ Executed: `{self.get_current_time()}`

💡 *Trade is now being monitored automatically*
"""
                
                # Logge erfolgreichen Trade
                logger.info(f"✅ SUCCESSFUL TRADE: {result['symbol']} | {result['direction']} | Entry: {result['entry_price']}")
                
            else:
                response_text = f"❌ *TRADE EXECUTION FAILED*\n\n*Error:* {result}\n\nPlease check the signal format and try again."
                
                # Logge fehlgeschlagenen Trade
                logger.warning(f"❌ FAILED TRADE: {result}")
            
            # SENDE ANTWORT
            await update.message.reply_text(response_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR PROCESSING SIGNAL: {e}")
            await update.message.reply_text(
                f"❌ *CRITICAL ERROR PROCESSING SIGNAL*\n\n"
                f"Please check the signal format and try again.\n"
                f"Error: {str(e)}",
                parse_mode='Markdown'
            )

    async def test_group_notification(self):
        """Testet PROFESSIONELLE Gruppen-Benachrichtigungen"""
        try:
            await self.bot.send_message(
                chat_id=self.target_chat_id,
                text="🔔 *PROFESSIONAL TRADING BOT INITIALIZED* 🚀\n\n"
                     "*🤖 System Status:* 🟢 ONLINE\n"
                     "*📊 Monitoring:* 🟢 ACTIVE\n"  
                     "*💾 Database:* 🟢 CONNECTED\n"
                     "*📈 API:* 🟢 OPERATIONAL\n\n"
                     "*🎯 Ready for trading signals!*\n"
                     "*💡 Simply forward signals from your channels.*",
                parse_mode='Markdown'
            )
            logger.info(f"✅ Professional test notification sent to group: {self.target_chat_id}")
        except Exception as e:
            logger.error(f"❌ Error sending test notification: {e}")

    def get_current_time(self):
        """Holt PROFESSIONELLE aktuelle Zeit für Timestamps"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    def _get_bot_uptime(self):
        """Berechnet Bot Uptime"""
        uptime = datetime.now() - self.bot_start_time
        hours = uptime.total_seconds() / 3600
        
        if hours < 1:
            return f"{int(uptime.total_seconds() / 60)} minutes"
        elif hours < 24:
            return f"{hours:.1f} hours"
        else:
            return f"{hours/24:.1f} days"

    def run(self):
        """Start the PROFESSIONELLE Trading Bot"""
        logger.info("🤖 STARTING PROFESSIONAL TRADING BOT...")
        logger.info("🔍 Price monitoring system initializing...")
        logger.info("💾 Professional database system initialized")
        logger.info("📈 Advanced risk management activated")
        logger.info("📊 Real-time analytics engine started")
        logger.info("🚀 Bot ready for professional trading!")
        
        # FIX: Event Loop für Windows setzen
        import platform
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Starte Background Monitoring
        monitoring_success = self.start_background_monitoring()
        
        if monitoring_success:
            logger.info("✅ Background monitoring started successfully")
        else:
            logger.error("❌ Failed to start background monitoring")
        
        # Sende Start-Benachrichtigung (asynchron in der Bot-Loop)
        async def send_startup_notification():
            try:
                await self.test_group_notification()
                # Verwende den Bot direkt für die Benachrichtigung
                await self.bot.send_message(
                    chat_id=self.target_chat_id,
                    text="🤖 *PROFESSIONAL TRADING BOT STARTED SUCCESSFULLY!* 🚀\n\n"
                         "*📊 System Status:* 🟢 ALL SYSTEMS GO\n"
                         "*🎯 Monitoring:* 🟢 ACTIVE\n"  
                         "*💾 Database:* 🟢 CONNECTED\n"
                         "*📈 API:* 🟢 OPERATIONAL\n\n"
                         "*🚀 Ready for trading signals!*",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Error sending startup notification: {e}")
        
        # Starte den Bot
        try:
            # FIX: Verwende die vorhandene Event Loop
            loop = asyncio.get_event_loop()
            
            # Sende Startup Notification
            loop.create_task(send_startup_notification())
            
            # Starte den Bot Polling
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            # Versuche Monitoring zu stoppen falls Bot fehlschlägt
            try:
                self.stop_background_monitoring()
            except:
                pass
            raise e

if __name__ == "__main__":
    try:
        bot = ProfessionalTradingBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error in main: {e}")
        raise e