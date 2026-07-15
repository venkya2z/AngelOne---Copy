# Signal Generator V2.0 - Redis Integration Guide

## Overview

The Signal Generator V2.0 publishes real-time trading signals to Redis for consumption by downstream systems (Strategy Engine, UI dashboards, logging). This document provides complete specifications for all signal types and integration patterns.

---

## Redis Channel

**Primary Channel**: `charts_engine:signals`

**Publisher**: Signal Generator V2.0 (`core/signal_manager.py`)

**Consumers**:
- Strategy Engine (trade execution)
- UI Dashboards (monitoring)
- Logging services

---

## Signal Types

### 1. ENTRY Signal

**When**: Market conditions meet entry criteria (accumulation + structural alignment)

**Payload Structure**:
```json
{
  "timestamp": 1768189502.531828,
  "iso": "2026-01-13T09:15:02.558083+05:30",
  "signal": "ENTRY",
  "state": "ENTRY",
  "instrument": "NIFTY50",
  "regime": "MEDIUM",
  "reason": "ENTRY_ACCUMULATION_COMPLETE",
  "metadata": {
    "spot_price": 23850.50,
    "pi_direction": "BULLISH",
    "pi_value": 0.0234,
    "fmsi_regime": "COMPRESSION",
    "fmsi_gap": 0.00012,
    "accumulation_ticks": 18,
    "gate_reason": "HIGH_BOX_ALIGNED",
    "entry_percentile": 60,
    "deadzone": 0.05
  }
}
```

**Critical Fields**:
- `signal`: Always "ENTRY"
- `instrument`: Trading instrument (e.g., "NIFTY50")
- `regime`: Detected market regime (HIGH/MEDIUM/LOW)
- `reason`: Entry trigger reason
- `metadata.pi_direction`: Trade direction (BULLISH/BEARISH)
- `metadata.spot_price`: Entry price reference

**Downstream Action**: Strategy Engine executes trade entry

---

### 2. EXIT Signal

**When**: Exit conditions met (spike detected, stop-loss, or time-based)

**Payload Structure**:
```json
{
  "timestamp": 1768190325.123456,
  "iso": "2026-01-13T09:28:45.150000+05:30",
  "signal": "EXIT",
  "state": "NULL",
  "instrument": "NIFTY50",
  "regime": "MEDIUM",
  "reason": "EXIT_SPIKE_DETECTED",
  "metadata": {
    "spot_price": 23875.25,
    "pi_direction": "BULLISH",
    "fmsi_spike_magnitude": 0.0045,
    "exit_percentile": 90,
    "holding_duration_seconds": 823,
    "estimated_pnl": 24.75
  }
}
```

**Critical Fields**:
- `signal`: Always "EXIT"
- `state`: Transitions to "NULL" after exit
- `reason`: Exit trigger (SPIKE/STOP_LOSS/TIME)
- `metadata.holding_duration_seconds`: Trade duration
- `metadata.estimated_pnl`: Unrealized P&L (indicative)

**Downstream Action**: Strategy Engine closes open position

---

### 3. WAIT Signal

**When**: Conditions not met for entry (gatekeeper blocked, accumulation incomplete)

**Payload Structure**:
```json
{
  "timestamp": 1768189515.234567,
  "iso": "2026-01-13T09:15:15.250000+05:30",
  "signal": "WAIT",
  "state": "NULL",
  "instrument": "NIFTY50",
  "regime": "LOW",
  "reason": "FMSI_NOT_READY",
  "metadata": {
    "fmsi_regime": "TRENDING",
    "accumulation_ticks": 8,
    "min_required": 15,
    "gap_percentile": 85
  }
}
```

**Critical Fields**:
- `signal`: Always "WAIT"
- `reason`: Why entry is blocked (FMSI_NOT_READY, GATE_BLOCKED, etc.)
- `metadata`: Diagnostic info for debugging

**Downstream Action**: No trade action, informational only

---

### 4. HOLD Signal (Heartbeat)

**When**: In-trade, no exit conditions yet, periodic heartbeat (default: every 30s)

**Payload Structure**:
```json
{
  "timestamp": 1768190100.456789,
  "iso": "2026-01-13T09:25:00.500000+05:30",
  "signal": "HOLD",
  "state": "ENTRY",
  "instrument": "NIFTY50",
  "regime": "MEDIUM",
  "reason": "MONITORING",
  "metadata": {
    "heartbeat": true,
    "spot_price": 23862.00,
    "time_in_trade_seconds": 598,
    "unrealized_pnl": 11.50,
    "fmsi_current_gap": 0.00018
  }
}
```

**Critical Fields**:
- `signal`: Always "HOLD"
- `state`: "ENTRY" (confirms active trade)
- `metadata.heartbeat`: true (identifies as periodic update)
- `metadata.unrealized_pnl`: Current P&L estimate

**Downstream Action**: UI updates, no trade action

---

## Live Trading Safety Checklist

### ✅ Production Readiness

| Category | Status | Details |
|----------|--------|---------|
| **State Persistence** | ✅ SAFE | Checkpoint saved to `experiments/outputs/checkpoint_v2.json` |
| **Error Handling** | ✅ SAFE | Try-catch blocks with fallback to WAIT state |
| **Redis Failover** | ✅ SAFE | Falls back to file mode if Redis unavailable |
| **Duplicate Prevention** | ✅ SAFE | State machine enforces single active trade |
| **Mode Isolation** | ✅ SAFE | LIVE and REPLAY modes use separate state files |
| **Parameter Validation** | ✅ SAFE | Defaults provided for all tunables |
| **Cooldown Protection** | ✅ SAFE | Configurable cooldown prevents overtrading |

### ⚠️ Critical Safeguards

**1. Single Trade Enforcement**  
- State machine only allows ENTRY when `current_state == 'NULL'`
- Duplicate entries blocked even if Redis delivers messages twice

**2. Gatekeeper Integration**  
- In REPLAY: Defaults to `allow_entry=True` (deterministic)
- In LIVE: Defaults to `allow_entry=False` (requires explicit permission)
- **IMPORTANT**: Gatekeeper operates asynchronously in LIVE mode with ~500ms lag

**3. Emergency Stop**  
- Set `config['enabled'] = false` in `signal_generator_v2_config.json`
- System gracefully stops processing after current tick

**4. Parameter Reload**  
- **NOT ENABLED** for live trading (`reload_enabled: false`)
- Prevents mid-session parameter changes

---

## Integration Guide

### For Strategy Engine (Consumer)

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)
pubsub = r.pubsub()
pubsub.subscribe('charts_engine:signals')

for message in pubsub.listen():
    if message['type'] == 'message':
        signal = json.loads(message['data'])
        
        if signal['signal'] == 'ENTRY':
            # Execute buy/sell based on signal['metadata']['pi_direction']
            direction = signal['metadata']['pi_direction']
            instrument = signal['instrument']
            entry_price = signal['metadata']['spot_price']
            execute_trade(instrument, direction, entry_price)
        
        elif signal['signal'] == 'EXIT':
            # Close position
            close_position(signal['instrument'])
        
        elif signal['signal'] == 'HOLD':
            # Update UI with unrealized P&L
            update_dashboard(signal)
```

### Signal Validation

**Always validate**:
1. `signal['signal']` is one of: `['ENTRY', 'EXIT', 'WAIT', 'HOLD']`
2. `signal['metadata']['pi_direction']` is `'BULLISH'` or `'BEARISH'` for ENTRY
3. `signal['timestamp']` is recent (< 5 seconds old to detect stale messages)

---

## Heartbeat Mechanism

**Purpose**: Ensure signal stream liveness, provide real-time monitoring

**Configuration**:
```json
{
  "heartbeat_interval_seconds": 30,
  "publish_heartbeat_enabled": true
}
```

**Behavior**:
- Publishes HOLD signal every 30s if in ENTRY state
- Publishes WAIT signal every 30s if in NULL state (with `heartbeat: true` flag)
- Strategy Engine can detect disconnection if no signal received for >60s

---

## Error Scenarios & Recovery

### Scenario 1: Redis Connection Lost

**Detection**: `redis_publisher.publish_signal()` returns `False`

**Recovery**:
1. Signals saved to CSV file (`data/signals/*.csv`)
2. State checkpoint persists to JSON
3. On reconnection, system continues from last checkpoint
4. **No trades lost** - state is authoritative

### Scenario 2: Malformed Signal Reception

**Prevention**: 
- Signal validation in Strategy Engine
- Schema version field (`"signal_schema_version": "2.0"`) for compatibility checks

**Handling**:
```python
try:
    signal = json.loads(message['data'])
    assert signal.get('signal') in ['ENTRY', 'EXIT', 'WAIT', 'HOLD']
    assert 'timestamp' in signal
    assert 'metadata' in signal
except (json.JSONDecodeError, AssertionError) as e:
    logger.error(f"Invalid signal: {e}")
    continue  # Skip malformed signal
```

### Scenario 3: Missed EXIT Signal

**Mitigation**:
- Strategy Engine should implement timeout (e.g., max 4-hour holding)
- Monitor trades independently, don't rely solely on EXIT signal
- HOLD heartbeats confirm signal generator is still active

---

## Monitoring & Debugging

### Key Metrics to Track

1. **Signal Rate**: ENTRY+EXIT count per day (typical: 20-100)
2. **Heartbeat Regularity**: HOLD signals every ~30s when in ENTRY
3. **WAIT Reasons**: Distribution of gate blocking reasons
4. **Regime Distribution**: % of time in HIGH/MEDIUM/LOW

### Log Level Configuration

- **Production**: `INFO` (only ENTRY/EXIT logged)
- **Debug**: `DEBUG` (logs all WAIT reasons every 30s)

### Diagnostic Commands

**Check last 10 signals**:
```bash
redis-cli --csv LRANGE signal_history 0 9
```

**Monitor live stream**:
```bash
redis-cli SUBSCRIBE charts_engine:signals
```

**Inspect current state**:
```bash
cat experiments/outputs/signal_state_v2.json
```

---

## Changelog

### v2.0 (2026-01-14)
- ✅ Decoupled entry/exit percentiles
- ✅ Added heartbeat mechanism
- ✅ Gatekeeper integration (async in LIVE, sync in REPLAY)
- ✅ Unified regime parameters (entry=60%, exit=90%)
- ✅ FMSI compression detection
- ✅ Proximity dynamics with adaptive deadzone

### v1.x (Legacy)
- Basic ENTRY/EXIT signals
- Fixed percentile thresholds
- No gatekeeper integration

---

## Contact & Support

**Issues**: Report via GitHub or internal ticket system  
**Config Path**: `data/signal_generator_v2_config.json`  
**State Files**: `experiments/outputs/signal_state_v2*.json`  
**Signal History**: `data/signals/*.csv`

---

**⚠️ CRITICAL REMINDER**: Always test configuration changes in REPLAY mode before deploying to LIVE trading.
