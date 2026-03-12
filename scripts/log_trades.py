#!/usr/bin/env python3
"""Trade logger — generates a JSON status summary for cron notifications.

Outputs a JSON object with:
  - account: equity, cash, buying_power, today_pnl
  - positions: list of open positions with P&L
  - strategies: list of active strategies with performance
  - recent_fills: trades filled in the last hour
  - timestamp: when this report was generated

Usage:
  python scripts/log_trades.py              # Full status
  python scripts/log_trades.py --brief      # One-line summary
  python scripts/log_trades.py --log-only   # Append to trade_log.txt, no stdout
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_SITE = SKILL_DIR / ".venv/lib"
for p in sorted(VENV_SITE.glob("python*/site-packages")):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import alpaca_trade_api as tradeapi

CONFIG_PATH = SKILL_DIR / "config.json"
LOG_PATH = SKILL_DIR / "trade_log.txt"


def get_api():
    """Create Alpaca API client from config."""
    if not CONFIG_PATH.exists():
        print(json.dumps({"error": "Not configured. Run setup first."}))
        sys.exit(1)
    cfg = json.loads(CONFIG_PATH.read_text())
    return tradeapi.REST(
        cfg["api_key"], cfg["secret_key"],
        base_url="https://paper-api.alpaca.markets",
        api_version="v2"
    )


def get_account_summary(api):
    """Get account summary dict."""
    a = api.get_account()
    equity = float(a.equity)
    last_equity = float(a.last_equity)
    pnl = equity - last_equity
    pnl_pct = (pnl / last_equity * 100) if last_equity > 0 else 0
    return {
        "equity": round(equity, 2),
        "cash": round(float(a.cash), 2),
        "buying_power": round(float(a.buying_power), 2),
        "today_pnl": round(pnl, 2),
        "today_pnl_pct": round(pnl_pct, 2),
        "status": a.status,
    }


def get_positions(api):
    """Get list of open positions."""
    positions = api.list_positions()
    result = []
    for p in positions:
        result.append({
            "symbol": p.symbol,
            "qty": str(p.qty),
            "avg_entry": round(float(p.avg_entry_price), 2),
            "current_price": round(float(p.current_price), 2),
            "market_value": round(float(p.market_value), 2),
            "unrealized_pnl": round(float(p.unrealized_pl), 2),
            "unrealized_pnl_pct": round(float(p.unrealized_plpc) * 100, 2),
        })
    return result


def get_recent_fills(api, hours=1):
    """Get fills from the last N hours."""
    activities = api.get_activities(activity_types="FILL", direction="desc")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    for a in activities:
        try:
            t = a.transaction_time
            if hasattr(t, 'tzinfo') and t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t < cutoff:
                break
            recent.append({
                "symbol": a.symbol,
                "side": a.side,
                "qty": str(a.qty),
                "price": round(float(a.price), 2),
                "time": str(a.transaction_time)[:19],
            })
        except (AttributeError, TypeError):
            continue
    return recent


def get_strategies_summary():
    """Get strategy summary from strategy_manager."""
    try:
        from strategy_manager import StrategyManager
        sm = StrategyManager()
        strategies = sm.list_strategies()
        return [s for s in strategies if s["status"] in ("active", "pending", "paused")]
    except Exception:
        return []


def append_log(summary):
    """Append a one-line summary to trade_log.txt."""
    ts = datetime.now().strftime("%m/%d %H:%M:%S")
    acct = summary["account"]
    n_pos = len(summary["positions"])
    n_strat = len(summary["strategies"])
    n_fills = len(summary["recent_fills"])

    pnl = acct["today_pnl"]
    sign = "+" if pnl >= 0 else ""
    line = (f"{ts}  STATUS  equity=${acct['equity']:,.2f}  "
            f"pnl={sign}${pnl:,.2f} ({sign}{acct['today_pnl_pct']:.1f}%)  "
            f"positions={n_pos}  strategies={n_strat}  "
            f"recent_fills={n_fills}\n")

    with open(LOG_PATH, "a") as f:
        f.write(line)

    # Also log individual fills
    for fill in summary["recent_fills"]:
        fill_line = (f"{ts}  FILL {fill['side'].upper():<4} "
                     f"{fill['symbol']} x{fill['qty']} @ ${fill['price']:,.2f}\n")
        with open(LOG_PATH, "a") as f:
            f.write(fill_line)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Paper trading status logger")
    parser.add_argument("--brief", action="store_true", help="One-line summary only")
    parser.add_argument("--log-only", action="store_true", help="Append to log, no stdout")
    args = parser.parse_args()

    api = get_api()

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account": get_account_summary(api),
        "positions": get_positions(api),
        "strategies": get_strategies_summary(),
        "recent_fills": get_recent_fills(api),
    }

    # Always append to log
    append_log(summary)

    if args.log_only:
        return

    if args.brief:
        acct = summary["account"]
        pnl = acct["today_pnl"]
        sign = "+" if pnl >= 0 else ""
        print(f"Equity: ${acct['equity']:,.2f} | "
              f"P&L: {sign}${pnl:,.2f} ({sign}{acct['today_pnl_pct']:.1f}%) | "
              f"Positions: {len(summary['positions'])} | "
              f"Strategies: {len(summary['strategies'])}")
    else:
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
