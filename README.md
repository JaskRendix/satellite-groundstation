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

---

## **1. System Overview**

The ground station tracks fast LEO satellites with high pointing accuracy.  
It consists of two main subsystems:

### **Rotator Subsystem (Raspberry Pi)**  
Handles hardware control:

- stepper motors (azimuth and elevation)
- polarization relays
- GPIO abstraction
- MQTT command interface
- telemetry and heartbeat
- structured logging
- runtime metrics
- systemd‑managed daemon

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

GPIO pins control all hardware.

---

## **3. Rotator Software**

The rotator software is modular and runs as a systemd service.

### **Modules**
Located in `groundstation/rotator/`:

- `controller.py` — motion logic  
- `stepper.py` — stepper control  
- `gpio.py` — hardware abstraction  
- `polarization.py` — relay control  
- `state_machine.py` — explicit states  
- `mqtt_client.py` — MQTT command and telemetry  
- `protocol.py` — message schema  
- `rotator_daemon.py` — main daemon  
- `rotator_shutdown.py` — safe shutdown  

---

## **3.1 Logging**

The rotator uses structured logging through the Python `logging` module.  
Each module exposes a dedicated logger:

- `rotator.controller`
- `rotator.stepper`
- `rotator.polarization`
- `rotator.mqtt`

Logs include:

- movement commands  
- limit violations  
- homing  
- shutdown events  
- stepper activity  
- MQTT connection and message handling  

Enable logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

---

## **3.2 Metrics**

Runtime metrics are collected through a thread‑safe metrics store:

```
groundstation/logging/metrics.py
```

Metrics include:

- `rotator.azimuth_deg`  
- `rotator.elevation_deg`  
- `rotator.limit_violations`  
- `rotator.mqtt_messages_sent`  
- `rotator.mqtt_latency_ms`  

API:

```python
from groundstation.logging.metrics import metrics

metrics.set("rotator.azimuth_deg", 123.4)
metrics.inc("rotator.limit_violations")
metrics.observe("rotator.mqtt_latency_ms", 12.8)

print(metrics.snapshot())
```

Metrics support testing, debugging, and monitoring.

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

- Vertical  
- Horizontal  
- RHCP  
- LHCP  

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
- tracking parameters  
- scheduler settings  
- TLE cache settings  
- transmitter DB settings  
- SatNOGS API token  

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
