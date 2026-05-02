from groundstation.logging.metrics import metrics


def test_metrics_set_and_snapshot():
    metrics.set("rotator.azimuth_deg", 123.4)
    snap = metrics.snapshot()
    assert snap["rotator.azimuth_deg"] == 123.4


def test_metrics_increment():
    metrics.set("station.mqtt_messages_sent", 0)
    metrics.inc("station.mqtt_messages_sent")
    metrics.inc("station.mqtt_messages_sent", 5)

    snap = metrics.snapshot()
    assert snap["station.mqtt_messages_sent"] == 6


def test_metrics_observe():
    metrics.observe("rotator.mqtt_latency_ms", 12.8)
    snap = metrics.snapshot()
    assert snap["rotator.mqtt_latency_ms"] == 12.8
