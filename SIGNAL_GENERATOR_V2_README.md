# Signal Generator V2.0 - System Documentation

**Version:** 2.0  
**Date:** January 2026  
**Architecture:** Event-Driven, FMSI-Master Clock, Elastic State Machine  
**Purpose:** Automated Option Buying Signals (Nifty Options) based on Physical Market Mechanics.

---

## 1. Core Logic & Architecture

The Signal Generator V2.0 moves away from rigid thresholds to an **Elastic State Cycle** that adapts to market volatility ("breathing"). It treats the market as a physical system with support (Box), momentum (PI), and potential energy (FMSI Gap).

### 1.1 FMSI Master Clock
*   **Design**: The system is strictly synchronized to the **FMSI (Flow Multi-Strike Index)** tick interval (~15s).
*   **Data Fusion**: Gamma levels and CMSI Box data are cached and "forward-filled" to align exactly with the incoming FMSI tick.
*   **Implication**: Signal decisions are made *only* when FMSI updates, ensuring all metrics (Structure, Flow, Momentum) are evaluated simultaneously.

### 1.2 The 5-State Elastic Cycle
The engine uses a finite state machine (`StateMachineV2`) to manage trade lifecycle:

1.  **`NULL`**: Scanning for setup. No active trade.
2.  **`ORIGIN_ENTRY`**: Initial entry trigger fired.
3.  **`ACTIVE_HOLD`**: Trade active. Monitoring for expansion (profit) or failure (risk).
4.  **`SPIKE_EXIT`**: Exit triggered by rapid acceleration (profit taking) or structural veto (stop loss).
5.  **`COOLDOWN`**: Mandatory pause (e.g., 60s) to reset emotional/systemic state.

---

## 2. Mathematical Models & Signals

### 2.1 Entry Logic (The "Permission Stack")
A trade is ONLY taken if **ALL 3** layers align:

1.  **Layer 1: Dealer Box Structure (Stability)**
    *   **Math**: `Standard Deviation(History Window) < Epsilon`.
    *   **Logic**: The Dealer must actively suppress price volatility ("Lock") to build inventory.
    *   **Tunables**:
        *   `box_history_window` (10-100 ticks): How long the wall must hold.
        *   `box_epsilon` (0.001-0.010): Volatility tolerance.
    *   **Regimes**: `OPPOSITION` (Best), `ALIGNMENT`, `CUMULATIVE_ONLY`.

2.  **Layer 2: Proximity Index (Momentum)**
    *   **Math**: Normalized position of Price within the Dealer Box (-1 to +1).
    *   **Logic**: Trade MUST NOT be in the "Dead Zone" (Box Center). We need momentum away from the center.
    *   **Tunables**:
        *   `dead_zone_buffer` (0.05): Area around 0.0 to ignore.

3.  **Layer 3: Gap Compression (Timing)**
    *   **Math**: `FMSI - Price`.
    *   **Logic**: Entry triggers when the gap begins to compress (Velocity < 0), indicating potential energy release.

### 2.2 Trade Direction (Option Buying)
*   **Bullish Signal**: Maps to **CE** (Call Option).
*   **Bearish Signal**: Maps to **PE** (Put Option).

### 2.3 Exit Logic
The system has three distinct exit triggers:

1.  **3σ Gap Acceleration (Profit/Spike)**
    *   **Type**: Adaptive Profit Taking.
    *   **Math**: `Acceleration > 3 * Rolling_Std_Dev(Acceleration)`.
    *   **Logic**: Exits when price moves *too fast* relative to recent history. Captures the "pop" before mean reversion.
    *   **Tunable**: `spike_history_window` (10-100 ticks), `spike_sigma_threshold` (2.0-5.0).

2.  **PI Veto (Structural Stop)**
    *   **Type**: Stop Loss / Invalidated Setup.
    *   **Logic**: If Price crosses back over the Box Midpoint (PI flips sign/touches 0), the momentum is broken. **Immediate Exit**.

3.  **Box Reversal Flip (Smart Degradation)**
    *   **Type**: Major Trend Change.
    *   **Logic**:
        *   If Box simply unlocks/disappears: **HOLD** (Price may be running away from Box).
        *   If a **NEW Box locks** in the **OPPOSITE** direction: **EXIT IMMEDIATELY**.

---

## 3. Tunable Parameters (UI & CLI)

All parameters support **Hot Reloading** (Real-time update without restart).

| Parameter | Range | Default | Description |
| :--- | :--- | :--- | :--- |
| **Box History Window** | 10-100 | 20 | Ticks required to confirm a Dealer Wall. Higher = More stability, fewer entries. |
| **Spike History Window** | 10-100 | 30 | Baseline for "normal" acceleration. Higher = More robust spike detection. |
| **Box Epsilon** | .001-.01 | .005 | Strictness of the "Lock". Lower = Harder to find entries. |
| **Sigma Threshold** | 2.0-5.0 | 3.0 | Intensity of spike required to exit. Lower = Quick scalps. Higher = Runners. |
| **Dead Zone** | .03-.10 | .05 | Buffer around box center to avoid noise. |

---

## 4. Infrastructure & Redis Interface

### 4.1 Channels
*   **INPUT** (Subscribed):
    *   `charts_engine:fmsi`: Master Clock (Ticks).
    *   `charts_engine:gamma`: Gamma Levels.
    *   `charts_engine:atm_cmsi`: Dealer Box Data.
    *   `charts_engine:commands`: **NEW** Control channel (Reset/Stop).
*   **OUTPUT** (Published):
    *   `charts_engine:signals`: Generated signals.

### 4.2 Signal Output Schema
Channel: `charts_engine:signals`
```json
{
  "ts": 1709923456.78,
  "iso": "2026-01-11T10:15:00...",
  "event_type": "ENTRY",       // or "EXIT", "RESET"
  "state": "ORIGIN_ENTRY",     // or "SPIKE_EXIT", "NULL"
  "instrument": "CE",          // or "PE", or null
  "metadata": {
      "reason": "OPPOSITION_ENTRY", // or "SPIKE_EXIT_3.2σ", "BOX_REVERSAL_FLIP"
      "pi": 0.08,
      "gap": 12.5,
      "sigma_level": 3.2,       // (Exit Only)
      "cooldown_remaining": 60  // (Wait Only)
  }
}
```

### 4.3 Command Interface (Bot Integration)
Use this to force the engine to reset (e.g., when your P&L target is hit).

**Channel**: `charts_engine:commands`
**Payload**:
```json
{
  "command": "RESET_STATE",
  "source": "PnL_Manager_Bot"
}
```
**Effect**:
1.  Clears active trade memory (Instrument, Entry Price, etc.).
2.  Sets Internal State to `NULL`.
3.  Logs event.
4.  **Warning**: If entry conditions are still valid, engine may *re-enter* on next tick.

---

## 5. UI Controls (Page 11)

*   **Status Indicators**: Live readiness check (Redis, Data freshness).
*   **Tunable Sliders**: Real-time adjustment of all parameters above.
*   **Action Buttons**:
    *   `Reload Config`: Force read from disk.
    *   `Reset Defaults`: Restore factory settings.
    *   `🛑 Force Reset State`: **Manual Kill Switch**. Clears current trade memory and forces state to NULL. Equivalent to the Redis command.

---

## 6. Integration Guide for P&L Bots

To build a P&L bot on top of V2.0:

1.  **Listen** to `charts_engine:signals`.
2.  When `event_type == "ENTRY"`, place your broker order.
3.  **Monitor** your P&L.
4.  **If P&L Hit**:
    *   Close order at broker.
    *   **Publish** `RESET_STATE` to `charts_engine:commands`.
    *   (Optional) If you want to stop trading for the day, maintain a local "Done" flag and ignore future `ENTRY` signals.
5.  **If Signal Exit** (`event_type == "EXIT"`):
    *   Close order at broker.
