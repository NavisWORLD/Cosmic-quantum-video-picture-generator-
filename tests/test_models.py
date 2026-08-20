from __future__ import annotations

from cosmos_media.models import ModelRegistry


def test_cosmos_main_is_default_and_identifies_qc67(tmp_path):
    registry = ModelRegistry(tmp_path)
    assert registry.default_id == "cosmos-main"
    model = registry.get("cosmos-main")
    assert model.default is True
    assert model.controller_repo == "phera-ra/QC67_cosmo"
    assert "image_edit" in model.capabilities
    assert "video_edit" in model.capabilities


def test_default_model_switch_persists(tmp_path):
    registry = ModelRegistry(tmp_path)
    registry.set_default("native-edit")
    reloaded = ModelRegistry(tmp_path)
    assert reloaded.default_id == "native-edit"
    assert reloaded.get("native-edit").default is True
    assert reloaded.get("cosmos-main").default is False


def test_diffusers_model_is_registered_but_can_be_unavailable(tmp_path):
    registry = ModelRegistry(tmp_path, semantic_available=False)
    model = registry.get("diffusers-edit")
    assert model.available is False
    assert "image_edit" in model.capabilities
    assert "semantic_edit" in model.capabilities
    assert "framewise_video_edit" in model.capabilities


def test_cosmos_main_can_route_image_and_video_to_different_renderers(tmp_path):
    registry = ModelRegistry(
        tmp_path,
        edit_renderer="native",
        image_edit_renderer="diffusers",
        video_edit_renderer="http",
        edit_endpoint="http://127.0.0.1:9999",
        semantic_available=True,
    )
    model = registry.get("cosmos-main")
    assert registry.renderer_for(model, "image_edit") == "diffusers"
    assert registry.renderer_for(model, "video_edit") == "http"


def test_unknown_model_is_rejected(tmp_path):
    registry = ModelRegistry(tmp_path)
    try:
        registry.get("not-a-model")
    except ValueError as exc:
        assert "unknown model" in str(exc)
    else:
        raise AssertionError("unknown model should fail")
