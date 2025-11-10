import sqlite3
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager
import os
import time

logger = logging.getLogger(__name__)

class AdvancedDatabaseManager:
    def __init__(self, db_path='trading_bot.db'):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._connection_pool = {}
        self.max_pool_size = 5
        self.init_database()
    
    @contextmanager
    def _get_connection(self):
        """Thread-safe database connection context manager mit Connection Pooling - KORRIGIERT"""
        conn = None
        thread_id = threading.get_ident()
        
        try:
            with self._lock:
                # Versuche vorhandene Connection aus Pool zu verwenden
                if thread_id in self._connection_pool:
                    conn = self._connection_pool[thread_id]
                    try:
                        # Prüfe ob Connection noch gültig ist
                        conn.execute("SELECT 1")
                    except sqlite3.Error:
                        # Connection ist ungültig, entferne aus Pool
                        try:
                            conn.close()
                        except:
                            pass
                        del self._connection_pool[thread_id]
                        conn = None
                
                # Erstelle neue Connection falls nötig
                if conn is None:
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA synchronous = NORMAL")
                    conn.execute("PRAGMA cache_size = -64000")
                    
                    # Füge zur Pool hinzu wenn Platz vorhanden
                    if len(self._connection_pool) < self.max_pool_size:
                        self._connection_pool[thread_id] = conn
            
            yield conn
            conn.commit()
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            # Connection bleibt im Pool für Wiederverwendung
            # Nur schließen wenn außerhalb des Pools
            pass
    
    def _cleanup_connection_pool(self):
        """Bereinigt alte Connections aus dem Pool"""
        with self._lock:
            current_time = time.time()
            threads_to_remove = []
            
            for thread_id, conn in self._connection_pool.items():
                try:
                    # Prüfe ob Thread noch aktiv
                    if not threading._active.get(thread_id):
                        threads_to_remove.append(thread_id)
                    else:
                        # Prüfe Connection Health
                        conn.execute("SELECT 1")
                except:
                    threads_to_remove.append(thread_id)
            
            for thread_id in threads_to_remove:
                try:
                    self._connection_pool[thread_id].close()
                except:
                    pass
                del self._connection_pool[thread_id]
    
    def init_database(self):
        """Initialisiert die Datenbank mit PROFESSIONELLEN erweiterten Tabellen"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Tabelle für aktive Trades mit VOLLSTÄNDIGEN Feldern
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        leverage REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        position TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        stop_loss REAL NOT NULL,
                        take_profit_1 REAL NOT NULL,
                        take_profit_2 REAL NOT NULL,
                        take_profit_3 REAL NOT NULL,
                        take_profit_4 REAL NOT NULL,
                        active INTEGER DEFAULT 1,
                        status TEXT DEFAULT 'NEW',
                        order_ids TEXT,
                        risk_amount REAL DEFAULT 0,
                        current_pnl REAL DEFAULT 0,
                        pnl_percentage REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confidence REAL DEFAULT 75.0,
                        risk_reward_ratio REAL DEFAULT 1.0,
                        signal_source TEXT DEFAULT 'TELEGRAM',
                        UNIQUE(symbol, active)  -- Prevent duplicate active trades
                    )
                ''')
                
                # Tabelle für Trade-Historie/Archiv mit erweiterten Feldern
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trade_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_trade_id INTEGER,
                        symbol TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        position TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        leverage REAL NOT NULL,
                        pnl REAL DEFAULT 0,
                        pnl_percentage REAL DEFAULT 0,
                        status TEXT NOT NULL,
                        exit_reason TEXT,
                        trade_duration_seconds INTEGER,
                        confidence REAL DEFAULT 75.0,
                        risk_reward_ratio REAL DEFAULT 1.0,
                        created_at TIMESTAMP,
                        closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (original_trade_id) REFERENCES trades (id) ON DELETE SET NULL
                    )
                ''')
                
                # Tabelle für Performance-Metriken mit täglichen Aggregationen
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_date DATE UNIQUE,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0,
                        win_rate REAL DEFAULT 0,
                        avg_win REAL DEFAULT 0,
                        avg_loss REAL DEFAULT 0,
                        largest_win REAL DEFAULT 0,
                        largest_loss REAL DEFAULT 0,
                        avg_trade_duration INTEGER DEFAULT 0,
                        sharpe_ratio REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabelle für System-Logs und Auditing
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        log_level TEXT NOT NULL,
                        module TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # PROFESSIONELLE Indexe für optimale Performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol_active ON trades(symbol, active)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_symbol ON trade_history(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_closed_at ON trade_history(closed_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_pnl ON trade_history(pnl)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_date ON performance_metrics(metric_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at)')
                
                conn.commit()
                logger.info("✅ Database initialized successfully with PROFESSIONAL features")
                
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
            raise
    
    def new_trade_db(self, date: str, symbol: str, leverage: float, price: float, 
                    positionSide: str, qty: float, stoploss: float, 
                    tk1: float, tk2: float, tk3: float, tk4: float, ordersID: str,
                    risk_amount: float = 0, confidence: float = 75.0, 
                    risk_reward: float = 1.0) -> bool:
        """Speichert neuen Trade in der Datenbank mit VOLLSTÄNDIGEN erweiterten Daten - KORRIGIERT"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # PROFESSIONELLE Duplikat-Prüfung mit Lock
                cursor.execute('SELECT id FROM trades WHERE symbol = ? AND active = 1', (symbol.upper(),))
                if cursor.fetchone():
                    logger.warning(f"⚠️ Active trade already exists for {symbol}")
                    return False
                
                # KORRIGIERTER Insert mit allen Feldern
                cursor.execute('''
                    INSERT INTO trades 
                    (date, symbol, leverage, entry_price, position, quantity, stop_loss, 
                    take_profit_1, take_profit_2, take_profit_3, take_profit_4, 
                    order_ids, risk_amount, confidence, risk_reward_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date, symbol.upper(), leverage, price, positionSide, qty, stoploss, 
                    tk1, tk2, tk3, tk4, ordersID, risk_amount, confidence, risk_reward
                ))
                
                conn.commit()
                logger.info(f"✅ New trade saved: {symbol} | Leverage: {leverage}x | Risk: ${risk_amount:.2f}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"❌ Database error saving new trade {symbol}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error saving new trade {symbol}: {e}")
            return False
    
    def get_trade_db(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Holt Trade-Daten für ein Symbol als Dictionary - VOLLSTÄNDIG ROBUST"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT date, symbol, leverage, entry_price, position, quantity, 
                        stop_loss, take_profit_1, take_profit_2, take_profit_3, 
                        take_profit_4, active, status, order_ids, risk_amount,
                        current_pnl, pnl_percentage, confidence, risk_reward_ratio,
                        created_at, updated_at
                    FROM trades 
                    WHERE symbol = ? AND active = 1
                ''', (symbol.upper(),))
                
                row = cursor.fetchone()
                if row:
                    # Konvertiere sqlite3.Row zu Dictionary
                    trade_dict = dict(row)
                    
                    # VOLLSTÄNDIGE FELD-GARANTIE mit intelligenten Defaults
                    field_defaults = {
                        'date': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        'symbol': symbol.upper(),
                        'leverage': 1.0,
                        'entry_price': 0.0,
                        'position': 'LONG',
                        'quantity': 0.0,
                        'stop_loss': 0.0,
                        'take_profit_1': 0.0,
                        'take_profit_2': 0.0,
                        'take_profit_3': 0.0,
                        'take_profit_4': 0.0,
                        'active': 1,
                        'status': 'NEW',
                        'order_ids': '[]',
                        'risk_amount': 0.0,
                        'current_pnl': 0.0,
                        'pnl_percentage': 0.0,
                        'confidence': 75.0,
                        'risk_reward_ratio': 1.0,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    for field, default in field_defaults.items():
                        if field not in trade_dict or trade_dict[field] is None:
                            logger.warning(f"⚠️ Setting default for missing field {field} in {symbol}")
                            trade_dict[field] = default
                    
                    # PROFESSIONELLE Typ-Konvertierung
                    try:
                        if isinstance(trade_dict['order_ids'], str):
                            trade_dict['order_ids'] = json.loads(trade_dict['order_ids'])
                        else:
                            trade_dict['order_ids'] = []
                    except:
                        trade_dict['order_ids'] = []
                    
                    # Konvertiere Datum-Strings zu datetime Objects falls nötig
                    for date_field in ['created_at', 'updated_at']:
                        if date_field in trade_dict and isinstance(trade_dict[date_field], str):
                            try:
                                trade_dict[date_field] = datetime.fromisoformat(
                                    trade_dict[date_field].replace('Z', '+00:00')
                                )
                            except:
                                trade_dict[date_field] = datetime.now()
                    
                    logger.debug(f"✅ Successfully retrieved COMPLETE trade data for {symbol}")
                    return trade_dict
                else:
                    logger.warning(f"⚠️ No active trade found for symbol: {symbol}")
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"❌ Database error getting trade {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting trade {symbol}: {e}")
            return None

    def get_active_trades_symbol_db(self) -> List[str]:
        """Holt alle aktiven Trade-Symbole - OPTIMIERTE VERSION"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol FROM trades 
                    WHERE active = 1 
                    ORDER BY created_at DESC
                ''')
                
                rows = cursor.fetchall()
                symbols = [row['symbol'] for row in rows] if rows else []
                
                if symbols:
                    logger.info(f"🔍 Found {len(symbols)} active trades: {symbols}")
                else:
                    logger.debug("📭 No active trades found")
                    
                return symbols
                
        except Exception as e:
            logger.error(f"❌ Error getting active trades: {e}")
            return []
    
    def update_trade_status_db(self, symbol: str, new_status: str) -> bool:
        """Aktualisiert den Trade-Status mit Timestamp"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE trades 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND active = 1
                ''', (new_status, symbol.upper()))
                
                affected = cursor.rowcount
                conn.commit()
                
                if affected > 0:
                    logger.info(f"✅ Updated status for {symbol}: {new_status}")
                    return True
                else:
                    logger.warning(f"⚠️ No active trade found for {symbol} to update status")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error updating trade status for {symbol}: {e}")
            return False
    
    def set_trade_noActive_db(self, symbol: str, exit_price: float = None, 
                            exit_reason: str = None, pnl: float = 0, pnl_percentage: float = 0) -> bool:
        """Setzt Trade auf inaktiv und archiviert ihn - VOLLSTÄNDIG ROBUST"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Hole VOLLSTÄNDIGE Trade-Daten für Archivierung
                cursor.execute('''
                    SELECT id, date, symbol, leverage, entry_price, position, quantity, 
                           status, confidence, risk_reward_ratio, created_at
                    FROM trades WHERE symbol = ? AND active = 1
                ''', (symbol.upper(),))
                
                trade_data = cursor.fetchone()
                if not trade_data:
                    logger.warning(f"⚠️ No active trade found for {symbol}")
                    return False
                
                # Berechne Trade-Dauer
                trade_duration = 0
                try:
                    if isinstance(trade_data['created_at'], str):
                        created_at = datetime.fromisoformat(trade_data['created_at'].replace('Z', '+00:00'))
                    else:
                        created_at = trade_data['created_at']
                    trade_duration = int((datetime.now() - created_at).total_seconds())
                except:
                    trade_duration = 0
                
                # TRANSACTION START: Setze Trade auf inaktiv
                cursor.execute('''
                    UPDATE trades 
                    SET active = 0, updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND active = 1
                ''', (symbol.upper(),))
                
                # Archiviere Trade in Historie mit ALLEN Daten
                cursor.execute('''
                    INSERT INTO trade_history 
                    (original_trade_id, symbol, entry_price, exit_price, position, 
                     quantity, leverage, pnl, pnl_percentage, status, exit_reason,
                     trade_duration_seconds, confidence, risk_reward_ratio, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade_data['id'], trade_data['symbol'], trade_data['entry_price'], 
                    exit_price, trade_data['position'], trade_data['quantity'], 
                    trade_data['leverage'], pnl, pnl_percentage, trade_data['status'], 
                    exit_reason, trade_duration, trade_data.get('confidence', 75.0),
                    trade_data.get('risk_reward_ratio', 1.0), trade_data['date']
                ))
                
                conn.commit()
                logger.info(f"✅ Trade archived and deactivated: {symbol} | Reason: {exit_reason} | Duration: {trade_duration}s")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ Integrity error deactivating trade {symbol}: {e}")
            return self._fallback_deactivate_trade(symbol)
        except Exception as e:
            logger.error(f"❌ Error deactivating trade {symbol}: {e}")
            return self._fallback_deactivate_trade(symbol)
    
    def _fallback_deactivate_trade(self, symbol: str) -> bool:
        """Fallback für fehlgeschlagene Trade-Deaktivierung"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trades 
                    SET active = 0, updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND active = 1
                ''', (symbol.upper(),))
                conn.commit()
                logger.info(f"✅ Trade deactivated (fallback): {symbol}")
                return True
        except Exception as e2:
            logger.error(f"❌ Fallback also failed for {symbol}: {e2}")
            return False
    
    def update_trade_performance(self, symbol: str, current_pnl: float, pnl_percentage: float) -> bool:
        """Aktualisiert Performance-Daten eines Trades"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE trades 
                    SET current_pnl = ?, pnl_percentage = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND active = 1
                ''', (current_pnl, pnl_percentage, symbol.upper()))
                
                conn.commit()
                logger.debug(f"📈 Updated performance for {symbol}: PnL {current_pnl:.2f} ({pnl_percentage:.2f}%)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating trade performance for {symbol}: {e}")
            return False
    
    def update_trade_amount_db(self, symbol: str, amount: float) -> bool:
        """Aktualisiert Trade Amount"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE trades 
                    SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND active = 1
                ''', (amount, symbol.upper()))
                
                conn.commit()
                logger.info(f"✅ Updated quantity for {symbol}: {amount:.6f}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating trade amount for {symbol}: {e}")
            return False
    
    def update_trade_enteryprice_db(self, symbol: str, realPrice: float) -> bool:
        """Aktualisiert Entry Price"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE trades 
                    SET entry_price = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND active = 1
                ''', (realPrice, symbol.upper()))
                
                conn.commit()
                logger.info(f"✅ Updated entry price for {symbol}: {realPrice:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating entry price for {symbol}: {e}")
            return False
    
    def get_orders_id_db(self, symbol: str) -> List[str]:
        """Holt Order IDs für ein Symbol - ROBUST"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT order_ids FROM trades WHERE symbol = ? AND active = 1', (symbol.upper(),))
                result = cursor.fetchone()
                
                if result and result['order_ids']:
                    try:
                        return json.loads(result['order_ids'])
                    except:
                        return []
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting order IDs for {symbol}: {e}")
            return []
    
    def get_trade_history(self, days: int = 30, symbol: str = None, 
                         limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Holt Trade-Historie mit Pagination und Filtern"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT symbol, entry_price, exit_price, position, quantity, 
                           leverage, pnl, pnl_percentage, status, exit_reason, 
                           trade_duration_seconds, confidence, risk_reward_ratio,
                           closed_at, created_at
                    FROM trade_history 
                    WHERE closed_at >= datetime('now', ?)
                '''
                params = [f'-{days} days']
                
                if symbol:
                    query += ' AND symbol = ?'
                    params.append(symbol.upper())
                
                query += ' ORDER BY closed_at DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Error getting trade history: {e}")
            return []
    
    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Berechnet UM FASSENDE Performance-Statistiken"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                        SUM(pnl) as total_pnl,
                        AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                        AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
                        MAX(pnl) as largest_win,
                        MIN(pnl) as largest_loss,
                        AVG(trade_duration_seconds) as avg_trade_duration,
                        COUNT(DISTINCT symbol) as unique_symbols_traded
                    FROM trade_history 
                    WHERE closed_at >= datetime('now', ?)
                ''', [f'-{days} days'])
                
                result = cursor.fetchone()
                if not result:
                    return {}
                    
                stats = dict(result)
                
                # Berechne erweiterte Metriken
                if stats['total_trades'] > 0:
                    stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
                    stats['profit_factor'] = (
                        abs(stats['avg_win'] * stats['winning_trades']) / 
                        abs(stats['avg_loss'] * stats['losing_trades'])
                        if stats['losing_trades'] > 0 and stats['avg_loss'] != 0 else 0
                    )
                    stats['expectancy'] = (
                        (stats['win_rate'] / 100 * stats['avg_win']) + 
                        ((1 - stats['win_rate'] / 100) * stats['avg_loss'])
                    )
                else:
                    stats.update({
                        'win_rate': 0,
                        'profit_factor': 0,
                        'expectancy': 0
                    })
                
                logger.info(f"📊 Performance stats: {stats['total_trades']} trades, Win Rate: {stats['win_rate']:.1f}%")
                return stats
                
        except Exception as e:
            logger.error(f"❌ Error calculating performance stats: {e}")
            return {}
    
    def get_detailed_trade_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Holt DETAILLIERTE Trade-Informationen"""
        try:
            trade_data = self.get_trade_db(symbol)
            if not trade_data:
                return None
            
            # Füge UM FASSENDE Metriken hinzu
            trade_data.update({
                'order_ids_list': self.get_orders_id_db(symbol),
                'recent_trade_history': self.get_trade_history(symbol=symbol, days=7),
                'performance_stats': self.get_performance_stats(30),
                'similar_trades': self.get_similar_trades(symbol)
            })
            
            return trade_data
            
        except Exception as e:
            logger.error(f"❌ Error getting detailed trade info for {symbol}: {e}")
            return None
    
    def get_similar_trades(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Findet ähnliche Trades in der Historie"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, entry_price, exit_price, pnl, pnl_percentage, status
                    FROM trade_history 
                    WHERE symbol = ? AND closed_at >= datetime('now', ?)
                    ORDER BY closed_at DESC
                    LIMIT 10
                ''', (symbol.upper(), f'-{days} days'))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Error getting similar trades: {e}")
            return []
    
    def backup_database(self, backup_path: str = None) -> bool:
        """Erstellt ein PROFESSIONELLES Backup der Datenbank"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_trading_bot_{timestamp}.db"
            
            # Sicherstelle dass Backup-Verzeichnis existiert
            os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
            
            with self._get_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                with backup_conn:
                    conn.backup(backup_conn)
                backup_conn.close()
            
            # Prüfe Backup-Integrität
            try:
                test_conn = sqlite3.connect(backup_path)
                test_conn.execute("SELECT COUNT(*) FROM trades")
                test_conn.close()
            except:
                logger.error("❌ Backup integrity check failed")
                return False
            
            file_size = os.path.getsize(backup_path)
            logger.info(f"✅ Database backup created: {backup_path} ({file_size / 1024 / 1024:.2f} MB)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating database backup: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Gibt Datenbank-Statistiken zurück"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Tabellen-Größen
                cursor.execute('''
                    SELECT 
                        (SELECT COUNT(*) FROM trades WHERE active = 1) as active_trades,
                        (SELECT COUNT(*) FROM trades WHERE active = 0) as inactive_trades,
                        (SELECT COUNT(*) FROM trade_history) as history_trades,
                        (SELECT COUNT(*) FROM performance_metrics) as performance_entries
                ''')
                table_stats = cursor.fetchone()
                stats.update(dict(table_stats))
                
                # Datenbank-Größe
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                stats['database_size_mb'] = round(db_size / 1024 / 1024, 2)
                
                # Connection Pool Stats
                stats['connection_pool_size'] = len(self._connection_pool)
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

# Globale Instanz
db_manager = AdvancedDatabaseManager()

# KOMPATIBILITÄTSFUNKTIONEN für alten Code
def new_trade_db(price: float, date: str, symbol: str, leverage: float, qty: float, 
                positionSide: str, stoploss: float, tk1: float, tk2: float, 
                tk3: float, tk4: float, ordersID: str, risk_amount: float = 0,
                confidence: float = 75.0, risk_reward: float = 1.0):
    return db_manager.new_trade_db(date, symbol, leverage, price, positionSide, 
                                  qty, stoploss, tk1, tk2, tk3, tk4, ordersID,
                                  risk_amount, confidence, risk_reward)

def get_trade_db(symbol: str):
    return db_manager.get_trade_db(symbol)

def get_active_trades_symbol_db():
    return db_manager.get_active_trades_symbol_db()

def update_trade_status_db(symbol: str, new_status: str):
    return db_manager.update_trade_status_db(symbol, new_status)

def set_trade_noActive_db(symbol: str, exit_price: float = None, exit_reason: str = None, pnl: float = 0, pnl_percentage: float = 0):
    return db_manager.set_trade_noActive_db(symbol, exit_price, exit_reason, pnl, pnl_percentage)

def get_orders_id_db(symbol: str):
    return db_manager.get_orders_id_db(symbol)

def update_trade_amount_db(symbol: str, amount: float):
    return db_manager.update_trade_amount_db(symbol, amount)

def update_trade_enteryprice_db(symbol: str, realPrice: float):
    return db_manager.update_trade_enteryprice_db(symbol, realPrice)

def check_if_trade_exist(symbol: str) -> bool:
    """Überprüft ob Trade bereits existiert - KORRIGIERTE LOGIK"""
    trade = get_trade_db(symbol)
    return trade is not None

def check_and_update_unique_names(filename: str, symbol: str):
    """Fügt Symbol zur Handelsliste hinzu - ROBUST"""
    try:
        # Erstelle Verzeichnis falls nicht existiert
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Erweiterte Implementierung mit Duplikatprüfung
        existing_symbols = set()
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_symbols = set(line.strip() for line in f.readlines() if line.strip())
            except Exception as e:
                logger.warning(f"⚠️ Error reading {filename}: {e}")
        
        if symbol not in existing_symbols:
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(symbol + '\n')
            logger.info(f"✅ Added {symbol} to {filename}")
            return True
        else:
            logger.debug(f"ℹ️ {symbol} already exists in {filename}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error updating unique names file: {e}")
        return False

# ERWEITERTE FUNKTIONEN für neue Features
def get_trade_history(days: int = 30, symbol: str = None, limit: int = 100, offset: int = 0):
    return db_manager.get_trade_history(days, symbol, limit, offset)

def get_performance_stats(days: int = 30):
    return db_manager.get_performance_stats(days)

def get_detailed_trade_info(symbol: str):
    return db_manager.get_detailed_trade_info(symbol)

def backup_database(backup_path: str = None):
    return db_manager.backup_database(backup_path)

def get_database_stats():
    return db_manager.get_database_stats()