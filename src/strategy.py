# strategy.py
import logging

log = logging.getLogger("Strategy")


def thickness_pct(o, h, l, c) -> float:
    """Return candle body thickness as % of total range."""
    return 0 if h == l else abs(c - o) / (h - l) * 100


class Trade:
    def __init__(self, side: str, entry: float, sl: float, qty: int):
        self.side = side          # "BUY" or "SELL"
        self.entry_price = entry
        self.stop_loss = sl
        self.qty = qty
        self.active = True


class VWAPStrategy:
    """
    VWAP‑3‑band strategy with daily limits and simple fixed‑risk sizing.
    """

    def __init__(
        self,
        max_trades_per_day: int = 2,
        start_entry_time: str = "09:40",
        end_entry_time: str = "14:00",
    ):
        self.max_per_day = max_trades_per_day
        self.start = start_entry_time
        self.end = end_entry_time

        self.trades_taken = 0
        self.open_trades = {}    # symbol -> Trade

    # ---------- helpers ----------
    def _can_enter(self, hhmm: str) -> bool:
        return (
            self.trades_taken < self.max_per_day
            and self.start <= hhmm <= self.end
        )

    def _signal(self, prev_bar, up1: float, dn1: float, mid: float):
        _, o, h, l, c, _ = prev_bar
        if thickness_pct(o, h, l, c) < 60:
            return None, None
        if c > o and o >= up1:
            return "BUY", mid
        if c < o and o <= dn1:
            return "SELL", mid
        return None, None

    @staticmethod
    def _sl(side, mid):
        return mid * 0.9998 if side == "BUY" else mid * 1.0002

    @staticmethod
    def _qty(entry, sl, risk=5_000):
        dist = abs(entry - sl)
        return max(int(risk // dist), 1) if dist else 0

    # ---------- main entry point ----------
    def on_bar(
        self,
        symbol: str,
        prev_bar,
        curr_bar,
        indicator: dict,
        hhmm: str,
        *,
        place,
    ):
        """
        Called once per completed 3‑min bar.

        • place(order_dict) — callback that sends the REST order.
        """
        up1, dn1 = indicator["bands"][0]
        side, mid = self._signal(prev_bar, up1, dn1, indicator["vwap"])

        if side and self._can_enter(hhmm):
            entry = curr_bar[1]             # open of current bar
            sl = self._sl(side, mid)
            qty = self._qty(entry, sl)

            order = {
                "symbol": symbol,
                "qty": qty,
                "type": 2,                        # MARKET
                "side": 1 if side == "BUY" else -1,
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False",
                "stopLoss": 0,
                "takeProfit": 0,
            }
            place(order)
            log.info(
                f"{symbol} {side} sent  qty={qty}  entry={entry:.2f}  SL={sl:.2f}"
            )

            self.open_trades[symbol] = Trade(side, entry, sl, qty)
            self.trades_taken += 1

        # placeholder for trailing‑stop / partial‑exit management
        if symbol in self.open_trades:
            self._update_trade(self.open_trades[symbol], curr_bar)

    # ---------- extension point ----------
    def _update_trade(self, trade: Trade, curr_bar):
        """Add trailing‑stop / TP logic here."""
        pass
