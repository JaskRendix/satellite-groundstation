# **Ground Station for Satellite Tracking**

This repository documents the design and implementation of a complete **VHF/UHF satellite ground station** capable of automatically tracking Low Earth Orbit (LEO) satellites.  
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

Here’s a **short, clean installation section** you can drop straight into your README without breaking its flow:

---

## **Installation**

Create a virtual environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

For development work:

```bash
pip install -e ".[dev]"
```

Run the full test suite:

```bash
pytest -q
```

---

## **1. System Overview**

The ground station is built to track fast‑moving LEO satellites with high pointing accuracy.  
It consists of two main subsystems:

### **Rotator Subsystem (Raspberry Pi)**  
Handles all hardware control:

- stepper motors (azimuth + elevation)
- polarization relays (VHF + UHF)
- GPIO abstraction
- MQTT command interface
- telemetry + heartbeat
- systemd‑managed daemon

### **Station Subsystem (Laptop/PC)**  
Handles all high‑level logic:

- TLE management and caching
- pass prediction
- scheduling
- SatNOGS API integration
- transmitter metadata
- MQTT control of the rotator
- optional GUI

---

## **2. Rotator Hardware**

### **Mechanical Design**
The rotator frame is built from aluminum and wood, with dimensions **240 × 240 × 305 mm**.  
It includes:

- 4 bearings (2 azimuth, 2 elevation)
- spur gear reduction
- modular rods for easy assembly
- 3D‑printed parts (available in `/stl-files/rotator`)

### **Electronics**
Powered by a **20 V / 45 W laptop charger**, with a buck converter providing 5 V logic power.

Key components:

- Raspberry Pi 4B  
- 2× NEMA23 stepper motors  
- 2× TB6600 stepper drivers  
- LM2596 buck converter  
- 4× polarization relays  

The Raspberry Pi controls all hardware via GPIO.

---

## **3. Rotator Software**

The rotator software is fully modular and runs as a systemd service.

### **Modules**
Located in `groundstation/rotator/`:

- `controller.py` — high‑level motion logic  
- `stepper.py` — stepper motor control  
- `gpio.py` — hardware abstraction  
- `polarization.py` — relay control  
- `state_machine.py` — explicit rotator states  
- `mqtt_client.py` — MQTT command + telemetry  
- `protocol.py` — shared message schema  
- `service/rotator.service` — systemd unit  
- `rotator_daemon.py` — main daemon  
- `rotator_shutdown.py` — safe shutdown  

### **MQTT Interface**
Commands:

- move to az/el  
- stop  
- home  
- shutdown  
- set polarization  

Telemetry:

- current az/el  
- current polarization  
- state  
- heartbeat  

---

## **4. Antennas**

Two **cross‑Yagi antennas** are mounted on the rotator:

### **VHF (145 MHz)**
- 4 elements  
- λ/4 phase offset  
- element lengths and positions included in documentation  

### **UHF (435 MHz)**
- 9 elements  
- λ/4 phase offset  
- element lengths and positions included in documentation  

All mechanical models are available in `/stl-files/antennas`.

---

## **5. Polarization Switchers**

Each band (VHF and UHF) uses a dual‑relay phase‑shift switcher supporting:

- Vertical  
- Horizontal  
- RHCP  
- LHCP  

Housings are 3D‑printed (`/stl-files/polarization_switcher`).

---

## **6. Receiver**

The station uses an **Airspy Mini** SDR for high‑quality VHF/UHF reception.

---

## **7. Station Software**

The station computer runs the high‑level tracking logic.

### **Tracking Modules**
Located in `groundstation/station/tracking/`:

- `predictor.py` — pass prediction using the *beyond* library  
- `scheduler.py` — selects next satellite to track  
- `tle_manager.py` — cached TLE storage + updates  
- `satnogs_client.py` — async SatNOGS API client  
- `transmitter_db.py` — transmitter metadata cache  

### **MQTT Client**
Located in `groundstation/station/mqtt/`:

- `client.py` — sends commands to rotator and receives telemetry  

### **Workflow**
1. Load TLEs and transmitter metadata  
2. Predict upcoming passes  
3. When AOS occurs:  
   - send initial az/el to rotator  
4. During pass:  
   - stream az/el updates  
5. After LOS:  
   - rotator returns to home position  

---

## **8. Configuration**

All system configuration is stored in:

```
config/default.yaml
```

This includes:

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

All 3D‑printed parts are included in:

```
stl-files/
```

Subdirectories:

- `rotator/`
- `antennas/`
- `polarization_switcher/`

---

## **10. Images**

Reference images and diagrams are stored in:

```
images/
```

These include:

- rotator photos  
- antenna photos  
- Raspberry Pi pinout  
- SDR screenshots  
- GUI screenshots  
