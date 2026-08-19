from __future__ import annotations

from pathlib import Path

from PIL import Image

from cosmos_media.config import Settings
from cosmos_media.edit_providers import prompt_video_filter
from cosmos_media.editing import EditingService


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        home=tmp_path / ".cosmos",
        provider="native",
        quantum_mode="off",
        width=96,
        height=64,
        fps=12,
        chunk_seconds=1.0,
        default_model="cosmos-main",
        edit_renderer="native",
        max_upload_mb=4,
    )


def test_upload_and_native_image_edit(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (64, 48), (40, 60, 80)).save(source)
    service = EditingService(make_settings(tmp_path))

    asset = service.import_file(source)
    assert asset["kind"] == "image"
    assert asset["asset_id"]

    output = tmp_path / "edited.png"
    result = service.edit_image(
        asset["asset_id"],
        "warm cinematic neon",
        output,
        model="native-edit",
        strength=0.8,
    )
    assert output.exists()
    assert output.read_bytes() != source.read_bytes()
    assert result["model"] == "native-edit"
    assert result["renderer"] == "native"
    assert Path(result["receipt"]).exists()
    assert service.job(result["job_id"])["status"] == "completed"


def test_cosmos_main_uses_qc67_identity_but_reports_actual_renderer(tmp_path):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (32, 32), (90, 40, 20)).save(source)
    service = EditingService(make_settings(tmp_path))
    asset = service.import_file(source)

    result = service.edit_image(
        asset["asset_id"],
        "cool moonlit cinematic",
        tmp_path / "cosmos-main.png",
        strength=0.6,
    )
    assert result["model"] == "cosmos-main"
    assert result["controller_repo"] == "phera-ra/QC67_cosmo"
    assert result["renderer"] == "native"


def test_prompt_video_filter_is_deterministic_and_prompt_conditioned():
    neon = prompt_video_filter("neon cyberpunk night")
    warm = prompt_video_filter("warm golden sunset")
    assert neon == prompt_video_filter("neon cyberpunk night")
    assert neon != warm
    assert isinstance(neon, str) and neon


def test_rejects_unsupported_upload(tmp_path):
    bad = tmp_path / "payload.exe"
    bad.write_bytes(b"not media")
    service = EditingService(make_settings(tmp_path))
    try:
        service.import_file(bad)
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("unsupported upload should fail")
