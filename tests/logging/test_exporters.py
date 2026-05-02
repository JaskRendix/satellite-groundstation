import json
import time
import urllib.request

from groundstation.logging.exporters import (
    export_metrics_json,
    start_prometheus_exporter,
)
from groundstation.logging.metrics import metrics


def test_prometheus_exporter_runs(tmp_path):
    metrics.set("rotator.azimuth_deg", 42)

    start_prometheus_exporter(port=9999)
    time.sleep(0.2)  # allow server to start

    data = urllib.request.urlopen("http://localhost:9999/metrics").read().decode()
    assert "rotator_azimuth_deg 42" in data


def test_json_export(tmp_path):
    metrics.set("station.scheduler_queue_len", 3)

    out = tmp_path / "metrics.json"
    export_metrics_json(str(out))

    assert out.exists()
    content = json.loads(out.read_text())
    assert content["station.scheduler_queue_len"] == 3
