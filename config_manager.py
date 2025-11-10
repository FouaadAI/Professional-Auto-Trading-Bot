import configparser
import os
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ProfessionalConfigManager:
    def __init__(self, config_file: str = 'config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._config_cache = {}
        self._defaults_created = False
        self._last_modified = None
        self._change_listeners = []
        
        # Erweiterte Validierungsregeln
        self._validation_rules = {
            'BINANCE': {
                'api_key': {'type': 'str', 'min_len': 20, 'required': False},
                'api_secret': {'type': 'str', 'min_len': 20, 'required': False},
                'testnet': {'type': 'bool', 'default': True},
                'timeout': {'type': 'int', 'min': 10, 'max': 120, 'default': 30}
            },
            'TELEGRAM': {
                'bot_token': {'type': 'str', 'min_len': 10, 'required': True},
                'target_channel': {'type': 'str', 'required': True},
                'owner_id': {'type': 'str', 'required': True}
            },
            'TRADING': {
                'amount_per_trade': {'type': 'float', 'min': 10, 'max': 10000, 'default': 100},
                'max_open_trades': {'type': 'int', 'min': 1, 'max': 20, 'default': 5},
                'risk_per_trade': {'type': 'float', 'min': 0.1, 'max': 10, 'default': 2.0}
            }
        }
        
        self.load_config()
    
    def add_change_listener(self, listener):
        """Fügt einen Listener für Konfigurationsänderungen hinzu"""
        self._change_listeners.append(listener)
    
    def _notify_listeners(self, section: str, key: str, value: Any):
        """Benachrichtigt alle Listener über Änderungen"""
        for listener in self._change_listeners:
            try:
                listener(section, key, value)
            except Exception as e:
                logger.error(f"Error in config change listener: {e}")
    
    def load_config(self) -> bool:
        """Lädt die Konfiguration mit erweitertem Monitoring"""
        try:
            config_path = Path(self.config_file)
            
            # Prüfe auf Änderungen der Konfigurationsdatei
            current_modified = config_path.stat().st_mtime if config_path.exists() else None
            if current_modified == self._last_modified and not self._defaults_created:
                return True  # Keine Änderungen
            
            self._last_modified = current_modified
            
            if not config_path.exists():
                logger.warning(f"⚠️ Config file {self.config_file} not found, creating professional defaults")
                self.create_professional_config()
                self._defaults_created = True
            else:
                # Versuche verschiedene Encodings
                encodings = ['utf-8', 'utf-8-sig', 'latin-1']
                for encoding in encodings:
                    try:
                        with open(self.config_file, 'r', encoding=encoding) as f:
                            content = f.read()
                        self.config.read_string(content)
                        logger.info(f"✅ Config loaded from {self.config_file} with encoding {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    logger.error(f"❌ Could not read config file with any encoding: {self.config_file}")
                    return False
                
            # Erweiterte Validierung und Auto-Korrektur
            validation_result = self._advanced_validation()
            if not validation_result['valid']:
                logger.warning(f"⚠️ Config validation issues: {validation_result['errors']}")
                self._auto_fix_config_issues(validation_result['errors'])
            
            self._cache_config_values()
            self._migrate_old_config()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            # Erstelle Notfall-Standardkonfiguration
            self.create_professional_config()
            return False
    
    def create_professional_config(self) -> None:
        """Erstellt eine PROFESSIONELLE Standard-Konfigurationsdatei"""
        try:
            # PROFESSIONELLE Standardwerte für maximale Leistung
            self.config['BINANCE'] = {
                'api_key': 'qHAelUMq7GDK82aWaGZcIcECHuNFifTVYfhXxi5RXMIp5CPQbALoqplrvsKlxaSA',
                'api_secret': 'eXOBcL0QxoDll8MBFtcutMsNrH8j1fM0unHdDjcOZvnMywsvAsjBnxj1oSB3SAEX',
                'testnet': 'true',
                'timeout': '45',
                'rate_limit': 'true',
                'sandbox_mode': 'true',
                'recv_window': '15000',
                'enable_rate_limit': 'true',
                'verbose': 'false'
            }
            
            self.config['TELEGRAM'] = {
                'bot_token': '7142965432:AAH3_1h6b5I4C8D9E0F1G2H3I4J5K6L7M8N9O0P',
                'target_channel': '@your_trading_channel',
                'owner_id': '123456789',
                'admin_ids': '123456789,987654321',
                'enable_notifications': 'true',
                'notification_level': 'INFO',
                'alert_on_trade': 'true',
                'alert_on_error': 'true',
                'alert_on_completion': 'true'
            }
            
            self.config['TRADING'] = {
                'amount_per_trade': '100',
                'max_open_trades': '5',
                'default_leverage': '3',
                'risk_per_trade': '2.0',
                'max_daily_trades': '10',
                'min_risk_reward': '1.5',
                'auto_position_sizing': 'true',
                'enable_stop_loss': 'true',
                'enable_take_profit': 'true',
                'trailing_stop': 'true',
                'breakeven_stop': 'true',
                'partial_profit_taking': 'true',
                'emergency_stop_loss': '15.0',
                'max_position_size': '10000',
                'min_trade_amount': '10'
            }
            
            self.config['RISK_MANAGEMENT'] = {
                'max_portfolio_risk': '5.0',
                'max_drawdown_per_trade': '2.0',
                'max_drawdown_daily': '5.0',
                'volatility_adjustment': 'true',
                'correlation_protection': 'true',
                'emergency_stop_loss': '10.0',
                'position_sizing_method': 'fixed_fractional',
                'max_leverage_allowed': '20',
                'trailing_stop_activation': '5.0',
                'trailing_stop_distance': '2.0',
                'breakeven_activation': '3.0'
            }
            
            self.config['MONITORING'] = {
                'polling_interval': '30',
                'price_check_interval': '10',
                'health_check_interval': '60',
                'performance_tracking': 'true',
                'trade_analytics': 'true',
                'alert_on_slippage': 'true',
                'slippage_threshold': '0.5',
                'max_retries': '3',
                'retry_delay': '2',
                'enable_websocket': 'false',
                'real_time_updates': 'true'
            }
            
            self.config['DATABASE'] = {
                'db_path': 'professional_trading_bot.db',
                'backup_interval_hours': '24',
                'max_history_days': '365',
                'performance_tracking': 'true',
                'auto_cleanup': 'true',
                'connection_pool_size': '5',
                'query_timeout': '30',
                'enable_wal_mode': 'true'
            }
            
            self.config['LOGGING'] = {
                'log_level': 'INFO',
                'log_file': 'professional_trading.log',
                'max_log_size_mb': '50',
                'log_backup_count': '10',
                'enable_console_logging': 'true',
                'enable_file_logging': 'true',
                'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'enable_rotation': 'true',
                'log_to_telegram': 'false'
            }
            
            self.config['API'] = {
                'max_retries': '5',
                'retry_delay': '1',
                'request_timeout': '30',
                'enable_rate_limiting': 'true',
                'requests_per_minute': '120',
                'request_delay': '0.15',
                'enable_compression': 'true',
                'cache_timeout': '300'
            }
            
            self.config['ADVANCED'] = {
                'auto_restart_on_error': 'true',
                'health_check_enabled': 'true',
                'memory_usage_monitor': 'true',
                'cpu_usage_monitor': 'true',
                'auto_update_check': 'false',
                'debug_mode': 'false',
                'simulation_mode': 'false',
                'performance_optimization': 'true',
                'enable_caching': 'true',
                'cache_cleanup_interval': '3600'
            }

            # Erstelle Verzeichnis falls nicht existiert
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
                
            logger.info(f"✅ Professional config created at {self.config_file}")
            
        except Exception as e:
            logger.error(f"❌ Error creating professional config: {e}")
            raise
    
    def _advanced_validation(self) -> Dict[str, Any]:
        """Führt erweiterte Validierung mit Auto-Korrektur durch"""
        errors = []
        warnings = []
        
        try:
            required_sections = ['BINANCE', 'TELEGRAM', 'TRADING', 'LOGGING']
            
            for section in required_sections:
                if not self.config.has_section(section):
                    errors.append(f"Missing required section: {section}")
                    # Auto-Korrektur: Fehlende Sektion hinzufügen
                    self.config[section] = {}
            
            # Validiere Telegram Bot Token
            bot_token = self.get('TELEGRAM', 'bot_token')
            if not bot_token or bot_token.startswith('your_'):
                errors.append("Telegram bot token not configured")
            
            # Validiere Trading-Parameter
            trading_settings = self.get_trading_settings()
            if trading_settings['amount_per_trade'] <= 0:
                errors.append("amount_per_trade must be positive")
            
            if not (0.1 <= trading_settings['risk_per_trade'] <= 20):
                errors.append("risk_per_trade must be between 0.1 and 20")
            
            # Validiere API Konfiguration
            if self.get_boolean('BINANCE', 'testnet', True):
                warnings.append("Running in TESTNET mode - no real trades")
            
            # Validiere numerische Werte
            numeric_checks = [
                ('TRADING', 'amount_per_trade', 10, 100000),
                ('TRADING', 'risk_per_trade', 0.1, 50),
                ('MONITORING', 'polling_interval', 5, 300),
                ('API', 'max_retries', 1, 10)
            ]
            
            for section, key, min_val, max_val in numeric_checks:
                value = self.get_float(section, key)
                if not (min_val <= value <= max_val):
                    warnings.append(f"{section}.{key} should be between {min_val} and {max_val}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {'valid': False, 'errors': [str(e)], 'warnings': []}
    
    def _auto_fix_config_issues(self, errors: List[str]):
        """Automatische Korrektur von Konfigurationsproblemen"""
        fixes_applied = []
        
        for error in errors:
            try:
                if "amount_per_trade" in error:
                    self.set('TRADING', 'amount_per_trade', '100')
                    fixes_applied.append("Set amount_per_trade to 100")
                
                elif "risk_per_trade" in error:
                    self.set('TRADING', 'risk_per_trade', '2.0')
                    fixes_applied.append("Set risk_per_trade to 2.0")
                
                elif "polling_interval" in error:
                    self.set('MONITORING', 'polling_interval', '30')
                    fixes_applied.append("Set polling_interval to 30")
                    
            except Exception as e:
                logger.error(f"Error auto-fixing {error}: {e}")
        
        if fixes_applied:
            logger.info(f"✅ Auto-fixed config issues: {fixes_applied}")
    
    def _migrate_old_config(self):
        """Migriert alte Konfigurationsformate zu neuen"""
        try:
            # Migration von alten Sektionsnamen
            migrations = [
                ('SETTINGS', 'MONITORING'),
                ('GENERAL', 'ADVANCED')
            ]
            
            for old_section, new_section in migrations:
                if self.config.has_section(old_section) and not self.config.has_section(new_section):
                    self.config[new_section] = dict(self.config.items(old_section))
                    self.config.remove_section(old_section)
                    logger.info(f"🔧 Migrated config section {old_section} to {new_section}")
            
            # Speichere migrierte Konfiguration
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
                
        except Exception as e:
            logger.debug(f"No config migration needed: {e}")
    
    def _cache_config_values(self) -> None:
        """Cached PROFESSIONELLE Konfigurationswerte für maximale Performance"""
        try:
            self._config_cache = {
                'binance_testnet': self.get_boolean('BINANCE', 'testnet', True),
                'trading_amount': self.get_float('TRADING', 'amount_per_trade', 100.0),
                'polling_interval': self.get_int('MONITORING', 'polling_interval', 30),
                'log_level': self.get('LOGGING', 'log_level', 'INFO'),
                'max_open_trades': self.get_int('TRADING', 'max_open_trades', 5),
                'risk_per_trade': self.get_float('TRADING', 'risk_per_trade', 2.0),
                'api_timeout': self.get_int('API', 'request_timeout', 30),
                'max_retries': self.get_int('API', 'max_retries', 3)
            }
        except Exception as e:
            logger.error(f"❌ Error caching config values: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Holt einen Konfigurationswert mit erweiterter Logik"""
        try:
            # Versuche zuerst den Cache
            cache_key = f"{section}_{key}"
            if cache_key in self._config_cache:
                return self._config_cache[cache_key]
            
            # Fallback-Ketten
            fallback_chain = [
                lambda: self.config.get(section, key, fallback=default),
                lambda: self._get_environment_variable(section, key, default),
                lambda: default
            ]
            
            for fallback in fallback_chain:
                try:
                    value = fallback()
                    if value is not None:
                        # Cache den Wert
                        self._config_cache[cache_key] = value
                        return value
                except (configparser.NoOptionError, configparser.NoSectionError):
                    continue
            
            return default
            
        except Exception as e:
            logger.debug(f"Config get error for {section}.{key}: {e}")
            return default
    
    def _get_environment_variable(self, section: str, key: str, default: Any) -> Any:
        """Holt Werte aus Environment Variables"""
        env_key = f"{section}_{key}".upper()
        return os.getenv(env_key, default)
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Holt einen Integer-Wert mit erweiterter Validierung"""
        try:
            value = self.get(section, key, default)
            if isinstance(value, int):
                return value
            elif isinstance(value, str):
                # Entferne nicht-numerische Zeichen
                cleaned = ''.join(c for c in value if c.isdigit() or c == '-')
                return int(cleaned) if cleaned else default
            else:
                return int(value) if value is not None else default
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ Invalid integer value for {section}.{key}: {e}, using default: {default}")
            return default
    
    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """Holt einen Float-Wert mit erweiterter Validierung"""
        try:
            value = self.get(section, key, default)
            if isinstance(value, float):
                return value
            elif isinstance(value, str):
                # Ersetze Kommas durch Punkte für internationale Unterstützung
                normalized = value.replace(',', '.')
                # Entferne nicht-numerische Zeichen außer Punkten und Minus
                cleaned = ''.join(c for c in normalized if c.isdigit() or c in '.-')
                return float(cleaned) if cleaned else default
            else:
                return float(value) if value is not None else default
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ Invalid float value for {section}.{key}: {e}, using default: {default}")
            return default
    
    def get_boolean(self, section: str, key: str, default: bool = False) -> bool:
        """Holt einen Boolean-Wert mit erweiterter Erkennung"""
        try:
            value = self.get(section, key, default)
            if isinstance(value, bool):
                return value
            
            if isinstance(value, (int, float)):
                return bool(value)
            
            if isinstance(value, str):
                value_lower = value.lower().strip()
                true_values = ['true', 'yes', '1', 'on', 'enable', 'enabled', 'active']
                false_values = ['false', 'no', '0', 'off', 'disable', 'disabled', 'inactive']
                
                if value_lower in true_values:
                    return True
                elif value_lower in false_values:
                    return False
                else:
                    logger.warning(f"⚠️ Unrecognized boolean value for {section}.{key}: '{value}', using default: {default}")
                    return default
            
            return bool(value)
        except Exception as e:
            logger.warning(f"⚠️ Invalid boolean value for {section}.{key}: {e}, using default: {default}")
            return default
    
    def get_list(self, section: str, key: str, default: List = None, delimiter: str = ',') -> List:
        """Holt eine Liste von Werten mit erweiterter Verarbeitung"""
        try:
            value = self.get(section, key, '')
            if not value:
                return default or []
            
            # Unterstützung für JSON-Arrays
            if value.strip().startswith('[') and value.strip().endswith(']'):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            
            # Standard Komma-getrennte Werte
            return [item.strip() for item in value.split(delimiter) if item.strip()]
        except Exception as e:
            logger.warning(f"⚠️ Invalid list value for {section}.{key}: {e}, using default")
            return default or []
    
    def get_dict(self, section: str, prefix: str = '') -> Dict[str, Any]:
        """Holt alle Werte einer Sektion als Dictionary"""
        try:
            if not self.config.has_section(section):
                return {}
            
            result = {}
            for key, value in self.config.items(section):
                dict_key = f"{prefix}_{key}" if prefix else key
                result[dict_key] = value
            
            return result
        except Exception as e:
            logger.error(f"Error getting dict for section {section}: {e}")
            return {}
    
    def set(self, section: str, key: str, value: Any, auto_save: bool = True) -> bool:
        """Setzt einen Konfigurationswert mit erweiterter Funktionalität"""
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            # Konvertiere Wert zu String für sichere Speicherung
            if isinstance(value, (list, dict)):
                str_value = json.dumps(value, ensure_ascii=False)
            else:
                str_value = str(value)
            
            self.config.set(section, key, str_value)
            
            # Aktualisiere Cache sofort
            cache_key = f"{section}_{key}"
            self._config_cache[cache_key] = value
            
            # Benachrichtige Listener
            self._notify_listeners(section, key, value)
            
            if auto_save:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    self.config.write(f)
                
                logger.info(f"✅ Config updated: {section}.{key} = {value}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting config value {section}.{key}: {e}")
            return False
    
    def set_multiple(self, updates: Dict[str, Dict[str, Any]], auto_save: bool = True) -> bool:
        """Setzt mehrere Konfigurationswerte auf einmal"""
        try:
            for section, section_updates in updates.items():
                for key, value in section_updates.items():
                    self.set(section, key, value, auto_save=False)
            
            if auto_save:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    self.config.write(f)
                
                logger.info(f"✅ Config updated {len(updates)} sections")
            
            return True
        except Exception as e:
            logger.error(f"❌ Error setting multiple config values: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """Gibt alle Konfigurationseinstellungen mit Typ-Konvertierung zurück"""
        settings = {}
        try:
            for section in self.config.sections():
                section_settings = {}
                for key, value in self.config.items(section):
                    # Intelligente Typ-Erkennung
                    if value.lower() in ['true', 'false']:
                        section_settings[key] = self.get_boolean(section, key)
                    elif value.replace('.', '').replace('-', '').isdigit():
                        if '.' in value:
                            section_settings[key] = self.get_float(section, key)
                        else:
                            section_settings[key] = self.get_int(section, key)
                    else:
                        section_settings[key] = value
                settings[section] = section_settings
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
        
        return settings
    
    def is_testnet_mode(self) -> bool:
        """Prüft ob Testnet-Modus aktiv ist"""
        return self.get_boolean('BINANCE', 'testnet', True)
    
    def get_trading_settings(self) -> Dict[str, Any]:
        """Gibt alle Trading-Einstellungen als optimiertes Dictionary zurück"""
        return {
            'amount_per_trade': self.get_float('TRADING', 'amount_per_trade', 100.0),
            'max_open_trades': self.get_int('TRADING', 'max_open_trades', 5),
            'default_leverage': self.get_int('TRADING', 'default_leverage', 3),
            'risk_per_trade': self.get_float('TRADING', 'risk_per_trade', 2.0),
            'min_risk_reward': self.get_float('TRADING', 'min_risk_reward', 1.5),
            'enable_stop_loss': self.get_boolean('TRADING', 'enable_stop_loss', True),
            'enable_take_profit': self.get_boolean('TRADING', 'enable_take_profit', True),
            'trailing_stop': self.get_boolean('TRADING', 'trailing_stop', True),
            'breakeven_stop': self.get_boolean('TRADING', 'breakeven_stop', True),
            'partial_profit_taking': self.get_boolean('TRADING', 'partial_profit_taking', True)
        }
    
    def get_risk_settings(self) -> Dict[str, Any]:
        """Gibt alle Risk-Management-Einstellungen als optimiertes Dictionary zurück"""
        return {
            'max_portfolio_risk': self.get_float('RISK_MANAGEMENT', 'max_portfolio_risk', 5.0),
            'max_drawdown_per_trade': self.get_float('RISK_MANAGEMENT', 'max_drawdown_per_trade', 2.0),
            'max_leverage_allowed': self.get_int('RISK_MANAGEMENT', 'max_leverage_allowed', 20),
            'volatility_adjustment': self.get_boolean('RISK_MANAGEMENT', 'volatility_adjustment', True),
            'trailing_stop_activation': self.get_float('RISK_MANAGEMENT', 'trailing_stop_activation', 5.0),
            'trailing_stop_distance': self.get_float('RISK_MANAGEMENT', 'trailing_stop_distance', 2.0)
        }
    
    def get_api_settings(self) -> Dict[str, Any]:
        """Gibt alle API-Einstellungen als optimiertes Dictionary zurück"""
        return {
            'max_retries': self.get_int('API', 'max_retries', 5),
            'retry_delay': self.get_int('API', 'retry_delay', 1),
            'request_timeout': self.get_int('API', 'request_timeout', 30),
            'enable_rate_limiting': self.get_boolean('API', 'enable_rate_limiting', True),
            'request_delay': self.get_float('API', 'request_delay', 0.15),
            'cache_timeout': self.get_int('API', 'cache_timeout', 300)
        }
    
    def reload(self) -> bool:
        """Lädt die Konfiguration neu mit erweiterter Logik"""
        self._config_cache.clear()
        return self.load_config()
    
    def create_backup(self, backup_path: str = None) -> bool:
        """Erstellt ein PROFESSIONELLES Backup der Konfiguration"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = "config_backups"
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, f"professional_config_backup_{timestamp}.ini")
            
            import shutil
            shutil.copy2(self.config_file, backup_path)
            
            # Erstelle auch eine JSON-Version für einfacheres Parsing
            json_backup = backup_path.replace('.ini', '.json')
            with open(json_backup, 'w', encoding='utf-8') as f:
                json.dump(self.get_all_settings(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Professional config backup created: {backup_path} and {json_backup}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating config backup: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """Stellt eine Konfiguration aus einem Backup wieder her"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Sicherung der aktuellen Konfiguration
            self.create_backup()
            
            # Wiederherstellung
            import shutil
            shutil.copy2(backup_path, self.config_file)
            
            # Neu laden
            self.reload()
            
            logger.info(f"✅ Config restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error restoring config backup: {e}")
            return False
    
    def validate_config_integrity(self) -> Dict[str, Any]:
        """Validiert die Integrität der gesamten Konfiguration"""
        try:
            issues = []
            recommendations = []
            
            # Prüfe kritische Einstellungen
            if self.is_testnet_mode():
                recommendations.append("Running in TESTNET mode - safe for testing")
            else:
                issues.append("LIVE TRADING mode - ensure proper risk management")
            
            # Prüfe Trading-Parameter
            trading_settings = self.get_trading_settings()
            if trading_settings['risk_per_trade'] > 5:
                issues.append(f"High risk per trade: {trading_settings['risk_per_trade']}%")
            
            if trading_settings['max_open_trades'] > 10:
                recommendations.append(f"Consider reducing max_open_trades from {trading_settings['max_open_trades']} for better risk management")
            
            # Prüfe API Konfiguration
            api_settings = self.get_api_settings()
            if api_settings['request_delay'] < 0.1:
                recommendations.append("Consider increasing request_delay to avoid rate limiting")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'recommendations': recommendations,
                'testnet_mode': self.is_testnet_mode(),
                'trading_settings': trading_settings,
                'risk_settings': self.get_risk_settings()
            }
            
        except Exception as e:
            logger.error(f"Error validating config integrity: {e}")
            return {'valid': False, 'issues': [str(e)], 'recommendations': []}
    
    def export_to_json(self, file_path: str = None) -> bool:
        """Exportiert die Konfiguration als JSON"""
        try:
            if not file_path:
                file_path = f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.get_all_settings(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Config exported to JSON: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error exporting config to JSON: {e}")
            return False

# PROFESSIONELLE Globale Instanz
config_manager = ProfessionalConfigManager()

# Kompatibilitäts-Alias für bestehenden Code
config = config_manager

# Schnelle Zugriffsfunktionen für häufig verwendete Werte
def get_trading_amount() -> float:
    return config.get_float('TRADING', 'amount_per_trade', 100.0)

def get_risk_per_trade() -> float:
    return config.get_float('TRADING', 'risk_per_trade', 2.0)

def is_testnet() -> bool:
    return config.is_testnet_mode()

def get_polling_interval() -> int:
    return config.get_int('MONITORING', 'polling_interval', 30)

def get_log_level() -> str:
    return config.get('LOGGING', 'log_level', 'INFO')

def get_max_open_trades() -> int:
    return config.get_int('TRADING', 'max_open_trades', 5)