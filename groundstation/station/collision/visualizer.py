from __future__ import annotations

import matplotlib.pyplot as plt

from .geometry import Box3D, Pose
from .simulator import SimulationResult


class CollisionVisualizer:
    """
    3D visualizer for debugging collision simulation.

    Features:
      - Draw mast, VHF boom, UHF boom
      - Plot safe vs unsafe track points
      - Optional animation mode
    """

    def __init__(self):
        pass

    def show_static(self, sim: SimulationResult, poses: list[Pose]):
        """
        Show a static 3D plot of:
          - mast
          - VHF/UHF booms at each sample
          - safe/unsafe points
        """
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")

        # Draw ground plane
        self._draw_ground(ax)

        # Draw mast (constant)
        if poses:
            self._draw_box(ax, poses[0].mast_box, color="gray", alpha=0.4)

        # Draw booms for each pose
        for pose in poses:
            self._draw_box(ax, pose.vhf_box, color="blue", alpha=0.15)
            self._draw_box(ax, pose.uhf_box, color="green", alpha=0.15)

        # Plot safe/unsafe points
        self._plot_track_points(ax, sim)

        self._setup_axes(ax)
        plt.title("Collision Simulation — 3D Visualization")
        plt.show()

    def _draw_ground(self, ax):
        """
        Draw a simple ground plane at z=0.
        """
        size = 3.0
        X = [[-size, size], [-size, size]]
        Y = [[-size, -size], [size, size]]
        Z = [[0, 0], [0, 0]]
        ax.plot_surface(X, Y, Z, color="sienna", alpha=0.2)

    def _draw_box(self, ax, box: Box3D, color="blue", alpha=0.2):
        """
        Draw an axis-aligned bounding box.
        """
        xs = [box.min_x, box.max_x]
        ys = [box.min_y, box.max_y]
        zs = [box.min_z, box.max_z]

        # 8 corners
        corners = [
            (xs[0], ys[0], zs[0]),
            (xs[1], ys[0], zs[0]),
            (xs[1], ys[1], zs[0]),
            (xs[0], ys[1], zs[0]),
            (xs[0], ys[0], zs[1]),
            (xs[1], ys[0], zs[1]),
            (xs[1], ys[1], zs[1]),
            (xs[0], ys[1], zs[1]),
        ]

        # 12 edges
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]

        for i, j in edges:
            x = [corners[i][0], corners[j][0]]
            y = [corners[i][1], corners[j][1]]
            z = [corners[i][2], corners[j][2]]
            ax.plot(x, y, z, color=color, alpha=alpha)

    def _plot_track_points(self, ax, sim: SimulationResult):
        """
        Plot safe (green) and unsafe (red) track points.
        """
        safe_x, safe_y, safe_z = [], [], []
        unsafe_x, unsafe_y, unsafe_z = [], [], []

        for tp in sim.safe_points:
            safe_x.append(tp.az)
            safe_y.append(tp.el)
            safe_z.append(tp.range_km)

        for tp, _ in sim.unsafe_points:
            unsafe_x.append(tp.az)
            unsafe_y.append(tp.el)
            unsafe_z.append(tp.range_km)

        ax.scatter(safe_x, safe_y, safe_z, color="green", label="Safe", s=20)
        ax.scatter(unsafe_x, unsafe_y, unsafe_z, color="red", label="Unsafe", s=40)

        ax.legend()

    def _setup_axes(self, ax):
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_zlabel("Z (m)")
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        ax.set_zlim(0, 3)
