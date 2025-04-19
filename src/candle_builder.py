# candle_builder.py
import asyncio, logging, datetime

RES_SEC = 180  # 3‑minute bars
log = logging.getLogger("CandleBuilder")

class CandleBuilder:
    """Aggregates ticks into 3‑min OHLCV candles."""

    def __init__(self, tick_q: asyncio.Queue, bar_q: asyncio.Queue):
        self.tq = tick_q
        self.bq = bar_q
        self.cache = {}  # symbol -> current building bar

    def _bucket(self, epoch):
        return epoch - (epoch % RES_SEC)

    async def run(self):
        try:
            while True:
                item = await self.tq.get()
                sym = item["symbol"]

                # Historical bar handed over from DataFeed
                if "bar" in item:
                    self.bq.put_nowait((sym, item["bar"]))
                    continue

                tick = item["tick"]
                epoch = tick["timestamp"] // 1000
                bucket = self._bucket(epoch)

                bar = self.cache.get(sym)
                if (not bar) or bar[0] != bucket:
                    # flush completed bar
                    if bar:
                        self.bq.put_nowait((sym, bar))
                        ts = datetime.datetime.fromtimestamp(bar[0]).strftime("%H:%M")
                        log.info(f"{sym} closed bar {ts}  O={bar[1]} C={bar[4]} Vol={bar[5]}")
                    # start new bar
                    bar = [bucket, tick["ltp"], tick["ltp"], tick["ltp"],
                           tick["ltp"], tick["volume"]]
                    self.cache[sym] = bar
                else:
                    # update existing bar
                    bar[2] = max(bar[2], tick["ltp"])   # high
                    bar[3] = min(bar[3], tick["ltp"])   # low
                    bar[4] = tick["ltp"]                # close
                    bar[5] = tick["volume"]             # cumulative vol
        except asyncio.CancelledError:
            # Flush any still‑building bars before exiting
            for sym, bar in self.cache.items():
                self.bq.put_nowait((sym, bar))
            raise
