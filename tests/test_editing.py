from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image
import pytest

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
    assert asset["width"] == 64
    assert asset["height"] == 48

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


def test_masked_native_image_edit_preserves_unmasked_pixels(tmp_path):
    source = tmp_path / "source.png"
    mask = tmp_path / "mask.png"
    Image.new("RGB", (8, 4), (60, 90, 120)).save(source)
    mask_image = Image.new("L", (8, 4), 0)
    for x in range(4):
        for y in range(4):
            mask_image.putpixel((x, y), 255)
    mask_image.save(mask)

    service = EditingService(make_settings(tmp_path))
    source_asset = service.import_file(source)
    mask_asset = service.import_file(mask)
    output = tmp_path / "masked.png"

    result = service.edit_image(
        source_asset["asset_id"],
        "warm neon cinematic",
        output,
        model="native-edit",
        strength=1.0,
        mask_asset_id=mask_asset["asset_id"],
    )

    with Image.open(source) as original, Image.open(output) as edited:
        original = original.convert("RGB")
        edited = edited.convert("RGB")
        for x in range(4, 8):
            for y in range(4):
                assert edited.getpixel((x, y)) == original.getpixel((x, y))
        assert any(
            edited.getpixel((x, y)) != original.getpixel((x, y))
            for x in range(4)
            for y in range(4)
        )

    assert result["mask_asset_id"] == mask_asset["asset_id"]


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
    with pytest.raises(ValueError, match="unsupported"):
        service.import_file(bad)


def test_rejects_invalid_image_bytes_with_valid_extension(tmp_path):
    bad = tmp_path / "fake.png"
    bad.write_bytes(b"this is not actually a png")
    service = EditingService(make_settings(tmp_path))
    with pytest.raises(ValueError, match="invalid image"):
        service.import_file(bad)


def test_native_video_edit_smoke_and_chunk_parameters(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not available")

    settings = make_settings(tmp_path)
    source = tmp_path / "source.mp4"
    output = tmp_path / "edited.mp4"
    import subprocess

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=96x64:d=0.5:r=12",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    service = EditingService(settings)
    asset = service.import_file(source)
    result = service.edit_video(
        asset["asset_id"],
        "warm cinematic",
        output,
        model="native-edit",
        chunk_seconds=0.25,
        style_lock=True,
        temporal_blend=0.1,
        preserve_audio=False,
    )
    assert output.exists() and output.stat().st_size > 0
    assert result["parameters"]["chunk_seconds"] == 0.25
    assert result["parameters"]["style_lock"] is True
    assert result["parameters"]["temporal_blend"] == 0.1
