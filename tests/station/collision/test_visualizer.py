from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from groundstation.station.collision.geometry import Box3D, Pose
from groundstation.station.collision.simulator import SimulationResult
from groundstation.station.collision.visualizer import CollisionVisualizer
from groundstation.station.tracking.predictor import TrackPoint


def tp(az=100, el=45, r=500):
    return TrackPoint(
        time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        az=az,
        el=el,
        range_km=r,
    )


def pose():
    return Pose(
        vhf_box=Box3D(0, 0, 1, 1, 1, 2),
        uhf_box=Box3D(1, 1, 1, 2, 2, 2),
        mast_box=Box3D(-0.1, -0.1, 0, 0.1, 0.1, 2),
    )


@patch("matplotlib.pyplot.figure")
@patch("matplotlib.pyplot.show")
def test_show_static_calls_matplotlib(mock_show, mock_fig):
    mock_ax = MagicMock()
    mock_fig.return_value.add_subplot.return_value = mock_ax

    vis = CollisionVisualizer()

    sim = SimulationResult(
        safe_points=[tp(az=10, el=20)],
        unsafe_points=[(tp(az=30, el=40), ["boom_mast_collision"])],
    )

    poses = [pose(), pose()]

    vis.show_static(sim, poses)

    # Figure created
    mock_fig.assert_called()

    # Axes created
    mock_fig.return_value.add_subplot.assert_called_once()

    # Ground plane drawn
    assert mock_ax.plot_surface.called

    # Boxes drawn
    assert mock_ax.plot.call_count > 0

    # Scatter for safe + unsafe
    assert mock_ax.scatter.call_count == 2

    # Legend added
    mock_ax.legend.assert_called_once()

    # Show called
    mock_show.assert_called_once()


def test_draw_box_edge_count():
    vis = CollisionVisualizer()
    ax = MagicMock()

    b = Box3D(0, 0, 0, 1, 1, 1)
    vis._draw_box(ax, b, color="blue", alpha=0.5)

    # 12 edges → 12 plot() calls
    assert ax.plot.call_count == 12


def test_draw_ground():
    vis = CollisionVisualizer()
    ax = MagicMock()

    vis._draw_ground(ax)

    ax.plot_surface.assert_called_once()


def test_plot_track_points():
    vis = CollisionVisualizer()
    ax = MagicMock()

    sim = SimulationResult(
        safe_points=[tp(az=10, el=20, r=100)],
        unsafe_points=[(tp(az=30, el=40, r=200), ["boom_mast_collision"])],
    )

    vis._plot_track_points(ax, sim)

    # Two scatter calls: safe + unsafe
    assert ax.scatter.call_count == 2

    # First scatter is safe (green)
    args, kwargs = ax.scatter.call_args_list[0]
    assert kwargs["color"] == "green"

    # Second scatter is unsafe (red)
    args, kwargs = ax.scatter.call_args_list[1]
    assert kwargs["color"] == "red"


def test_setup_axes():
    vis = CollisionVisualizer()
    ax = MagicMock()

    vis._setup_axes(ax)

    ax.set_xlabel.assert_called_with("X (m)")
    ax.set_ylabel.assert_called_with("Y (m)")
    ax.set_zlabel.assert_called_with("Z (m)")

    ax.set_xlim.assert_called_with(-2, 2)
    ax.set_ylim.assert_called_with(-2, 2)
    ax.set_zlim.assert_called_with(0, 3)
