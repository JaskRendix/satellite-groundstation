from pathlib import Path
from typing import Any

from stl import mesh


def analyze_part(file_path: Path, density_g_cm3: float = 1.25) -> dict[str, Any] | None:
    """
    Performs a deep mechanical analysis of an STL component.
    Default density is for PLA.
    """
    if not file_path.exists():
        print(f"Error: Could not find {file_path}")
        return None

    part_mesh = mesh.Mesh.from_file(str(file_path))

    # Extract mass properties
    volume, cog, inertia = part_mesh.get_mass_properties()

    # Bounding box
    min_dist = part_mesh.min_
    max_dist = part_mesh.max_
    dims = max_dist - min_dist

    # Mass in grams
    mass_g = (volume / 1000.0) * density_g_cm3

    return {
        "filename": file_path.name,
        "dims": dims,
        "volume": volume,
        "cog": cog,
        "mass_g": mass_g,
        "inertia": inertia,
    }


def print_report(data: dict[str, Any]) -> None:
    print(f"\n{'='*50}")
    print(f" Hardware Analysis: {data['filename']}")
    print(f"{'='*50}")

    print(f"PHYSICAL DIMENSIONS (mm):")
    print(f" X (Width):  {data['dims'][0]:8.2f}")
    print(f" Y (Depth):  {data['dims'][1]:8.2f}")
    print(f" Z (Height): {data['dims'][2]:8.2f}")

    print(f"\nMASS PROPERTIES:")
    print(f" Volume:      {data['volume']:8.2f} mm³")
    print(f" Est. Weight: {data['mass_g']:8.2f} g")
    print(f" Center of Gravity:")
    print(
        f" [X: {data['cog'][0]:.2f}, Y: {data['cog'][1]:.2f}, Z: {data['cog'][2]:.2f}]"
    )

    print(f"\nROTATIONAL INERTIA (Moment of Inertia):")
    print(f" Ixx: {data['inertia'][0][0]:.2e}")
    print(f" Iyy: {data['inertia'][1][1]:.2e}")
    print(f" Izz: {data['inertia'][2][2]:.2e}")

    accel_suggestion = max(5, 100 - (data["mass_g"] / 10))
    print(f"\nCONFIG SUGGESTIONS:")
    print(f" > Suggested Max Accel: ~{accel_suggestion:.1f} dps²")
    print(f" > Check 'max_deg' if Z-height ({data['dims'][2]:.1f}mm) risks collision.")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    boom_assembly: list[Path] = [
        Path("stl-files/rotator/antenna_holder-part1.stl"),
        Path("stl-files/rotator/antenna_holder-part2.stl"),
        Path("stl-files/rotator/rod_connector-inner.stl"),
        Path("stl-files/rotator/rod_connector-outer.stl"),
        Path("stl-files/antennas/gamma_match_holder-UHF.stl"),
        Path("stl-files/antennas/gamma_match_holder-VHF.stl"),
        Path("stl-files/polarization_switcher/polarization_switcher.stl"),
    ]

    total_mass: float = 0.0

    for f in boom_assembly:
        stats = analyze_part(f)
        if stats:
            total_mass += stats["mass_g"]
            print_report(stats)

    print(f"\n[ TOTAL BOOM PAYLOAD: {total_mass:.2f} g ]")
    print("Update elevation torque calculations using this total mass.")
