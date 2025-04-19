# main.py

import time
import logging
from datetime import datetime
from src.fyers_integration import FyersIntegration
from src.indicators import VWAPCalculator
from src.strategy import VWAPStrategy

# Example constants
SYMBOLS_TO_TRADE = ["NSE:RELIANCE-EQ"]
MAX_TRADES_PER_DAY = 2
START_ENTRY_TIME = "09:40"
END_ENTRY_TIME   = "14:00"
FORCE_EXIT_TIME  = "14:30"
MARKET_CLOSE_TIME= "15:30"

def hhmm():
    return datetime.now().strftime("%H:%M")

def run_bot():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

    integration = FyersIntegration()
    try:
        fyers = integration.get_fyers_instance()
    except ValueError as e:
        logging.error(f"Access token error: {e}")
        logging.error("Run 'python auth_server.py' first to authenticate.")
        return

    strategy = VWAPStrategy(
        max_trades_per_day=MAX_TRADES_PER_DAY,
        start_entry_time=START_ENTRY_TIME,
        end_entry_time=END_ENTRY_TIME
    )

    # We'll do incremental VWAP
    vwap_calcs = {s: VWAPCalculator() for s in SYMBOLS_TO_TRADE}
    candle_cache = {s: [] for s in SYMBOLS_TO_TRADE}

    logging.info(f"Starting the strategy with {SYMBOLS_TO_TRADE}")

    while True:
        now_str = hhmm()
        if now_str >= MARKET_CLOSE_TIME:
            logging.info("Market close. Exiting script.")
            # If you want to forcibly close positions, do it here.
            break

        if now_str >= FORCE_EXIT_TIME:
            logging.info("Force exit time. If you want to exit open trades, do it here.")

        # For each symbol, get the last N minutes of data (we only need a small chunk)
        for sym in SYMBOLS_TO_TRADE:
            new_candles = integration.get_candle_data(fyers, sym, resolution="3", minutes_back=30)

            if not new_candles:
                continue

            # Compare the last candle in candle_cache to see if there's a new timestamp
            # We'll handle only the *last* item from new_candles
            last_timestamp = candle_cache[sym][-1][0] if candle_cache[sym] else -1
            last_candle = new_candles[-1]  # pick the final candle
            if last_candle[0] > last_timestamp:
                # It's a new candle
                candle_cache[sym].append(last_candle)
                indicator_output = vwap_calcs[sym].update(last_candle)

                # If we have at least 2 candles in the cache, do strategy
                if len(candle_cache[sym]) >= 2:
                    prev_candle = candle_cache[sym][-2]
                    curr_candle = candle_cache[sym][-1]
                    strategy.on_new_candle(
                        symbol=sym,
                        prev_candle=prev_candle,
                        curr_candle=curr_candle,
                        indicator_output=indicator_output,
                        hhmm_str=now_str,
                        place_order_fn=lambda od: integration.place_order(fyers, od)
                    )
        time.sleep(10)

if __name__ == "__main__":
    run_bot()
