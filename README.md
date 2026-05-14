# **Ground Station for Satellite Tracking**

This repository documents the design and implementation of a complete **VHF/UHF satellite ground station** capable of tracking Low Earth Orbit (LEO) satellites.  
The system includes:

- a dual‑axis **rotator**
- **cross‑Yagi antennas** for VHF and UHF
- a **polarization switcher**
- an **SDR receiver**
- a **station computer** running prediction and tracking software

The project draws conceptual inspiration from the SatNOGS Rotator v3, but all mechanical, electrical, and software components have been **fully redesigned and rewritten**.

**Attribution:**  
This project includes mechanical assets and reference images originally published by  
*David Nenicka* in the repository:  
[https://github.com/DaveXNN/Ground-station-for-satellite-tracking](https://github.com/DaveXNN/Ground-station-for-satellite-tracking)

---

## **Installation**

Create a virtual environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

Run the full test suite:

```bash
pytest -q
```

The test suite uses **MockGpioBackend** and patched stepper/motion threads to simulate hardware.

---

## **1. System Overview**

The ground station tracks fast LEO satellites with high pointing accuracy.  
It consists of two main subsystems:

### **Rotator Subsystem (Raspberry Pi)**  
Handles hardware control:

- stepper motors (azimuth and elevation)
- homing switches (GPIO input)
- polarization relays
- GPIO abstraction layer
- MQTT command interface
- telemetry and heartbeat
- structured logging
- runtime metrics
- systemd‑managed daemon
- shortest‑path azimuth rotation

### **Station Subsystem (Laptop/PC)**  
Handles high‑level logic:

- TLE management
- pass prediction
- scheduling
- SatNOGS API integration
- transmitter metadata
- MQTT control of the rotator
- optional GUI
- structured logging

---

## **2. Rotator Hardware**

### **Mechanical Design**
The rotator frame uses aluminum, wood, and 3D‑printed parts.  
Dimensions: **240 × 240 × 305 mm**

Features:

- 4 bearings (2 azimuth, 2 elevation)
- spur gear reduction
- modular rods
- 3D‑printed components (`/stl-files/rotator`)

### **Electronics**

- Raspberry Pi 4B  
- 2× NEMA23 stepper motors  
- 2× TB6600 drivers  
- LM2596 buck converter  
- 4× polarization relays  
- 20 V / 45 W supply  
- 2× normally‑closed homing switches (azimuth + elevation)  

GPIO pins control all hardware, including **input pins for homing switches**.

---

## **3. Rotator Software**

The rotator software is modular and runs as a systemd service.

### **Modules**
Located in `groundstation/rotator/`:

- `controller.py` — high‑level motion logic, limits, offsets, homing  
- `stepper.py` — stepper control, homing, shortest‑path azimuth  
- `gpio.py` — hardware abstraction (input + output)  
- `polarization.py` — relay control  
- `state_machine.py` — explicit rotator states  
- `mqtt_client.py` — MQTT command + telemetry  
- `protocol.py` — message schema  
- `rotator_daemon.py` — main daemon (config‑driven, performs homing)  
- `rotator_shutdown.py` — safe shutdown  

---

## **3.1 Logging**

The rotator uses structured logging through the Python `logging` module.  
Each module exposes a dedicated logger:

- `rotator.controller`
- `rotator.stepper`
- `rotator.polarization`
- `rotator.mqtt`
- `rotator.gpio`

Logs include:

- movement commands  
- limit violations  
- homing events  
- shutdown events  
- stepper activity  
- MQTT connection and message handling  

---

## **3.2 Metrics**

Runtime metrics are collected through a thread‑safe metrics store:

```
groundstation/logging/metrics.py
```

Metrics include:

### **Position + motion**
- `rotator.azimuth_deg`
- `rotator.elevation_deg`
- `rotator.motor_position_deg`
- `rotator.motor_speed_dps`
- `rotator.motor_steps`

### **Events + errors**
- `rotator.limit_violations`
- `rotator.state_machine`
- `rotator.polarization_changes`

### **MQTT**
- `rotator.mqtt_messages_sent`
- `rotator.mqtt_latency_ms`
- `rotator.heartbeat_sent`
- `rotator.state_published`

API:

```python
from groundstation.logging.metrics import metrics

metrics.set("rotator.azimuth_deg", 123.4)
metrics.inc("rotator.limit_violations")
metrics.observe("rotator.mqtt_latency_ms", 12.8)
```

---

## **4. Antennas**

Two **cross‑Yagi antennas** are mounted on the rotator.

### **VHF (145 MHz)**  
- 4 elements  
- λ/4 phase offset  

### **UHF (435 MHz)**  
- 9 elements  
- λ/4 phase offset  

Models are in `/stl-files/antennas`.

---

## **5. Polarization Switchers**

Each band uses a dual‑relay phase‑shift switcher supporting:

- `Vertical`
- `Horizontal`
- `RHCP`
- `LHCP`

Modes are **case‑sensitive** and must match the protocol strings.

Housings are in `/stl-files/polarization_switcher`.

---

## **6. Receiver**

The station uses an **Airspy Mini** SDR for VHF/UHF reception.

---

## **7. Station Software**

The station computer runs the tracking logic.

### **Tracking Modules**
Located in `groundstation/station/tracking/`:

- `predictor.py` — pass prediction  
- `scheduler.py` — pass selection  
- `tle_manager.py` — TLE caching  
- `satnogs_client.py` — SatNOGS API  
- `transmitter_db.py` — transmitter metadata  

### **MQTT Client**
Located in `groundstation/station/mqtt/`:

- `client.py` — sends commands and receives telemetry  

### **Logging**

The station subsystem uses Python logging for:

- TLE updates  
- scheduler decisions  
- tracking loop  
- SatNOGS API interactions  

---

## **8. Configuration**

All configuration is stored in:

```
config/default.yaml
```

Includes:

- station location  
- MQTT broker settings  
- rotator hardware pins  
- home pins for both axes   
- azimuth_mode for shortest‑path rotation  
- tracking parameters  
- scheduler settings  
- TLE cache settings  
- transmitter DB settings  
- SatNOGS API token  

Example (excerpt):

```yaml
rotator:
  azimuth:
    ena_pin: 5
    dir_pin: 6
    pul_pin: 13
    home_pin: 18
    azimuth_mode: true

  elevation:
    ena_pin: 17
    dir_pin: 27
    pul_pin: 22
    home_pin: 23
    azimuth_mode: false
```

---

## **9. Mechanical Assets**

3D‑printed parts are in:

```
stl-files/
```

Subdirectories:

- `rotator/`
- `antennas/`
- `polarization_switcher/`
