from pathlib import Path
from typing import Any

import numpy as np
import yaml
from stl import mesh

CONFIG_PATH: Path = Path("config/default.yaml")

BOOM_PARTS: list[Path] = [
    Path("stl-files/rotator/antenna_holder-part1.stl"),
    Path("stl-files/rotator/antenna_holder-part2.stl"),
    Path("stl-files/rotator/rod_connector-inner.stl"),
    Path("stl-files/rotator/rod_connector-outer.stl"),
    Path("stl-files/antennas/gamma_match_holder-UHF.stl"),
    Path("stl-files/antennas/gamma_match_holder-VHF.stl"),
    Path("stl-files/polarization_switcher/polarization_switcher.stl"),
]

PLA_DENSITY_G_CM3: float = 1.25


def analyze_stl(path: Path) -> tuple[float, np.ndarray] | None:
    """Return (mass_g, cog_mm) for an STL file."""
    if not path.exists():
        print(f"Missing STL: {path}")
        return None

    part = mesh.Mesh.from_file(str(path))
    volume, cog, inertia = part.get_mass_properties()

    mass_g: float = (volume / 1000.0) * PLA_DENSITY_G_CM3
    return mass_g, cog


def compute_boom_properties() -> tuple[float, np.ndarray]:
    """Compute total mass and combined center of gravity."""
    total_mass: float = 0.0
    weighted_cog = np.zeros(3)

    for part in BOOM_PARTS:
        result = analyze_stl(part)
        if not result:
            continue

        mass_g, cog = result
        total_mass += mass_g
        weighted_cog += cog * mass_g

    cog_total = weighted_cog / total_mass if total_mass > 0 else np.zeros(3)
    return total_mass, cog_total


def update_yaml(total_mass_g: float, cog: np.ndarray) -> None:
    """Update default.yaml with computed payload properties."""
    with CONFIG_PATH.open("r") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    elevation = config["rotator"]["elevation"]

    suggested_accel: float = max(5, 100 - (total_mass_g / 10))

    elevation["payload_mass_g"] = round(total_mass_g, 2)
    elevation["payload_cog_mm"] = [round(float(c), 2) for c in cog]
    elevation["suggested_max_accel_dps2"] = round(suggested_accel, 2)

    with CONFIG_PATH.open("w") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    print("default.yaml updated successfully.")
    print(f"  payload_mass_g: {total_mass_g:.2f}")
    print(f"  payload_cog_mm: {cog}")
    print(f"  suggested_max_accel_dps2: {suggested_accel:.2f}")


if __name__ == "__main__":
    print("Analyzing STL geometry...")
    total_mass, cog = compute_boom_properties()

    print(f"Total boom mass: {total_mass:.2f} g")
    print(f"Center of gravity: {cog}")

    print("Updating config/default.yaml...")
    update_yaml(total_mass, cog)
