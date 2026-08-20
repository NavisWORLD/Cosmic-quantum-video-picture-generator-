from __future__ import annotations

from types import SimpleNamespace

from cosmos_media.controller import CosmosController


def settings(**overrides):
    base = {
        "controller_mode": "off",
        "controller_model": "phera-ra/QC67_cosmo",
        "controller_endpoint": "",
        "controller_hf_token": "",
        "controller_max_tokens": 160,
        "controller_strict": False,
        "media_timeout": 30.0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_controller_off_is_truthful_passthrough():
    controller = CosmosController(settings())
    plan = controller.plan("make the sky neon", kind="image")
    assert plan["render_prompt"] == "make the sky neon"
    assert plan["model"] == "phera-ra/QC67_cosmo"
    assert plan["used_model"] is False
    assert plan["mode"] == "off"


def test_hf_controller_executes_model_when_authorized():
    calls = []

    class FakeClient:
        def text_generation(self, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return "Preserve the subject. Replace the sky with luminous violet aurora."

    controller = CosmosController(
        settings(controller_mode="hf", controller_hf_token="token"),
        hf_client_factory=lambda **kwargs: FakeClient(),
    )
    plan = controller.plan(
        "make the sky neon",
        kind="image",
        negative_prompt="do not alter the subject",
    )
    assert plan["used_model"] is True
    assert plan["mode"] == "hf"
    assert "luminous violet aurora" in plan["render_prompt"]
    assert calls
    assert calls[0][1]["max_new_tokens"] == 160


def test_auto_controller_falls_back_and_discloses_error():
    def broken_factory(**kwargs):
        raise RuntimeError("model service unavailable")

    controller = CosmosController(
        settings(controller_mode="auto", controller_hf_token="token"),
        hf_client_factory=broken_factory,
    )
    plan = controller.plan("keep continuity", kind="video")
    assert plan["render_prompt"] == "keep continuity"
    assert plan["used_model"] is False
    assert plan["mode"] == "fallback"
    assert "unavailable" in plan["error"]


def test_strict_controller_does_not_silently_fallback():
    def broken_factory(**kwargs):
        raise RuntimeError("no access")

    controller = CosmosController(
        settings(
            controller_mode="hf",
            controller_hf_token="token",
            controller_strict=True,
        ),
        hf_client_factory=broken_factory,
    )
    try:
        controller.plan("edit this", kind="image")
    except RuntimeError as exc:
        assert "no access" in str(exc)
    else:
        raise AssertionError("strict controller should propagate execution failure")
