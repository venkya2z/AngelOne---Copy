# Sophisticated Logging System

## Overview

Date-wise logging with automatic Paper/Live mode distinction for the Angel One Trading Bot.

## Log Structure

```
backend/logs/
├── 2026-01-11/
│   ├── paper_app.log        # Paper mode general logs
│   ├── paper_trades.log     # Paper mode trade logs
│   ├── paper_signals.log    # Paper mode signal logs
│   ├── live_app.log         # Live mode general logs
│   ├── live_trades.log      # Live mode trade logs
│   ├── live_signals.log     # Live mode signal logs
│   └── errors.log           # Shared error log
├── 2026-01-12/
│   └── ...
```

## Log Entry Formats

### Application Log (app.log)
```
2026-01-11 09:15:23 - [PAPER] - AngelBot.App - INFO - SYSTEM | BOT_STARTUP | Mode: PAPER
2026-01-11 09:15:25 - [PAPER] - AngelBot.App - INFO - Processing ENTRY signal: CE, Confidence: HIGH
2026-01-11 09:15:26 - [PAPER] - AngelBot.App - INFO - RISK_CHECK | APPROVED | Lots:3 | Approved for NIFTY2600CE
```

### Trade Log (trades.log)
```
2026-01-11 09:15:26 - [PAPER] - AngelBot.Trades - INFO - ENTRY | NIFTY26000CE | CE | Confidence:HIGH | Qty:75 | Price:₹105.50 | OrderID:PAPER_1000
2026-01-11 09:47:12 - [PAPER] - AngelBot.Trades - INFO - EXIT | NIFTY26000CE | Reason:PNL_TARGET_₹1125 | P&L:+₹1125.00 | OrderID:PAPER_1000
```

### Signal Log (signals.log)
```
2026-01-11 09:15:20 - [PAPER] - AngelBot.Signals - INFO - SIGNAL | Type:ENTRY | Direction:CE | Confidence:HIGH | Spot:₹26050.00
2026-01-11 09:47:10 - [PAPER] - AngelBot.Signals - INFO - SIGNAL | Type:EXIT | Direction:N/A | Confidence:N/A | Spot:₹0.00
```

### Error Log (errors.log)
```
2026-01-11 10:15:30 - [PAPER] - AngelBot.Errors - ERROR - Failed to find ATM strike for entry | Exception: Invalid Token
```

## Usage

### Basic Logging
```python
from logger import get_logger

logger = get_logger()

# General logs
logger.info("Processing order")
logger.warning("Unusual market condition")
logger.error("Order failed", exception_obj)

# System events
logger.system_event("CONFIG_RELOAD", "Strategy config reloaded")
```

### Trade Logging
```python
# Entry
logger.trade_entry(
    symbol="NIFTY26000CE",
    direction="CE",
    confidence="HIGH",
    quantity=75,
    price=105.50,
    order_id="PAPER_1000"
)

# Exit
logger.trade_exit(
    symbol="NIFTY26000CE",
    reason="PNL_TARGET_₹1125",
    pnl=1125.00,
    order_id="PAPER_1000"
)
```

### Signal Logging
```python
logger.signal_received(
    signal_type="ENTRY",
    direction="CE",
    confidence="HIGH",
    spot_price=26050.00
)
```

### Risk Logging
```python
logger.risk_check(
    approved=True,
    num_lots=3,
    reason="Approved for NIFTY26000CE"
)
```

## Key Features

✅ **Date-wise Organization**: New folder per day  
✅ **Mode Distinction**: Separate logs for PAPER/LIVE  
✅ **Multiple Log Types**: App, Trades, Signals, Errors  
✅ **Timestamps**: Every entry timestamped  
✅ **Console & File**: Logs to both simultaneously  
✅ **Structured Format**: Easy to parse and analyze  

## Log Retention

- Logs preserved indefinitely
- Manually cleanup old dates if disk space needed
- Typical day: ~5-10MB total logs

## Viewing Logs

**Today's paper trading logs:**
```bash
cat logs/2026-01-11/paper_app.log
cat logs/2026-01-11/paper_trades.log
```

**Today's errors:**
```bash
cat logs/2026-01-11/errors.log
```

**Follow live:**
```bash
tail -f logs/2026-01-11/paper_app.log
```

## Analysis Examples

**Count trades today:**
```bash
grep "ENTRY |" logs/2026-01-11/paper_trades.log | wc -l
```

**Calculate total P&L:**
```bash
grep "P&L:" logs/2026-01-11/paper_trades.log | \
  grep -oP "P&L:[+-]₹\K[0-9.]+" | \
  awk '{sum += $1} END {print "Total P&L: ₹" sum}'
```

**Find errors:**
```bash
cat logs/2026-01-11/errors.log
```
