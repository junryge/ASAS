"""Tests for model registry and routing."""

from openharness.api.models import (
    MODEL_REGISTRY,
    FALLBACK_CHAINS,
    ENV_CONFIG,
    get_model_config,
    get_fallback_chain,
    get_max_tokens,
    classify_and_route,
    list_text_models,
    list_vision_models,
)


def test_model_registry_not_empty():
    assert len(MODEL_REGISTRY) > 10


def test_every_model_has_required_fields():
    for key, cfg in MODEL_REGISTRY.items():
        assert "env_id" in cfg, f"{key} missing env_id"
        assert "model" in cfg, f"{key} missing model"
        assert "url" in cfg, f"{key} missing url"
        assert "cost_tier" in cfg, f"{key} missing cost_tier"


def test_get_model_config_by_key():
    cfg = get_model_config("qwen3.5-397b")
    assert cfg is not None
    assert cfg["name"] == "PROD (397B)"


def test_get_model_config_by_env_id():
    cfg = get_model_config("prod")
    assert cfg is not None
    assert "397B" in cfg["model"]


def test_get_model_config_unknown():
    assert get_model_config("nonexistent-model") is None


def test_fallback_chains_exist():
    for key in MODEL_REGISTRY:
        assert key in FALLBACK_CHAINS, f"No fallback chain for {key}"


def test_fallback_chain_no_self_reference():
    for key, chain in FALLBACK_CHAINS.items():
        assert key not in chain, f"{key} references itself in fallback"


def test_get_max_tokens_high():
    tokens = get_max_tokens("qwen3.5-397b")
    assert tokens == 16384


def test_get_max_tokens_medium():
    tokens = get_max_tokens("glm-5")
    assert tokens == 8192


def test_get_max_tokens_low():
    tokens = get_max_tokens("glm-4.7")
    assert tokens == 4096


def test_classify_and_route_code():
    model = classify_and_route("코드를 구현해주세요. 함수를 작성해야 합니다.")
    assert "coder" in model


def test_classify_and_route_vision():
    model = classify_and_route("이 이미지를 분석해주세요", has_images=True)
    assert "vl" in model


def test_classify_and_route_simple():
    model = classify_and_route("hello")
    # Short prompt → common or dev model
    assert model in ("gpt-oss-120b", "glm-5", "glm-4.7")


def test_env_config_generated():
    assert "prod" in ENV_CONFIG
    assert "common" in ENV_CONFIG
    assert ENV_CONFIG["prod"]["model"] == "Qwen3.5-397B-A17B"


def test_list_text_models():
    models = list_text_models()
    assert len(models) > 5
    assert all("vl" not in m for m in models)


def test_list_vision_models():
    models = list_vision_models()
    assert len(models) >= 3
    assert all("vl" in m for m in models)
