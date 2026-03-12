"""Tests for strategy classes — logic tests without requiring live API."""

import json
import sys
import os
import tempfile
from pathlib import Path
from unittest import mock
from datetime import datetime, timezone, timedelta

import pytest

# Add skill directory to path
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

VENV_SITE = SKILL_DIR / ".venv/lib"
for p in sorted(VENV_SITE.glob("python*/site-packages")):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class MockPosition:
    def __init__(self, symbol, qty, avg_entry_price, current_price,
                 unrealized_pl, cost_basis):
        self.symbol = symbol
        self.qty = str(qty)
        self.avg_entry_price = str(avg_entry_price)
        self.current_price = str(current_price)
        self.unrealized_pl = str(unrealized_pl)
        self.unrealized_plpc = str(unrealized_pl / (avg_entry_price * qty)
                                    if qty > 0 else 0)
        self.market_value = str(current_price * qty)
        self.cost_basis = str(avg_entry_price * qty)


class MockOrder:
    def __init__(self, id="test-order-id", symbol="AAPL", side="buy",
                 qty=10, type="market", status="filled",
                 filled_avg_price=150.0, client_order_id=""):
        self.id = id
        self.symbol = symbol
        self.side = side
        self.qty = str(qty)
        self.type = type
        self.status = status
        self.filled_avg_price = str(filled_avg_price) if filled_avg_price else None
        self.filled_qty = str(qty)
        self.client_order_id = client_order_id
        self.limit_price = None


class MockTrade:
    def __init__(self, price):
        self.price = price


class MockAPI:
    """Mock Alpaca API for testing."""

    def __init__(self, equity=100000, positions=None, orders=None):
        self._equity = equity
        self._positions = positions or {}
        self._orders = orders or []
        self._submitted_orders = []
        self._key_id = "test-key"
        self._secret_key = "test-secret"

    def get_account(self):
        return mock.Mock(
            equity=str(self._equity),
            last_equity=str(self._equity - 100),
            cash=str(self._equity * 0.5),
            buying_power=str(self._equity * 2),
            status="ACTIVE",
        )

    def get_position(self, symbol):
        if symbol in self._positions:
            return self._positions[symbol]
        raise Exception(f"No position for {symbol}")

    def list_positions(self):
        return list(self._positions.values())

    def list_orders(self, status=None, limit=100):
        return self._orders

    def get_order(self, order_id):
        for o in self._orders:
            if o.id == order_id:
                return o
        raise Exception(f"Order {order_id} not found")

    def submit_order(self, **kwargs):
        order = MockOrder(
            id=f"order-{len(self._submitted_orders)}",
            symbol=kwargs.get("symbol", "AAPL"),
            side=kwargs.get("side", "buy"),
            qty=kwargs.get("qty", 1),
            type=kwargs.get("type", "market"),
            status="filled",
            filled_avg_price=150.0,
            client_order_id=kwargs.get("client_order_id", ""),
        )
        self._submitted_orders.append(order)
        return order

    def cancel_order(self, order_id):
        pass

    def get_latest_trade(self, symbol):
        return MockTrade(150.0)

    def get_clock(self):
        return mock.Mock(is_open=True)


# ── Strategy Base Tests ──────────────────────────────────

class TestStrategyBase:
    """Test base strategy functionality."""

    def test_create_strategy(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="test", config={"symbol": "AAPL"},
                     capital_allocated=10000)
        assert s.name == "test"
        assert s.type == "test"
        assert s.status == "pending"
        assert s.capital_allocated == 10000
        assert s.realized_pnl == 0.0

    def test_tag_order_id(self):
        from strategies.base import Strategy
        s = Strategy(name="my-strat", strategy_type="grid", config={})
        tag = s.tag_order_id("base_123")
        assert tag.startswith("grid_my-strat_")
        assert "base_123" in tag
        assert len(tag) <= 48

    def test_owns_order(self):
        from strategies.base import Strategy
        s = Strategy(name="my-strat", strategy_type="grid", config={})
        order = MockOrder(client_order_id="grid_my-strat_base_123")
        assert s._owns_order(order) is True

    def test_not_owns_order(self):
        from strategies.base import Strategy
        s = Strategy(name="my-strat", strategy_type="grid", config={})
        order = MockOrder(client_order_id="dca_other-strat_b0")
        assert s._owns_order(order) is False

    def test_to_dict_and_from_dict(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="test",
                     config={"symbol": "AAPL", "qty": 10},
                     capital_allocated=5000)
        s.status = "active"
        s.realized_pnl = 42.50
        d = s.to_dict()

        assert d["name"] == "test"
        assert d["type"] == "test"
        assert d["status"] == "active"
        assert d["realized_pnl"] == 42.50
        assert d["config"]["symbol"] == "AAPL"

        restored = Strategy.from_dict(d)
        assert restored.name == "test"
        assert restored.status == "active"
        assert restored.realized_pnl == 42.50

    def test_get_latest_price(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="test", config={})
        api = MockAPI()
        price = s._get_latest_price(api, "AAPL")
        assert price == 150.0

    def test_get_position_qty(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="test", config={})
        pos = MockPosition("AAPL", 10, 145.0, 150.0, 50.0, 1450.0)
        api = MockAPI(positions={"AAPL": pos})
        qty = s._get_position_qty(api, "AAPL")
        assert qty == 10.0

    def test_get_position_qty_none(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="test", config={})
        api = MockAPI()
        qty = s._get_position_qty(api, "AAPL")
        assert qty == 0.0

    def test_submit_order(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="test", config={})
        api = MockAPI()
        order = s._submit_order(api, symbol="AAPL", qty=5, side="buy",
                                type="market", time_in_force="day",
                                client_order_id="test_order_1")
        assert order is not None
        assert "test_order_1" in s.orders

    def test_stop_cancels_owned_orders(self):
        from strategies.base import Strategy
        s = Strategy(name="test", strategy_type="grid", config={})
        owned_order = MockOrder(id="owned-1", client_order_id="grid_test_g1")
        other_order = MockOrder(id="other-1", client_order_id="dca_other_b0")
        api = MockAPI(orders=[owned_order, other_order])
        s.stop(api)
        assert s.status == "stopped"


# ── DCA Strategy Tests ───────────────────────────────────

class TestDCAStrategy:
    """Test DCA strategy logic."""

    def test_create_dca(self):
        from strategies.dca import DCAStrategy
        s = DCAStrategy(name="my-dca", config={"symbol": "SPY",
                        "amount_per_buy": 200, "interval_minutes": 60},
                        capital_allocated=5000)
        assert s.type == "dca"
        assert s.config["symbol"] == "SPY"
        assert s.config["amount_per_buy"] == 200

    def test_initialize(self):
        from strategies.dca import DCAStrategy
        s = DCAStrategy(name="my-dca", config={"symbol": "AAPL"},
                        capital_allocated=5000)
        api = MockAPI()
        s.initialize(api)
        assert s.status == "active"
        assert s.total_fills == 1  # first buy happens on init
        assert s.config["buy_count"] == 1

    def test_tick_respects_interval(self):
        from strategies.dca import DCAStrategy
        s = DCAStrategy(name="my-dca",
                        config={"symbol": "AAPL", "interval_minutes": 60,
                                "amount_per_buy": 100},
                        capital_allocated=5000)
        api = MockAPI(positions={"AAPL": MockPosition("AAPL", 1, 150, 155, 5, 150)})

        # Set status to active and record recent buy
        s.status = "active"
        s.config["last_buy_time"] = datetime.now(timezone.utc).isoformat()

        initial_fills = s.total_fills
        s.tick(api)
        # Should NOT have bought (too soon)
        assert s.total_fills == initial_fills

    def test_tick_buys_after_interval(self):
        from strategies.dca import DCAStrategy
        s = DCAStrategy(name="my-dca",
                        config={"symbol": "AAPL", "interval_minutes": 1,
                                "amount_per_buy": 100},
                        capital_allocated=5000)
        api = MockAPI(positions={"AAPL": MockPosition("AAPL", 1, 150, 155, 5, 150)})

        s.status = "active"
        # Set last buy to 2 minutes ago
        past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        s.config["last_buy_time"] = past

        initial_fills = s.total_fills
        s.tick(api)
        assert s.total_fills == initial_fills + 1

    def test_serialization(self):
        from strategies.dca import DCAStrategy
        s = DCAStrategy(name="my-dca", config={"symbol": "AAPL"},
                        capital_allocated=5000)
        s.status = "active"
        s.realized_pnl = 25.0

        d = s.to_dict()
        restored = DCAStrategy.from_dict(d)
        assert restored.name == "my-dca"
        assert restored.status == "active"
        assert restored.realized_pnl == 25.0
        assert restored.config["symbol"] == "AAPL"

    def test_get_positions(self):
        from strategies.dca import DCAStrategy
        s = DCAStrategy(name="my-dca",
                        config={"symbol": "SPY", "amount_per_buy": 200,
                                "interval_minutes": 30, "total_invested": 1000,
                                "total_shares": 5, "buy_count": 5})
        pos = s.get_positions()
        assert pos["symbol"] == "SPY"
        assert pos["avg_price"] == 200.0  # 1000 / 5
        assert pos["buy_count"] == 5


# ── Grid Strategy Tests ──────────────────────────────────

class TestGridStrategy:
    """Test grid strategy logic."""

    def test_create_grid(self):
        from strategies.grid import GridStrategy
        s = GridStrategy(name="my-grid", config={"symbol": "NVDA",
                         "grid_pct": 6, "num_grids": 10, "qty_per_grid": 2},
                         capital_allocated=10000)
        assert s.type == "grid"
        assert s.config["symbol"] == "NVDA"

    def test_compute_grid_levels(self):
        from strategies.grid import GridStrategy
        s = GridStrategy(name="test", config={"grid_pct": 10, "num_grids": 10})
        levels = s._compute_grid_levels(100.0)
        # Should have num_grids levels (excluding center)
        assert len(levels) == 10
        buy_levels = [l for l in levels if l["side"] == "buy"]
        sell_levels = [l for l in levels if l["side"] == "sell"]
        assert len(buy_levels) == 5
        assert len(sell_levels) == 5
        # Buy prices should be below center
        for l in buy_levels:
            assert l["price"] < 100.0
        # Sell prices should be above center
        for l in sell_levels:
            assert l["price"] > 100.0

    def test_is_crypto(self):
        from strategies.grid import GridStrategy
        s1 = GridStrategy(name="t1", config={"symbol": "BTC/USD"})
        assert s1._is_crypto() is True
        s2 = GridStrategy(name="t2", config={"symbol": "AAPL"})
        assert s2._is_crypto() is False

    def test_tif(self):
        from strategies.grid import GridStrategy
        s1 = GridStrategy(name="t1", config={"symbol": "ETH/USD"})
        assert s1._tif() == "gtc"
        s2 = GridStrategy(name="t2", config={"symbol": "NVDA"})
        assert s2._tif() == "day"

    def test_serialization(self):
        from strategies.grid import GridStrategy
        s = GridStrategy(name="my-grid", config={"symbol": "NVDA"},
                         capital_allocated=10000)
        s.status = "active"
        s.realized_pnl = 100.0
        s.total_fills = 5

        d = s.to_dict()
        restored = GridStrategy.from_dict(d)
        assert restored.name == "my-grid"
        assert restored.realized_pnl == 100.0
        assert restored.total_fills == 5


# ── Mean Reversion Tests ─────────────────────────────────

class TestMeanReversionStrategy:
    """Test mean reversion strategy logic."""

    def test_create(self):
        from strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy(name="test-mr",
                                  config={"symbol": "AAPL", "window": 20,
                                          "threshold_pct": 2.0, "qty": 5})
        assert s.type == "mean_reversion"
        assert s.config["threshold_pct"] == 2.0

    def test_initialize(self):
        from strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy(name="test-mr",
                                  config={"symbol": "AAPL"})
        api = MockAPI()
        s.initialize(api)
        assert s.status == "active"
        assert len(s.config["price_samples"]) == 1

    def test_get_positions(self):
        from strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy(name="test-mr",
                                  config={"symbol": "AAPL", "window": 3,
                                          "price_samples": [100, 102, 104],
                                          "position_side": "long",
                                          "entry_price": 100})
        pos = s.get_positions()
        assert pos["symbol"] == "AAPL"
        assert pos["rolling_avg"] == 102.0  # avg(100, 102, 104)
        assert pos["position_side"] == "long"


# ── Momentum Strategy Tests ──────────────────────────────

class TestMomentumStrategy:
    """Test momentum strategy logic."""

    def test_create(self):
        from strategies.momentum import MomentumStrategy
        s = MomentumStrategy(name="test-mom",
                             config={"symbols": ["AAPL", "MSFT", "TSLA"],
                                     "top_n": 2})
        assert s.type == "momentum"
        assert len(s.config["symbols"]) == 3

    def test_compute_momentum_empty(self):
        from strategies.momentum import MomentumStrategy
        s = MomentumStrategy(name="test", config={})
        s.config["price_snapshots"] = {}
        result = s._compute_momentum()
        assert result == []


# ── Dip Buyer Tests ──────────────────────────────────────

class TestDipBuyerStrategy:
    """Test dip buyer strategy logic."""

    def test_create(self):
        from strategies.dip_buyer import DipBuyerStrategy
        s = DipBuyerStrategy(name="test-dip",
                             config={"symbol": "BTC/USD", "dip_pct": 1.5,
                                     "buy_amount": 50, "max_buys": 5})
        assert s.type == "dip_buyer"
        assert s.config["dip_pct"] == 1.5

    def test_initialize(self):
        from strategies.dip_buyer import DipBuyerStrategy
        s = DipBuyerStrategy(name="test-dip",
                             config={"symbol": "AAPL"})  # Use stock to avoid crypto path
        api = MockAPI()
        s.initialize(api)
        assert s.status == "active"
        assert len(s.config["price_samples"]) == 1


# ── Momentum Scalper Tests ───────────────────────────────

class TestMomentumScalperStrategy:
    """Test momentum scalper strategy logic."""

    def test_create(self):
        from strategies.momentum_scalper import MomentumScalperStrategy
        s = MomentumScalperStrategy(name="test-scalp",
                                    config={"symbol": "BTC/USD",
                                            "trade_amount": 100})
        assert s.type == "momentum_scalper"
        assert s.config["trade_amount"] == 100


# ── Strategy Manager Tests ───────────────────────────────

class TestStrategyManager:
    """Test strategy manager orchestration."""

    def test_add_strategy(self, tmp_path):
        from strategy_manager import StrategyManager
        # Use a temp state path
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "test-dca",
                           {"symbol": "AAPL", "amount_per_buy": 100},
                           capital_allocated=5000)
            assert "test-dca" in sm.strategies
            assert sm.strategies["test-dca"].type == "dca"
        finally:
            sm_mod.STATE_PATH = original

    def test_add_duplicate_raises(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "test-dca", {"symbol": "AAPL"})
            with pytest.raises(ValueError, match="already exists"):
                sm.add_strategy("dca", "test-dca", {"symbol": "AAPL"})
        finally:
            sm_mod.STATE_PATH = original

    def test_add_unknown_type_raises(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            with pytest.raises(ValueError, match="Unknown strategy type"):
                sm.add_strategy("fake_type", "test", {"symbol": "AAPL"})
        finally:
            sm_mod.STATE_PATH = original

    def test_remove_strategy(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "test-dca", {"symbol": "AAPL"})
            sm.remove_strategy("test-dca")
            assert "test-dca" not in sm.strategies
        finally:
            sm_mod.STATE_PATH = original

    def test_list_strategies(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "s1", {"symbol": "AAPL"})
            sm.add_strategy("grid", "s2", {"symbol": "NVDA"})
            result = sm.list_strategies()
            assert len(result) == 2
            names = {s["name"] for s in result}
            assert names == {"s1", "s2"}
        finally:
            sm_mod.STATE_PATH = original

    def test_pause_resume(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "test-dca", {"symbol": "AAPL"})
            # Manually set to active for testing
            sm.strategies["test-dca"].status = "active"
            sm.save()

            sm.pause_strategy("test-dca")
            assert sm.strategies["test-dca"].status == "paused"

            sm.resume_strategy("test-dca")
            assert sm.strategies["test-dca"].status == "active"
        finally:
            sm_mod.STATE_PATH = original

    def test_persistence(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm1 = StrategyManager()
            sm1.add_strategy("dca", "persist-test",
                            {"symbol": "SPY", "amount_per_buy": 200},
                            capital_allocated=5000)
            sm1.save()

            # Load fresh
            sm2 = StrategyManager()
            assert "persist-test" in sm2.strategies
            assert sm2.strategies["persist-test"].config["symbol"] == "SPY"
        finally:
            sm_mod.STATE_PATH = original

    def test_tick_all(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "tick-test",
                           {"symbol": "AAPL", "amount_per_buy": 100})
            api = MockAPI()
            # This should initialize the pending strategy
            sm.tick_all(api)
            assert sm.strategies["tick-test"].status == "active"
        finally:
            sm_mod.STATE_PATH = original

    def test_get_summary(self, tmp_path):
        from strategy_manager import StrategyManager
        import strategy_manager as sm_mod
        original = sm_mod.STATE_PATH
        sm_mod.STATE_PATH = tmp_path / "state.json"
        try:
            sm = StrategyManager()
            sm.add_strategy("dca", "sum-test", {"symbol": "AAPL"},
                           capital_allocated=5000)
            summary = sm.get_summary()
            assert summary["total_strategies"] == 1
            assert summary["total_allocated"] == 5000
        finally:
            sm_mod.STATE_PATH = original
