# main_async.py
import asyncio
import logging
import datetime
import io
import sys

from src.data_feed import DataFeed
from src.candle_builder import CandleBuilder
from src.indicators import VWAPCalculator
from src.strategy import VWAPStrategy
from src.fyers_integration import FyersIntegration

# ─────────────────────────────────────────────────────────────
# 1) Logging (console UTF‑8 + file)
# ─────────────────────────────────────────────────────────────
utf8_stdout = io.TextIOWrapper(sys.stdout.buffer,
                               encoding="utf-8",
                               errors="replace")

LOG_FMT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(utf8_stdout),
        logging.FileHandler("bot.log", mode="a", encoding="utf-8"),
    ],
)

# Module‑specific levels
logging.getLogger("VWAPCalc").setLevel(logging.DEBUG)
logging.getLogger("DataFeed").setLevel(logging.INFO)
logging.getLogger("CandleBuilder").setLevel(logging.INFO)
logging.getLogger("Strategy").setLevel(logging.INFO)
logging.getLogger("FyersREST").setLevel(logging.INFO)

log = logging.getLogger("Main")

# ─────────────────────────────────────────────────────────────
# 2) Symbols & helper queues
# ─────────────────────────────────────────────────────────────
SYMBOLS = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ"]


# ─────────────────────────────────────────────────────────────
# 3) Strategy consumer (runs per completed bar)
# ─────────────────────────────────────────────────────────────
async def consumer(bar_q: asyncio.Queue):
    intg = FyersIntegration()
    fy = intg.fyers()                     # REST client
    vwap = {s: VWAPCalculator() for s in SYMBOLS}
    strat = VWAPStrategy(max_trades_per_day=2,
                         start_entry_time="09:40",
                         end_entry_time="14:00")
    prev = {s: None for s in SYMBOLS}

    try:
        while True:
            sym, bar = await bar_q.get()
            ind = vwap[sym].update(bar)
            hhmm = datetime.datetime.now().strftime("%H:%M")
            if prev[sym]:
                strat.on_bar(
                    symbol=sym,
                    prev_bar=prev[sym],
                    curr_bar=bar,
                    indicator=ind,
                    hhmm=hhmm,
                    place=lambda order: intg.place_order(fy, order),
                )
            prev[sym] = bar
    except asyncio.CancelledError:
        log.info("Strategy task cancelled.")
        raise


# ─────────────────────────────────────────────────────────────
# 4) Main async entry point
# ─────────────────────────────────────────────────────────────
async def main():
    tick_q = asyncio.Queue(10000)
    bar_q = asyncio.Queue(10000)

    feed = DataFeed(SYMBOLS, tick_q)
    builder = CandleBuilder(tick_q, bar_q)

    tasks = [
        asyncio.create_task(feed.run(), name="DataFeed"),
        asyncio.create_task(builder.run(), name="CandleBuilder"),
        asyncio.create_task(consumer(bar_q), name="Strategy"),
    ]

    # Wait until cancelled (Ctrl+C) or until any task raises.
    try:
        await asyncio.gather(*tasks)
    finally:
        # Ensure all tasks are cancelled on exit path
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        log.info("Shutdown complete — bye!")


# ─────────────────────────────────────────────────────────────
# 5) Synchronous launcher with clean Ctrl+C
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Ctrl+C outside event‑loop fallback
        # (rare, because asyncio.run already handles SIGINT)
        log.info("KeyboardInterrupt — terminated.")
