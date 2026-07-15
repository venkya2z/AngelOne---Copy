# Signal Generator V2.0 - Redis Signal Schema

This document specifies the format of trading signals published to Redis by the **Signal Generator V2.0**.

**Channel**: `charts_engine:signals`  
**Format**: JSON

---

## 🔝 Common Envelope Fields

Every message published to Redis contains these core fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `ts` | float | Event timestamp (Unix epoch). |
| `iso` | string | ISO 8601 formatted timestamp. |
| `event_type` | string | `ENTRY` or `EXIT`. |
| `state` | string | Internal state machine name (e.g., `ORIGIN_ENTRY`, `SPIKE_EXIT`). |
| `instrument` | string | `CE` or ` PE`. |
| `reason` | string | Human-readable explanation of the trigger. |

---

## 🚩 ENTRY Signal Schema

Published when all permission layers (PI deadzone, FMSI velocity, regime confidence) are met.

### Metadata Fields
Included in the JSON object under their respective keys:

| Field | Description |
| :--- | :--- |
| `regime` | Current market regime (`HIGH`, `MEDIUM`, `LOW` confidence). |
| `ce_confidence` | Probability score for CE expansion. |
| `pe_confidence` | Probability score for PE expansion. |
| `agreement_ratio` | Measure of Box vs PI directional alignment. |
| `box_confidence` | Box structural stability (`HIGH_ALIGNMENT`, `CONFLICT`, etc.). |
| `pi` | Proximity Index value at entry. |
| `pi_zone` | Zone classification (`SUPPORT_ZONE`, `RESISTANCE_ZONE`). |
| `gap` | FMSI Gap (Fast - Slow) value. |
| `gap_velocity` | Current rate of gap expansion. |

**Example Message**:
```json
{
  "ts": 1705112345.67,
  "iso": "2026-01-13T09:15:45+0530",
  "event_type": "ENTRY",
  "state": "ORIGIN_ENTRY",
  "instrument": "CE",
  "reason": "PI_DYNAMICS_ENTRY",
  "regime": "HIGH",
  "ce_confidence": 0.85,
  "pe_confidence": 0.12,
  "agreement_ratio": 0.9,
  "box_confidence": "HIGH_ALIGNMENT",
  "pi": 0.82,
  "pi_zone": "RESISTANCE_ZONE",
  "gap": 15.4,
  "gap_velocity": 2.1
}
```

---

## 🏁 EXIT Signal Schema

Published when an exit trigger (PI Veto or FMSI Spike) is activated.

### Metadata Fields

| Field | Description |
| :--- | :--- |
| `exit_pi` | Proximity Index value at exit. |
| `exit_gap` | FMSI Gap value at exit. |
| `exit_velocity` | Gap velocity at exit. |
| `exit_acceleration`| Gap acceleration (used for spike detection). |
| `cooldown_seconds` | Duration of the cooldown period until next trade allowed. |

**Example Message**:
```json
{
  "ts": 1705112400.12,
  "iso": "2026-01-13T09:16:40+0530",
  "event_type": "EXIT",
  "state": "SPIKE_EXIT",
  "instrument": "CE",
  "reason": "GAP_ACCELERATION_EXIT_3.2sigma",
  "exit_pi": 0.15,
  "exit_gap": 22.1,
  "exit_velocity": 0.5,
  "exit_acceleration": 4.2,
  "cooldown_seconds": 300
}
```

---

## 📈 ADD_LOT Signal Schema

Published when an averaging or scale-in trigger is activated. It inherits the same core fields.

### Metadata Fields

| Field | Description |
| :--- | :--- |
| `regime` | Current market regime (`HIGH`, `MEDIUM`, `LOW` confidence). |
| `lots` | Optional. Explicit number of lots to add. If omitted, uses confidence mapped lots. |
| `contract_token` | Optional. Token of the specific contract to pin (must match active position). |
| `tradingsymbol` | Optional. Specific trading symbol. |

**Example Message**:
```json
{
  "ts": 1705112400.12,
  "iso": "2026-01-13T09:16:40+0530",
  "event_type": "ADD_LOT",
  "signal_id": "uuid-or-monotonic-id",
  "state": "AVERAGE_DOWN",
  "instrument": "CE",
  "reason": "CUMULATIVE_ENTRY",
  "regime": "HIGH"
}
```
