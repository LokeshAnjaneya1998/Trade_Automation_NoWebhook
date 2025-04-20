# data_feed.py
import asyncio
import datetime
import logging
import pytz

from fyers_apiv3.FyersWebsocket import data_ws
from src.fyers_integration import FyersIntegration, IST

log = logging.getLogger("DataFeed")


class DataFeed:
    """
    • Back‑fills N days of historical 3‑minute candles via REST.
    • Streams live ticks via FyersDataSocket (SymbolUpdate).
    • Pushes both into an asyncio.Queue → consumed by CandleBuilder.
    """

    def __init__(self, symbols, tick_queue: asyncio.Queue, days_back: int = 5):
        self.symbols = symbols
        self.tick_q = tick_queue
        self.days_back = days_back

        self.intg = FyersIntegration()
        self.fy = self.intg.fyers()
        self.ws = None

    # ─────────────────────────────────────────────────────────
    # REST back‑fill
    # ─────────────────────────────────────────────────────────
    def backfill(self, resolution: str = "3"):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=self.days_back)

        for sym in self.symbols:
            resp = self.intg.history(
                self.fy,
                symbol=sym,
                resolution=resolution,
                date_from=start.strftime("%Y-%m-%d"),
                date_to=today.strftime("%Y-%m-%d"),
            )
            if resp.get("s") == "ok":
                log.info(f"Back‑filled {sym}: {len(resp['candles'])} bars")
                for bar in resp["candles"]:
                    self.tick_q.put_nowait({"symbol": sym, "bar": bar})
            else:
                log.error(f"Back‑fill failed {sym}: {resp}")

    # ─────────────────────────────────────────────────────────
    # WebSocket helpers
    # ─────────────────────────────────────────────────────────
    async def _connect_ws(self):
        token = f"{self.intg.cfg.client_id}:{self.intg.cfg.access_token}"

        def on_message(msg):
            if msg.get("type") != "symbolUpdate":
                return
            for t in msg["data"]:
                self.tick_q.put_nowait({"symbol": t["symbol"], "tick": t})

        def on_open():
            log.info("WebSocket connected")
            self.ws.subscribe(self.symbols, data_type="SymbolUpdate")

        def on_close(msg):
            log.warning(f"WebSocket closed: {msg}")

        def on_error(err):
            log.error(f"WebSocket error: {err}")

        self.ws = data_ws.FyersDataSocket(
            access_token=token,
            log_path="logfiles",
            litemode=False,
            reconnect=True,
            on_connect=on_open,
            on_close=on_close,
            on_error=on_error,
            on_message=on_message,
        )
        # .connect() starts an internal thread and returns immediately
        self.ws.connect()

    # ─────────────────────────────────────────────────────────
    # Public coroutine
    # ─────────────────────────────────────────────────────────
    async def run(self):
        try:
            self.backfill()
            await self._connect_ws()

            # Keep coroutine alive indefinitely; cancellation will break the wait.
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            log.info("DataFeed task cancelled — closing WebSocket …")
            # Close the socket thread gracefully
            if self.ws:
                if hasattr(self.ws, "close_connection"):
                    self.ws.close_connection()
                elif hasattr(self.ws, "disconnect"):
                    self.ws.disconnect()
            raise
