from __future__ import annotations

from cosmos_media.integrator import handle_request


class FakeEngine:
    settings = object()


class FakeEditing:
    def __init__(self):
        self.image_call = None
        self.video_call = None

    def import_file(self, source):
        return {"asset_id": f"asset-{source}"}

    def edit_image(self, asset_id, prompt, output, **kwargs):
        self.image_call = {
            "asset_id": asset_id,
            "prompt": prompt,
            "output": output,
            **kwargs,
        }
        return self.image_call

    def edit_video(self, asset_id, prompt, output, **kwargs):
        self.video_call = {
            "asset_id": asset_id,
            "prompt": prompt,
            "output": output,
            **kwargs,
        }
        return self.video_call


def test_bridge_forwards_masked_image_edit_controls():
    editing = FakeEditing()
    response = handle_request(
        FakeEngine(),
        {
            "id": "img",
            "op": "edit_image",
            "input": "source.png",
            "mask": "mask.png",
            "prompt": "replace only the masked sky",
            "model": "cosmos-main",
            "strength": 0.7,
        },
        editing,
    )

    assert response["ok"] is True
    assert editing.image_call["mask_asset_id"] == "asset-mask.png"
    assert editing.image_call["model"] == "cosmos-main"
    assert editing.image_call["strength"] == 0.7


def test_bridge_forwards_video_continuity_controls():
    editing = FakeEditing()
    response = handle_request(
        FakeEngine(),
        {
            "id": "vid",
            "op": "edit_video",
            "input": "source.mp4",
            "prompt": "cinematic neon night",
            "model": "cosmos-main",
            "chunk_seconds": 3.5,
            "style_lock": False,
            "temporal_blend": 0.2,
            "preserve_audio": True,
        },
        editing,
    )

    assert response["ok"] is True
    assert editing.video_call["chunk_seconds"] == 3.5
    assert editing.video_call["style_lock"] is False
    assert editing.video_call["temporal_blend"] == 0.2
    assert editing.video_call["preserve_audio"] is True
