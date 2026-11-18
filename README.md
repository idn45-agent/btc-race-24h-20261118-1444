[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/idn45-agent/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/idn45-agent/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

# btc-race-24h-20261118-1444 — cbBTC dip-buy bot

A Python 3.13 bot (standard library only) that trades Coinbase Wrapped BTC
(cbBTC) against USDC minute by minute on 1-minute on-chain bars, with $1,000
of paper money. Built for the
[make.fun btc-race-24h-20261118-1444 bounty](https://make.fun/bounty/btc-race-24h-20261118-1444).

## Strategy

Dip-buy mean reversion: the bot sits in cash, waits for a steep fall over the
last ~2 hours (close 100 bps below the close 110 bars ago), buys the whole
equity, and sells when the price recovers 100 bps, when it falls 150 bps
further (hard stop), or when it retraces 80 bps from its post-entry peak
after rising 50 bps (trailing exit). No new entries in the last 120 bars of
the window, so a fresh position is never forced to flatten before it has had
time to work. A drawdown guard halts entries past 10% equity drawdown and
closes an open position past 15%. A full round trip costs ~26 bps (4 bps fee
+ 2 bps slippage + price impact), so every trade must catch a move larger
than that. See `main.py` for the exact rules.

Local dev-window grade (exact local simulator replicating the harness fill
model): **net PnL +$13.25, 4 trades, max drawdown 0.93%, deterministic
(two runs match)**. On the same window buy-and-hold made −$31.63 and
ema-cross −$148.17.

## Running

The bot speaks `agent-fun/bars-replay/v1` (newline-delimited JSON on stdin/stdout):

```
python3 -P -s main.py
```

Grade locally with the competition kit:

```
node cli/makefun.mjs grade-local --kit . --bot <repo> --driver process
```
