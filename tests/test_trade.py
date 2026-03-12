"""Tests for trade.py CLI — core functionality without requiring live API."""

import json
import sys
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Add skill directory to path
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

VENV_SITE = SKILL_DIR / ".venv/lib"
for p in sorted(VENV_SITE.glob("python*/site-packages")):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class TestConfig:
    """Test configuration resolution."""

    def test_resolve_config_from_file(self, tmp_path):
        """Config file is read correctly."""
        import trade
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({
            "api_key": "test-key-123",
            "secret_key": "test-secret-456",
        }))

        original = trade.CONFIG_PATH
        trade.CONFIG_PATH = cfg_file
        try:
            key, secret, source = trade.resolve_config()
            assert key == "test-key-123"
            assert secret == "test-secret-456"
            assert source == "config file"
        finally:
            trade.CONFIG_PATH = original

    def test_resolve_config_env_overrides_file(self, tmp_path):
        """Environment variables override config file."""
        import trade
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({
            "api_key": "file-key",
            "secret_key": "file-secret",
        }))

        original = trade.CONFIG_PATH
        trade.CONFIG_PATH = cfg_file
        try:
            with mock.patch.dict(os.environ, {
                "ALPACA_API_KEY": "env-key",
                "ALPACA_SECRET_KEY": "env-secret",
            }):
                key, secret, source = trade.resolve_config()
                assert key == "env-key"
                assert secret == "env-secret"
                assert source == "environment"
        finally:
            trade.CONFIG_PATH = original

    def test_resolve_config_missing_file(self, tmp_path):
        """Returns None when no config exists."""
        import trade
        original = trade.CONFIG_PATH
        trade.CONFIG_PATH = tmp_path / "nonexistent.json"
        try:
            with mock.patch.dict(os.environ, {}, clear=True):
                # Remove any ALPACA env vars
                env_clean = {k: v for k, v in os.environ.items()
                             if not k.startswith("ALPACA_")}
                with mock.patch.dict(os.environ, env_clean, clear=True):
                    key, secret, source = trade.resolve_config()
                    assert key is None
                    assert source == "none"
        finally:
            trade.CONFIG_PATH = original


class TestFormatting:
    """Test output formatting functions."""

    def test_fmt_money_small(self):
        import trade
        assert trade.fmt_money(42.50) == "$42.50"
        assert trade.fmt_money(0) == "$0.00"

    def test_fmt_money_thousands(self):
        import trade
        result = trade.fmt_money(15000)
        assert "15" in result
        assert "K" in result

    def test_fmt_money_millions(self):
        import trade
        result = trade.fmt_money(2500000)
        assert "2.5M" in result

    def test_fmt_money_negative(self):
        import trade
        result = trade.fmt_money(-500)
        assert "-" in result

    def test_fmt_pnl_positive(self):
        import trade
        result = trade.fmt_pnl(100)
        assert "green" in result
        assert "+" in result

    def test_fmt_pnl_negative(self):
        import trade
        result = trade.fmt_pnl(-50)
        assert "red" in result

    def test_fmt_side_buy(self):
        import trade
        result = trade.fmt_side("buy")
        assert "green" in result
        assert "BUY" in result

    def test_fmt_side_sell(self):
        import trade
        result = trade.fmt_side("sell")
        assert "red" in result
        assert "SELL" in result

    def test_fmt_status_filled(self):
        import trade
        result = trade.fmt_status("filled")
        assert "green" in result

    def test_fmt_status_rejected(self):
        import trade
        result = trade.fmt_status("rejected")
        assert "red" in result


class TestParser:
    """Test CLI argument parsing."""

    def test_build_parser(self):
        import trade
        parser = trade.build_parser()
        assert parser is not None
        assert parser.prog == "trade"

    def test_parse_buy(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["buy", "AAPL", "--qty", "10"])
        assert args.command == "buy"
        assert args.symbol == "AAPL"
        assert args.qty == 10.0

    def test_parse_buy_notional(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["buy", "TSLA", "--notional", "500"])
        assert args.command == "buy"
        assert args.symbol == "TSLA"
        assert args.notional == 500.0

    def test_parse_sell(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["sell", "MSFT", "--qty", "5"])
        assert args.command == "sell"
        assert args.symbol == "MSFT"
        assert args.qty == 5.0

    def test_parse_buy_limit(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["buy", "AAPL", "--qty", "10",
                                  "--type", "limit", "--limit-price", "150"])
        assert args.type == "limit"
        assert args.limit_price == 150.0

    def test_parse_account(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["account"])
        assert args.command == "account"

    def test_parse_pos_alias(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["pos"])
        assert args.command == "pos"

    def test_parse_quote(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["quote", "AAPL", "TSLA"])
        assert args.command == "quote"
        assert args.symbols == ["AAPL", "TSLA"]

    def test_parse_orders_with_status(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["orders", "--status", "open"])
        assert args.command == "orders"
        assert args.status == "open"

    def test_parse_close(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["close", "all"])
        assert args.command == "close"
        assert args.symbol == "all"

    def test_parse_cancel(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["cancel", "all"])
        assert args.command == "cancel"
        assert args.order_id == "all"

    def test_parse_strat_add(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["strat", "add", "grid", "my-grid", "NVDA",
                                  "--capital", "5000"])
        assert args.command == "strat"
        assert args.strat_action == "add"
        assert args.type == "grid"
        assert args.name == "my-grid"
        assert args.symbol == "NVDA"
        assert args.capital == 5000.0

    def test_parse_strat_list(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["strat", "list"])
        assert args.command == "strat"
        assert args.strat_action == "list"

    def test_parse_json_output(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["account", "-o", "json"])
        assert args.output == "json"

    def test_parse_watch_no_symbols(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["watch"])
        assert args.command == "watch"
        assert args.symbols == []

    def test_parse_watch_with_symbols(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["watch", "AAPL", "TSLA"])
        assert args.symbols == ["AAPL", "TSLA"]

    def test_parse_history_limit(self):
        import trade
        parser = trade.build_parser()
        args = parser.parse_args(["history", "--limit", "50"])
        assert args.limit == 50

    def test_dispatch_unknown_command(self):
        """Unknown command prints help without crashing."""
        import trade
        parser = trade.build_parser()
        args = parser.parse_args([])
        # Should not raise
        trade.dispatch(args)


class TestDispatch:
    """Test command dispatch mapping."""

    def test_all_commands_have_handlers(self):
        import trade
        commands = {
            "setup", "account", "acc", "buy", "sell", "positions", "pos",
            "orders", "cancel", "quote", "history", "close", "watch",
            "shell", "grid", "strat", "dashboard", "dash",
        }
        parser = trade.build_parser()
        # Check dispatch dict has all these
        dispatch_map = {
            "setup": trade.cmd_setup,
            "account": trade.cmd_account,
            "acc": trade.cmd_account,
            "buy": trade.cmd_buy,
            "sell": trade.cmd_sell,
            "positions": trade.cmd_positions,
            "pos": trade.cmd_positions,
            "orders": trade.cmd_orders,
            "cancel": trade.cmd_cancel,
            "quote": trade.cmd_quote,
            "history": trade.cmd_history,
            "close": trade.cmd_close,
            "watch": trade.cmd_watch,
            "shell": trade.cmd_shell,
            "grid": trade.cmd_grid,
            "strat": trade.cmd_strat,
            "dashboard": trade.cmd_dashboard,
            "dash": trade.cmd_dashboard,
        }
        for cmd in commands:
            assert cmd in dispatch_map, f"Missing handler for '{cmd}'"
