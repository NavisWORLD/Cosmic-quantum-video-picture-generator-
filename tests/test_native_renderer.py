from __future__ import annotations

from io import StringIO
from pathlib import Path

from cosmos_media.config import Settings
from cosmos_media.engine import CosmosMediaEngine
from cosmos_media.integrator import process_json_line, run_stdio
from cosmos_media.native_renderer import build_scene_spec, render_native_image


def test_native_renderer_is_deterministic_and_prompt_conditioned():
    state = [0.15, -0.22, 0.48, 0.03, 0.25, -0.1, 0.4, 0.2, 0.55, -0.3, 0.7, 0.12]
    a = render_native_image(
        "a luminous tree above an alien ocean under two moons",
        "floating islands surround a glass observatory",
        12345,
        state,
        160,
        90,
    )
    b = render_native_image(
        "a luminous tree above an alien ocean under two moons",
        "floating islands surround a glass observatory",
        12345,
        state,
        160,
        90,
    )
    c = render_native_image(
        "a dense futuristic city at midnight",
        "glass towers and a silent station",
        12345,
        state,
        160,
        90,
    )
    assert a.tobytes() == b.tobytes()
    assert a.tobytes() != c.tobytes()


def test_scene_grammar_reads_prompt_and_state():
    state = [0.0] * 12
    spec = build_scene_spec(
        "floating islands over an ocean with a giant tree and observatory",
        "two worlds meet at night",
        7,
        state,
        320,
        180,
    )
    assert spec.has_water
    assert spec.has_tree
    assert spec.has_city
    assert spec.has_islands
    assert 1 <= spec.moon_count <= 3


def test_jsonl_bridge_capabilities_and_status(tmp_path: Path):
    settings = Settings(home=tmp_path / ".cosmos", provider="native", quantum_mode="off")
    engine = CosmosMediaEngine(settings)
    response = process_json_line(engine, '{"id":"x1","op":"capabilities"}')
    assert response["ok"] is True
    assert response["id"] == "x1"
    assert "standalone" in response["result"]["modes"]
    assert "bridge" in response["result"]["modes"]

    source = StringIO('{"id":1,"op":"state"}\n{"id":2,"op":"branch","prompt":"moon garden"}\n')
    sink = StringIO()
    assert run_stdio(engine, source, sink) == 0
    output = sink.getvalue().splitlines()
    assert len(output) == 2
    assert '"ok":true' in output[0]
    assert '"ok":true' in output[1]
