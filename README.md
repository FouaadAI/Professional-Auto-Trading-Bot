# 🤖 Professional Auto-Trading Bot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8

**Advanced Algorithmic Trading System with Intelligent Risk Management**

[Features](#-features) • [Installation](#-installation) • [Configuration](#-configuration) • [Usage](#-usage) • [Signal Format](#-signal-format) • [Risk Management](#-risk-management) • [Monitoring](#-monitoring) • [Contributing](#-contributing)

</div>

## 🚀 Overview

Professional Auto-Trading Bot is a sophisticated algorithmic trading system designed for Binance that automatically executes trades based on Telegram signals. The system features advanced risk management, real-time monitoring, and comprehensive analytics.

### 🎯 Key Capabilities
- **🤖 Automatic Signal Processing** - Parse trading signals from any Telegram channel
- **📊 Advanced Risk Management** - Multi-layer protection with trailing stops
- **📈 Real-time Monitoring** - Continuous price tracking and position management
- **💾 Professional Database** - Complete trade history and performance analytics
- **📱 Telegram Integration** - Full control via Telegram commands

## ✨ Features

### 🎯 Core Trading
- ✅ **Intelligent Signal Parsing** - Advanced NLP for signal extraction
- 📊 **Multi-Target Strategy** - 4 take-profit levels with partial closes
- 🛡️ **Advanced Stop Loss** - Dynamic trailing stops and breakeven protection
- ⚖️ **Auto Position Sizing** - Risk-based position calculation
- 🔄 **Partial Profit Taking** - Secure profits at multiple levels

### 🛡️ Risk Management
- 🚨 **Emergency Stop Loss** - Automatic exit on extreme losses
- 📉 **Drawdown Protection** - Maximum loss limits per trade and portfolio
- ⚡ **Volatility Adjustment** - Dynamic risk parameters based on market conditions
- ⏰ **Time-based Exits** - Automatic closure after maximum duration
- 🔒 **Correlation Protection** - Prevent overexposure to correlated assets

### 📊 Monitoring & Analytics
- 📈 **Real-time Performance** - Live PnL tracking and analytics
- 📊 **Comprehensive Statistics** - Win rate, profit factor, expectancy
- 📋 **Trade History** - Complete audit trail and performance analysis
- 🏥 **System Health** - Continuous monitoring of all components
- 📱 **Telegram Dashboard** - Full control and status via Telegram

### 🔧 Technical Excellence
- 💾 **SQLite Database** - Professional data management with WAL mode
- 📡 **Robust API Integration** - Rate limiting, retry logic, error handling
- 🔄 **Connection Pooling** - High-performance database connections
- 🛠️ **Modular Architecture** - Clean, maintainable code structure
- 📝 **Comprehensive Logging** - Detailed audit trails and debugging

## 🛠 Installation

### Prerequisites
- Python 3.8 or higher
- Binance Account (Live or Testnet)
- Telegram Bot Token

### Step 1: Clone Repository
```bash
git clone https://github.com/FouaadAI/professional-Auto-Trading-Bot.git
cd professional-trading-bot
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configuration
1. Copy `config.ini.example` to `config.ini`
2. Configure your settings (see Configuration section below)

### Step 4: Set Environment Variables (Optional)
```bash
# For Live Trading
export BINANCE_LIVE_API_KEY="your_live_api_key"
export BINANCE_LIVE_API_SECRET="your_live_api_secret"

# For Testnet
export BINANCE_TESTNET_API_KEY="your_testnet_api_key"
export BINANCE_TESTNET_API_SECRET="your_testnet_api_secret"
```

## ⚙️ Configuration

### Essential Configuration

#### Binance API Settings
```ini
[BINANCE]
api_key = your_api_key_here
api_secret = your_api_secret_here
testnet = true  # Set to false for live trading
```

#### Telegram Bot Settings
```ini
[TELEGRAM]
bot_token = 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
target_channel = @your_trading_channel
owner_id = 123456789
```

#### Trading Parameters
```ini
[TRADING]
amount_per_trade = 100  # USDT per trade
max_open_trades = 5
risk_per_trade = 2.0    # % risk per trade
default_leverage = 3
```

### Risk Management Configuration
```ini
[RISK_MANAGEMENT]
max_portfolio_risk = 5.0
max_drawdown_per_trade = 2.0
trailing_stop_activation = 5.0
emergency_stop_loss = 15.0
```

## 🚀 Usage

### Starting the Bot
```bash
python main.py
```

### Telegram Commands
- `/start` - Show main menu with interactive controls
- `/balance` - Account balance and equity overview
- `/trades` - Active trades with real-time PnL
- `/stats` - Trading statistics and analytics
- `/performance` - Detailed performance metrics
- `/history` - Trade history and analysis
- `/settings` - Bot configuration and status
- `/monitoring` - Monitoring controls
- `/health` - System health status
- `/help` - Comprehensive help guide

### Trade Management
```bash
/cancel SYMBOL    # Cancel specific active trade
/monitoring start # Start price monitoring
/monitoring stop  # Stop price monitoring
```

## 📨 Signal Format

The bot automatically processes trading signals from any Telegram channel. Supported formats:

### Basic Format
```
#BTCUSDT Long
Entry: 50000
Target 1: 51000
Target 2: 52000
Target 3: 53000
Target 4: 54000
Stop-Loss: 49000
```

### Advanced Format with Leverage
```
#ETHUSDT Short
Entry: 3000-3100
Leverage: 5x
Target 1: 2900
Target 2: 2800
Target 3: 2700
Target 4: 2600
Stop-Loss: 3200
```

### Features Supported
- ✅ **Symbol Detection** - Automatic USDT pairing
- 📊 **Price Ranges** - Entry: 50000-51000 → Average: 50500
- ⚖️ **Leverage Detection** - Auto-detected or specified
- 📈 **Multiple Targets** - Up to 4 take-profit levels
- 🛡️ **Stop Loss** - Required for risk management
- 🔮 **Confidence Levels** - Optional confidence scoring

## 🛡️ Risk Management

### Multi-Layer Protection System

#### 1. Stop Loss Protection
- **Hard Stop Loss** - Fixed price level protection
- **Trailing Stop Loss** - Dynamic stops that follow price
- **Breakeven Stop** - Automatically moves to breakeven
- **Emergency Stop** - Extreme loss protection

#### 2. Position Management
```python
# Automatic position sizing
quantity, risk_amount = binance_api.calculate_position_size(entry_price)

# Risk per trade: 2% of portfolio
# Maximum drawdown: 2% per trade, 5% daily
# Leverage limits: Up to 20x (configurable)
```

#### 3. Portfolio Protection
- **Maximum Open Trades** - Prevents overexposure
- **Correlation Checks** - Avoids correlated positions
- **Daily Loss Limits** - Prevents catastrophic losses
- **Time-based Exits** - Maximum trade duration

### Risk Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| Risk per Trade | 2.0% | Maximum risk per individual trade |
| Max Portfolio Risk | 5.0% | Maximum total portfolio risk |
| Emergency Stop | 15.0% | Automatic exit on large losses |
| Max Trade Duration | 168h | Close trade after 7 days |
| Trailing Stop Activation | 5.0% | Activate trailing at 5% profit |

## 📊 Monitoring & Analytics

### Real-time Dashboard
The bot provides comprehensive monitoring through Telegram:

```
📊 PROFESSIONAL TRADING BOT - SYSTEM STATUS

🤖 Bot: 🟢 ONLINE
📊 Monitoring: 🟢 ACTIVE  
💾 Database: 🟢 CONNECTED
📈 API: 🟢 OPERATIONAL
🛡️ Risk Management: 🟢 ACTIVE

🔢 Active Trades: 3
📈 Total PnL: +245.50 USDT
🎯 Win Rate: 67.8%
⏰ Uptime: 12.5 hours
```

### Performance Metrics
- **Win Rate** - Percentage of profitable trades
- **Profit Factor** - Gross profit / gross loss
- **Expectancy** - Average profit per trade
- **Sharpe Ratio** - Risk-adjusted returns
- **Max Drawdown** - Largest peak-to-trough decline

### Health Monitoring
```python
# Continuous system health checks
health_status = {
    'status': 'healthy',
    'success_rate': 98.5,
    'uptime_seconds': 45000,
    'api_connection': 'stable',
    'database_health': 'optimal'
}
```

## 🗃️ Database

### Professional Data Management
- **SQLite with WAL Mode** - High-performance transactions
- **Connection Pooling** - Efficient database connections
- **Automatic Backups** - Daily backup with rotation
- **Comprehensive History** - Complete trade audit trail

### Database Schema
```sql
-- Trades Table
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    entry_price REAL NOT NULL,
    position TEXT NOT NULL,
    quantity REAL NOT NULL,
    leverage REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit_1 REAL NOT NULL,
    -- ... 4 take profit levels
    status TEXT DEFAULT 'NEW',
    active INTEGER DEFAULT 1
);

-- Trade History
CREATE TABLE trade_history (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    pnl REAL,
    pnl_percentage REAL,
    status TEXT NOT NULL,
    exit_reason TEXT
);
```

## 🏗️ Architecture

### System Components
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │◄──►│  Signal Parser   │◄──►│  Binance API    │
│                 │    │                  │    │                 │
│  - Commands     │    │  - NLP Parsing   │    │  - Order Exec   │
│  - Notifications│    │  - Validation    │    │  - Price Data   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Risk Manager   │◄──►│  Price Monitor   │◄──►│   Database      │
│                 │    │                  │    │                 │
│  - Stop Loss    │    │  - Real-time     │    │  - Trade Storage│
│  - Take Profit  │    │  - Monitoring    │    │  - Analytics    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Module Overview
- **`main.py`** - Telegram bot and command handler
- **`professional_signal_parser.py`** - Advanced signal processing
- **`risk_management.py`** - Comprehensive risk management
- **`advanced_polling.py`** - Real-time price monitoring
- **`enhanced_binance_api.py`** - Binance API integration
- **`database.py`** - Professional database management
- **`config_manager.py`** - Configuration management

## 🔧 Development

### Code Structure
```bash
professional-trading-bot/
├── main.py                      # Main bot application
├── professional_signal_parser.py # Signal processing engine
├── risk_management.py           # Risk management system
├── advanced_polling.py          # Price monitoring
├── enhanced_binance_api.py      # Binance API wrapper
├── database.py                  # Database management
├── config_manager.py            # Configuration handler
├── config.ini                   # Configuration file
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

### Adding New Features
1. Follow the modular architecture
2. Implement comprehensive error handling
3. Add proper logging and documentation
4. Update configuration management
5. Test thoroughly before deployment

## 🚨 Risk Disclaimer

**⚠️ IMPORTANT: Trading involves substantial risk**

- This software is for educational purposes
- Past performance does not guarantee future results
- Test thoroughly in simulation before live trading
- Use proper risk management at all times
- The developers are not responsible for financial losses

### Recommended Practices
1. **Start with Testnet** - Test extensively before live trading
2. **Small Position Sizes** - Begin with minimal risk
3. **Diversify** - Don't concentrate risk in few trades
4. **Monitor Continuously** - Always supervise automated systems
5. **Keep Backups** - Regular database and configuration backups

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/yourusername/professional-trading-bot.git

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

### Code Standards
- Follow PEP 8 style guide
- Include comprehensive docstrings
- Write unit tests for new features
- Update documentation accordingly

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/FouaadAI/Professional-Auto-Trading-Bot/blob/main/requirements.txt) file for details.



<div align="center">

**⭐ Star this repository if you find it helpful!**

*Built with ❤️ for the trading community*

</div>
