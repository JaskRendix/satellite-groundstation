from unittest.mock import MagicMock

import pytest

from groundstation.rotator.polarization import (
    POLARIZATION_MODES,
    PolarizationConfig,
    PolarizationSwitcher,
)


@pytest.fixture
def mock_gpio():
    gpio = MagicMock()
    gpio.setup_output = MagicMock()
    gpio.write = MagicMock()
    return gpio


@pytest.fixture
def config():
    return PolarizationConfig(
        uhf_rel1=1,
        uhf_rel2=2,
        vhf_rel1=3,
        vhf_rel2=4,
    )


@pytest.fixture
def switcher(mock_gpio, config):
    return PolarizationSwitcher(mock_gpio, config)


def test_initializes_all_pins(mock_gpio, config):
    PolarizationSwitcher(mock_gpio, config)

    expected_calls = [
        (1,),
        (2,),
        (3,),
        (4,),
    ]

    actual_calls = [call.args for call in mock_gpio.setup_output.call_args_list]
    assert actual_calls == expected_calls


def test_initial_mode_is_vertical(mock_gpio, config):
    PolarizationSwitcher(mock_gpio, config)

    expected = [
        (1, False),
        (2, False),
        (3, False),
        (4, False),
    ]

    actual = [call.args for call in mock_gpio.write.call_args_list]
    assert actual == expected


def test_supported_modes():
    assert POLARIZATION_MODES == {"Vertical", "Horizontal", "LHCP", "RHCP"}


def test_invalid_mode_raises(mock_gpio, config):
    switcher = PolarizationSwitcher(mock_gpio, config)
    with pytest.raises(ValueError):
        switcher.set("INVALID")


def test_vertical_mode(switcher, mock_gpio, config):
    mock_gpio.write.reset_mock()
    switcher.set("Vertical")

    expected = [
        (config.uhf_rel1, False),
        (config.uhf_rel2, False),
        (config.vhf_rel1, False),
        (config.vhf_rel2, False),
    ]

    actual = [call.args for call in mock_gpio.write.call_args_list]
    assert actual == expected


def test_horizontal_mode(switcher, mock_gpio, config):
    mock_gpio.write.reset_mock()
    switcher.set("Horizontal")

    expected = [
        (config.uhf_rel1, False),
        (config.uhf_rel2, True),
        (config.vhf_rel1, False),
        (config.vhf_rel2, True),
    ]

    actual = [call.args for call in mock_gpio.write.call_args_list]
    assert actual == expected


def test_lhcp_mode(switcher, mock_gpio, config):
    mock_gpio.write.reset_mock()
    switcher.set("LHCP")

    expected = [
        (config.uhf_rel1, True),
        (config.uhf_rel2, False),
        (config.vhf_rel1, True),
        (config.vhf_rel2, False),
    ]

    actual = [call.args for call in mock_gpio.write.call_args_list]
    assert actual == expected


def test_rhcp_mode(switcher, mock_gpio, config):
    mock_gpio.write.reset_mock()
    switcher.set("RHCP")

    expected = [
        (config.uhf_rel1, True),
        (config.uhf_rel2, True),
        (config.vhf_rel1, True),
        (config.vhf_rel2, True),
    ]

    actual = [call.args for call in mock_gpio.write.call_args_list]
    assert actual == expected
