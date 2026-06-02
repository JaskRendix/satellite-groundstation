# **Ground Station for Satellite Tracking**

This repository contains a complete **VHF/UHF satellite ground station** with hardware control, prediction, scheduling, and collision‑aware tracking.

The system includes:

- dual‑axis rotator  
- VHF and UHF cross‑Yagi antennas  
- polarization switchers  
- SDR receiver  
- station software for prediction and tracking  
- collision simulation and avoidance

**Attribution:**  
Mechanical assets and reference images include work by *David Nenicka*:  
[https://github.com/DaveXNN/Ground-station-for-satellite-tracking](https://github.com/DaveXNN/Ground-station-for-satellite-tracking)

---

## **Installation**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Development:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -q
```

---

# **1. System Overview**

The ground station tracks LEO satellites with high pointing accuracy.  
It has two main subsystems.

---

## **1.1 Rotator Subsystem (Raspberry Pi)**

Handles hardware control:

- stepper motors (azimuth, elevation)  
- homing switches  
- polarization relays  
- GPIO abstraction  
- MQTT command interface  
- telemetry  
- structured logging  
- metrics  
- systemd daemon  
- shortest‑path azimuth rotation  

---

## **1.2 Station Subsystem (PC/Laptop)**

Handles high‑level logic:

- TLE management  
- pass prediction  
- scheduling  
- SatNOGS API  
- transmitter metadata  
- MQTT control of the rotator  
- collision simulation and avoidance  
- optional GUI  
- structured logging  

---

# **2. Collision Subsystem**

Located in:

```
groundstation/station/collision/
```

Provides collision‑aware tracking:

- **geometry model** of mast and booms  
- **constraint checker** for limits, clearance, forbidden azimuth, mast collision  
- **collision simulator**  
- **planner** for strict or clamped safe tracks  
- **visualizer** for 3D debugging  
- **tracking pipeline** integrating prediction and collision checks  

Configuration block in `config/default.yaml`:

```yaml
collision:
  enabled: true
  mode: clamp
  mast_height_m: 2.0
  boom_vhf_length_m: 1.5
  boom_uhf_length_m: 1.2
  boom_offset_m: 0.15
  clearance_min_m: 0.3
  forbidden_azimuth_sectors: []
```

The pipeline returns a safe track for the rotator.

---

# **3. Rotator Hardware**

### **Mechanical**

- aluminum frame  
- bearings  
- spur gear reduction  
- 3D‑printed parts  
- dimensions: 240 × 240 × 305 mm  

### **Electronics**

- Raspberry Pi 4B  
- 2× NEMA23 motors  
- 2× TB6600 drivers  
- LM2596 buck converter  
- 4× polarization relays  
- 20 V / 45 W supply  
- 2× homing switches  

---

# **4. Rotator Software**

Located in `groundstation/rotator/`:

- `controller.py`  
- `stepper.py`  
- `gpio.py`  
- `polarization.py`  
- `state_machine.py`  
- `mqtt_client.py`  
- `protocol.py`  
- `rotator_daemon.py`  
- `rotator_shutdown.py`  

### **Logging**

Dedicated loggers per module.

### **Metrics**

Stored in:

```
groundstation/logging/metrics.py
```

Tracks position, events, MQTT activity, and state.

---

# **5. Antennas**

Two cross‑Yagi antennas:

### **VHF (145 MHz)**  
4 elements.

### **UHF (435 MHz)**  
9 elements.

Models in:

```
stl-files/antennas/
```

---

# **6. Polarization Switchers**

Dual‑relay phase‑shift switchers:

- Vertical  
- Horizontal  
- RHCP  
- LHCP  

Housings in:

```
stl-files/polarization_switcher/
```

---

# **7. Receiver**

Airspy Mini SDR for VHF/UHF.

---

# **8. Station Software**

Located in `groundstation/station/`.

### **Tracking**

- `predictor.py`  
- `scheduler.py`  
- `tle_manager.py`  
- `satnogs_client.py`  
- `transmitter_db.py`  

### **MQTT**

`station/mqtt/client.py`

---

# **9. Configuration**

Main config:

```
config/default.yaml
```

Contains station location, MQTT settings, rotator pins, tracking parameters, scheduler settings, TLE cache, transmitter DB, SatNOGS token, and collision settings.

---

# **10. Mechanical Assets**

3D‑printed parts:

```
stl-files/
    rotator/
    antennas/
    polarization_switcher/
```
