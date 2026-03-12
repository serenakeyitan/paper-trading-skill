# Paper Trading Skill for Claude Code

A Claude Code skill that turns your AI assistant into a paper trading coach. Designed for **stock beginners** — no quant background needed. Tell Claude what you want in plain English, and it handles the rest.

Powered by [Alpaca Markets](https://alpaca.markets/) paper trading (free, no real money).

## What It Does

- **Guides you through setup** — walks you through creating an Alpaca account and getting API keys
- **Trades in plain English** — "buy 10 shares of Apple", "sell my Tesla", "buy $200 of Bitcoin"
- **Explains as it goes** — teaches you what market orders, limit orders, and P&L mean
- **Automates strategies** — DCA, grid trading, momentum, mean reversion, dip buying
- **Keeps you updated** — cron-based trade logging and notifications
- **Live dashboard** — Bloomberg-style terminal UI for real-time monitoring

## Quick Start

### 1. Install

```bash
# Clone into your Claude Code skills directory
git clone https://github.com/serenakeyitan/paper-trading-skill.git ~/.claude/skills/paper-trade
cd ~/.claude/skills/paper-trade

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Get API Keys

1. Sign up at [app.alpaca.markets/signup](https://app.alpaca.markets/signup) (free)
2. Switch to **Paper Trading** in the top-left dropdown
3. Go to **API Keys** → **Generate New Key**
4. Save both the API Key ID and Secret Key

### 3. Configure

```bash
python trade.py setup YOUR_API_KEY YOUR_SECRET_KEY
```

### 4. Start Trading

Just tell Claude what you want:
- "Buy 5 shares of Apple"
- "How's my portfolio doing?"
- "Set up a DCA strategy for SPY, $200 every hour"
- "What's Bitcoin trading at?"

## Features

### Trading
| You say | What happens |
|---------|-------------|
| "buy 10 AAPL" | Market buy 10 shares of Apple |
| "buy $500 of TSLA" | Buy $500 worth of Tesla |
| "sell my NVDA" | Sell entire NVIDIA position |
| "buy $100 of Bitcoin" | Buy $100 of BTC/USD |
| "limit buy AAPL at $150" | Limit order at $150 |

### Automated Strategies
| Strategy | What it does | Best for |
|----------|-------------|----------|
| **DCA** | Buy fixed $ amount at regular intervals | Long-term accumulation |
| **Grid** | Place buy/sell orders at price levels | Sideways markets, crypto |
| **Momentum** | Buy top gainers, sell losers | Trending markets |
| **Mean Reversion** | Buy dips, sell bounces | Stable stocks |
| **Dip Buyer** | Buy when price drops below average | Crypto, volatile stocks |
| **Momentum Scalper** | Quick in/out on momentum | Crypto (24/7) |

### Live Dashboard
```bash
./run.sh
```
Real-time terminal UI with positions, orders, strategies, and watchlist panels.

## Architecture

```
paper-trade/
├── SKILL.md              # Claude Code skill definition
├── trade.py              # Main CLI (trade.py <command>)
├── tick.py               # Cron tick runner for strategies
├── strategy_manager.py   # Multi-strategy orchestrator
├── dashboard.py          # Bloomberg-style TUI
├── strategies/           # Strategy implementations
│   ├── base.py           # Abstract base class
│   ├── grid.py           # Grid trading
│   ├── dca.py            # Dollar cost averaging
│   ├── momentum.py       # Momentum/trend following
│   ├── mean_reversion.py # Mean reversion
│   ├── dip_buyer.py      # Buy-the-dip
│   └── momentum_scalper.py
├── scripts/
│   ├── install.sh        # Installation helper
│   └── log_trades.py     # Trade logging for cron
├── alpaca_cli/            # Click-based CLI (alternative)
├── tests/                # Test suite
│   ├── test_trade.py     # CLI tests
│   └── test_strategies.py # Strategy tests
└── config.example.json   # API key template
```

## Cron Integration

Set up automated strategy ticking and notifications:

```bash
# Tick strategies every 5 minutes
*/5 * * * * /path/to/.venv/bin/python /path/to/tick.py

# Log status every hour
0 * * * * /path/to/.venv/bin/python /path/to/scripts/log_trades.py --log-only
```

## Development

```bash
# Run tests
pip install pytest
pytest tests/ -v

# Install in development mode
pip install -e ".[dev]"
```

## Safety

- **Paper trading only** — hardcoded to Alpaca's paper endpoint, no real money
- **API keys stored securely** — config.json is chmod 600 and gitignored
- **No live trading** — the base URL cannot be changed

## License

MIT
