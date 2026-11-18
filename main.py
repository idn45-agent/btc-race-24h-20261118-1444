"""Dip-buy mean-reversion bot for btc-race-24h-20261118-1444 (cbBTC/USDC, 1m bars).

Idea: on a 1-minute chart BTC's sharp intraday drops tend to retrace within
the hour, while a full round trip costs only ~26 bps (4 bps fee + 2 bps
slippage + ~7 bps impact each way, plus the fill lag). So the bot sits in
cash, waits for a steep fall over the last hour, buys the whole equity, and
sells either when the price has climbed back a set amount or when it keeps
falling past a hard stop. No leverage, no shorts, one position at a time.

Entry (flat only):  close <= close[LOOKBACK] * (1 - DROP_BPS / 10000)
Exit  (holding):   close >= entry_close * (1 + RECOVER_BPS / 10000)  -> take profit
                   close <= entry_close * (1 - STOP_BPS / 10000)     -> hard stop
                   trailing: once the close has risen ARM_BPS above the
                   entry, sell when it falls TRAIL_BPS back from the best
                   close seen since entry (lets a good bounce run, cuts a
                   stalled one before it rolls over)
                   no new entries in the last NO_ENTRY_LAST_BARS bars,
                   so a fresh position is never forced to flatten at the
                   window's end before it has had time to work.
Safety: no new entries once equity has drawn down 10% from its peak, and an
open position is closed if equity falls 15% from its peak. That bounds the
worst case to roughly a dip-buy that keeps sliding.

Deterministic: pure integer math on closes, no clock, no randomness, no
network, no files. Standard library only, via the vendored kit shim.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- strategy parameters (tuned on the dev window, plateau centre) ---
LOOKBACK = 110       # bars back for the drop measurement (~2 hours)
DROP_BPS = 100       # buy when the close fell this far below LOOKBACK bars ago
RECOVER_BPS = 100    # sell when the close recovered this far above the entry
STOP_BPS = 150       # sell when the close fell this far below the entry
MAX_SLIP_BPS = 300   # max slippage allowed on any order (vs latest close)
HALT_DD_BPS = 1000   # stop opening new trades past this equity drawdown
EXIT_DD_BPS = 1500   # close an open position past this equity drawdown
ARM_BPS = 50         # arm the trailing exit once the close is this far above entry
TRAIL_BPS = 50       # sell when the close falls this far back from its post-entry peak
NO_ENTRY_LAST_BARS = 120  # do not open a new position this close to the window's end
WINDOW_BARS = 1440   # bars in the dev and race windows (competition rules)

closes = []          # closes seen so far, ints (price_scale 5)
entry_close = None   # close at which the current position was opened
peak_close = None    # best close seen since the current entry
peak_equity = None   # highest equity seen, in quote units


def _drawdown_bps(equity):
    global peak_equity
    if peak_equity is None or equity > peak_equity:
        peak_equity = equity
    if peak_equity <= 0:
        return 0
    return (peak_equity - equity) * 10_000 // peak_equity


def on_batch(state, batch):
    global entry_close, peak_close
    close = state.close(SYMBOL)
    if close is None or state.warming_up:
        return []
    closes.append(close)
    dd = _drawdown_bps(state.equity)
    holding = state.positions.get(SYMBOL)

    if holding is not None:
        if entry_close is None:
            # Position opened before this process saw it (should not happen
            # in a fresh run); anchor on the first close we see.
            entry_close = close
            peak_close = close
        if peak_close is None or close > peak_close:
            peak_close = close
        sell = False
        if dd >= EXIT_DD_BPS:
            sell = True
        if close * 10_000 >= entry_close * (10_000 + RECOVER_BPS):
            sell = True
        if close * 10_000 <= entry_close * (10_000 - STOP_BPS):
            sell = True
        if (peak_close * 10_000 >= entry_close * (10_000 + ARM_BPS)
                and close * 10_000 <= peak_close * (10_000 - TRAIL_BPS)):
            sell = True
        if sell:
            entry_close = None
            peak_close = None
            return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                     "max_slippage_bps": MAX_SLIP_BPS}]
        return []

    # Flat: look for a dip to buy.
    if dd >= HALT_DD_BPS:
        return []
    if len(closes) <= LOOKBACK:
        return []
    if len(closes) > WINDOW_BARS - NO_ENTRY_LAST_BARS:
        return []
    ref = closes[-1 - LOOKBACK]
    if close * 10_000 <= ref * (10_000 - DROP_BPS):
        amount = state.cash
        room = state.weight_room(SYMBOL)
        if room < amount:
            amount = room
        if amount <= 0:
            return []
        entry_close = close
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": amount,
                 "max_slippage_bps": MAX_SLIP_BPS}]
    return []


makefun_bars.run(on_batch)
