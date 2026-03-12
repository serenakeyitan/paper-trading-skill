---
name: paper-trade
description: Paper trade stocks and crypto via Alpaca. Guides beginners through setup, helps automate strategies, logs every action, and keeps you notified. Use when the user wants to trade stocks, buy crypto, check portfolio, automate trading strategies, or learn about investing.
user-invocable: true
argument-hint: [action or question]
---

# Paper Trading Skill

Your AI trading assistant for Alpaca paper trading. Designed for people who are **new to trading** — no quant background needed. You tell it what you want in plain English, and it handles the rest.

## When to Use This Skill

Use this skill when the user wants to:
- **Get started with paper trading** (set up an Alpaca account and API keys)
- **Buy or sell stocks/crypto** in plain English ("buy some Apple stock", "sell my Tesla")
- **Check their portfolio** ("how's my portfolio doing?", "am I making money?")
- **Learn about trading concepts** (explain what a limit order is, what DCA means)
- **Automate a trading strategy** (DCA, grid trading, momentum, dip buying)
- **See their trade history** or performance stats

## Step 1: Onboarding — Help Users Get Their API Keys

If the user hasn't set up their API keys yet (config.json doesn't exist or is empty), walk them through this:

### What is Alpaca?
Alpaca is a commission-free stock and crypto trading platform. **Paper trading** means you trade with fake money — so you can practice without any risk. It's completely free.

### How to Get Your API Keys

Guide the user through these steps:

1. **Create a free Alpaca account**
   - Go to [https://app.alpaca.markets/signup](https://app.alpaca.markets/signup)
   - Sign up with email (no credit card needed)
   - Verify your email

2. **Switch to Paper Trading**
   - After logging in, look at the top-left of the dashboard
   - Click the dropdown and select **"Paper Trading"**
   - This switches you to the practice environment

3. **Generate API Keys**
   - In the Paper Trading dashboard, click **"API Keys"** in the left sidebar
   - Click **"Generate New Key"**
   - You'll see two values:
     - **API Key ID** (looks like: `PKXXXXXXXXXXXXXXXXXX`)
     - **Secret Key** (longer string — **save this immediately**, you can only see it once!)

4. **Save the keys**
   Once the user provides both keys, run the setup:
   ```bash
   /root/.openclaw/skills/paper-trade/.venv/bin/python /root/.openclaw/skills/paper-trade/trade.py setup <API_KEY> <SECRET_KEY>
   ```
   This saves keys to `config.json` (chmod 600) and tests the connection.

5. **Verify it works**
   ```bash
   /root/.openclaw/skills/paper-trade/.venv/bin/python /root/.openclaw/skills/paper-trade/trade.py account
   ```
   Should show $100,000 starting equity in the paper account.

## Step 2: Trading — Natural Language to Commands

The user will speak in plain English. Translate their intent into CLI commands.

**CLI prefix**: `/root/.openclaw/skills/paper-trade/.venv/bin/python /root/.openclaw/skills/paper-trade/trade.py`

### Buying & Selling

| User says | Command |
|-----------|---------|
| "buy 10 shares of Apple" | `buy AAPL --qty 10` |
| "buy $500 worth of Tesla" | `buy TSLA --notional 500` |
| "sell all my Microsoft" | `sell MSFT` |
| "sell 5 shares of NVIDIA" | `sell NVDA --qty 5` |
| "buy some Bitcoin" | `buy BTC/USD --notional 100` |
| "buy $200 of Ethereum" | `buy ETH/USD --notional 200` |
| "set a limit buy for Apple at $150" | `buy AAPL --qty 10 --type limit --limit-price 150` |

**Beginner tips to share with users:**
- **Market order** = buy/sell right now at current price (default)
- **Limit order** = buy/sell only when price hits your target
- Crypto symbols use slash format: `BTC/USD`, `ETH/USD`, `SOL/USD`
- Stock symbols are uppercase: `AAPL`, `MSFT`, `TSLA`, `NVDA`
- For beginners, suggest starting with small amounts ($100-500 per trade)

### Portfolio & Account

| User says | Command |
|-----------|---------|
| "how's my portfolio?" | `account` |
| "show my positions" | `pos` |
| "what stocks do I own?" | `pos` |
| "how much can I spend?" | `account` (check buying power) |
| "show my orders" | `orders` |
| "show my trade history" | `history` |
| "close everything" | `close all` |

### Market Data

| User says | Command |
|-----------|---------|
| "what's Apple trading at?" | `quote AAPL` |
| "check Bitcoin price" | `quote BTC/USD` |
| "show me some stocks to watch" | `watch` (default: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META) |
| "watch these: AAPL TSLA NVDA" | `watch AAPL TSLA NVDA` |

### JSON Output (for scripting)

All commands support `-o json` for machine-readable output:
```bash
trade.py pos -o json
trade.py account -o json
```

## Step 3: Strategies — Automated Trading for Beginners

Strategies run automatically via a cron tick. The user describes what they want, you set it up.

**Strategy CLI**: `trade.py strat <action>`

### Available Strategies (explained simply)

**DCA (Dollar Cost Averaging)** — "Buy a little bit regularly"
- Best for: Building a long-term position in a stock you believe in
- How it works: Buys a fixed dollar amount at regular intervals, regardless of price
- Example: "Buy $200 of SPY every 30 minutes"
```bash
trade.py strat add dca my-spy-dca SPY --capital 5000
```
Config: `amount_per_buy=200`, `interval_minutes=30`

**Grid Trading** — "Buy low, sell high, repeat"
- Best for: Sideways/ranging markets, crypto
- How it works: Places buy orders below current price and sell orders above. When one fills, it places the opposite order. Profits from price bouncing around.
- Example: "Grid trade NVDA with 10 levels"
```bash
trade.py strat add grid my-nvda-grid NVDA --capital 10000
```
Config: `grid_pct=6`, `num_grids=10`, `qty_per_grid=2`

**Momentum** — "Ride the winners"
- Best for: Active markets, catching trends
- How it works: Ranks a list of stocks by recent price change. Buys the top gainers, sells the losers.
- Example: "Pick the top 3 movers from tech stocks"
```bash
trade.py strat add momentum my-tech-momo AAPL --capital 10000
```
Config: `symbols=["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","AMD","NFLX"]`, `top_n=3`

**Mean Reversion** — "Buy when it dips, sell when it bounces"
- Best for: Stable stocks that tend to return to average
- How it works: Tracks rolling average price. Buys when price drops below average, sells when it rises above.
- Example: "Trade AAPL mean reversion"
```bash
trade.py strat add mean_reversion my-aapl-mr AAPL --capital 5000
```

**Dip Buyer** — "Buy the dip!"
- Best for: Crypto, volatile stocks
- How it works: Watches price, buys small amounts when it dips below the rolling average
- Example: "Buy Bitcoin dips"
```bash
trade.py strat add dip_buyer my-btc-dip BTC/USD --capital 2000
```

**Momentum Scalper** — "Quick in, quick out"
- Best for: Crypto (runs 24/7), fast-moving assets
- How it works: Measures price velocity, buys when momentum accelerates upward, sells when the move slows
```bash
trade.py strat add momentum_scalper my-btc-scalp BTC/USD --capital 1000
```

### Managing Strategies

| User says | Command |
|-----------|---------|
| "show my strategies" | `strat list` |
| "pause my grid strategy" | `strat pause my-nvda-grid` |
| "resume it" | `strat resume my-nvda-grid` |
| "remove the DCA" | `strat remove my-spy-dca` |
| "run one tick cycle" | `strat tick` |

## Step 4: Cron — Automated Execution & Trade Logging

Strategies need periodic ticking to execute. Set up a cron job for this.

### Strategy Tick Cron

The tick runner (`tick.py`) runs all active strategies once per cycle:
```bash
/root/.openclaw/skills/paper-trade/.venv/bin/python /root/.openclaw/skills/paper-trade/tick.py
```
- Checks if market is open (stocks) or runs 24/7 (crypto)
- Ticks each active strategy
- Logs results to `strategy_manager.log`

Recommended cron schedule: every 5 minutes during market hours, every 15 minutes for crypto-only.

### Trade Log

Every execution appends to `trade_log.txt` with timestamped entries. The log script generates a summary:
```bash
/root/.openclaw/skills/paper-trade/.venv/bin/python /root/.openclaw/skills/paper-trade/scripts/log_trades.py
```
Returns JSON with: account summary, open positions, active strategies, and recent fills.

### Notification Cron

To keep the user informed, set up a cron that runs the log script and delivers a summary. Example cron message:

```
Run the paper trading status check.
1. Run: /root/.openclaw/skills/paper-trade/.venv/bin/python /root/.openclaw/skills/paper-trade/scripts/log_trades.py
2. Parse the JSON output.
3. Format a concise status update:
   - Account equity and today's P&L
   - Open positions with unrealized P&L
   - Active strategies and their performance
   - Any recent fills (last hour)
4. Only report if there are positions or active strategies. Skip if account is idle.
```

## Step 5: Live Dashboard

For users who want a real-time terminal view:
```bash
cd /root/.openclaw/skills/paper-trade && ./run.sh
```
Bloomberg-style TUI with live positions, orders, strategies, and watchlist panels.

## Key Rules

1. **Paper trading ONLY** — hardcoded to `https://paper-api.alpaca.markets`. No live trading, no real money risk.
2. **Beginner-friendly language** — avoid jargon. If you must use a term (like "limit order"), explain it in one sentence.
3. **Warn on large orders** — if a single trade would use >25% of buying power, mention it's a big trade and confirm intent.
4. **Crypto symbols use slash**: `BTC/USD`, `ETH/USD`, `SOL/USD`
5. **Stock symbols are uppercase**: `AAPL`, `MSFT`, `TSLA`
6. **Log every action** — after any trade or strategy change, append to `trade_log.txt`
7. **Always show P&L context** — when showing positions, include unrealized P&L so users know how they're doing.
8. **Suggest learning** — when a user tries something new (first limit order, first strategy), briefly explain what it does and why.

## Data Files

| File | Purpose |
|------|---------|
| `config.json` | API keys (chmod 600, gitignored) |
| `trade_log.txt` | Timestamped trade log (gitignored) |
| `strategies_state.json` | Strategy state persistence (gitignored) |
| `strategy_manager.log` | Strategy execution log (gitignored) |
| `watchlist.json` | Custom watchlist symbols |

## Architecture

```
paper-trade/
├── SKILL.md              # This file — Claude Code skill definition
├── trade.py              # Main CLI entry point (trade.py <command>)
├── tick.py               # Cron tick runner for strategies
├── strategy_manager.py   # Multi-strategy orchestrator
├── dashboard.py          # Bloomberg-style TUI dashboard
├── grid_bot.py           # Legacy standalone grid bot
├── strategies/
│   ├── base.py           # Abstract strategy base class
│   ├── grid.py           # Grid trading
│   ├── dca.py            # Dollar cost averaging
│   ├── momentum.py       # Momentum/trend following
│   ├── mean_reversion.py # Mean reversion
│   ├── dip_buyer.py      # Buy-the-dip
│   └── momentum_scalper.py # Quick momentum scalping
├── scripts/
│   ├── install.sh        # Installation script
│   └── log_trades.py     # Trade logging for cron notifications
├── alpaca_cli/            # Click-based CLI (alternative interface)
├── config.example.json   # Template for API keys
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
└── tests/
    ├── test_trade.py     # CLI unit tests
    └── test_strategies.py # Strategy logic tests
```
