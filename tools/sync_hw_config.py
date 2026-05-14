from pathlib import Path
from typing import Any

import numpy as np
import yaml
from stl import mesh

CONFIG_PATH: Path = Path("config/default.yaml")
ANTENNA_STL: str = "antenna_holder-part2.stl"
STL_DIR: Path = Path("stl-files/rotator/")

PLA_DENSITY_G_CM3: float = 1.25
GRAVITY: float = 9.81
NEMA23_HOLDING_TORQUE_NM: float = 1.2  # adjust to your motor


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r") as f:
        return yaml.safe_load(f)


def compute_mass_properties(stl_path: Path) -> tuple[float, np.ndarray, np.ndarray]:
    part = mesh.Mesh.from_file(str(stl_path))
    return part.get_mass_properties()


def analyze_torque_requirements() -> None:
    print("Calculating Mechanical Torque Budget...")

    stl_path = STL_DIR / ANTENNA_STL
    if not stl_path.exists():
        print(f"Error: {ANTENNA_STL} not found at {stl_path}")
        return

    volume_mm3, cog, inertia = compute_mass_properties(stl_path)

    mass_kg: float = (volume_mm3 / 1000) * PLA_DENSITY_G_CM3 / 1000
    lever_arm_m: float = float(np.linalg.norm(cog) / 1000)

    force_n: float = mass_kg * GRAVITY
    required_torque_nm: float = force_n * lever_arm_m

    config: dict[str, Any] = load_config(CONFIG_PATH)
    gear_ratio: float = config["rotator"]["elevation"]["gear_ratio"]

    available_torque_nm: float = NEMA23_HOLDING_TORQUE_NM * gear_ratio * 0.8

    print(f"--- Torque Report ---")
    print(f"Part Mass:      {mass_kg*1000:.1f} g")
    print(f"Lever Arm:      {lever_arm_m*1000:.1f} mm")
    print(f"Static Torque:  {required_torque_nm:.4f} Nm")
    print(f"System Capacity:{available_torque_nm:.2f} Nm (at {gear_ratio}:1)")

    safety_factor: float = (
        available_torque_nm / required_torque_nm if required_torque_nm > 0 else 999
    )

    if safety_factor < 2.0:
        print(f"LOW SAFETY MARGIN: {safety_factor:.2f}x")
        print("Suggestion: Increase gear ratio or reduce antenna weight.")
    else:
        print(f"SAFETY MARGIN: {safety_factor:.2f}x")


if __name__ == "__main__":
    analyze_torque_requirements()
