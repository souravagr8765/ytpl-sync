import pytest
from pydantic import ValidationError
from ytpl_sync.config import AppConfig
import tempfile
import yaml
from pathlib import Path

def test_valid_config_loads():
    cfg = AppConfig(**{"settings": {"lock_file": "a.lock"}, "sources": [{"type": "playlist", "name": "test", "url": "url"}]})
    assert cfg.sources[0].name == "test"

def test_missing_required_field():
    with pytest.raises(ValidationError):
        AppConfig(**{"settings": {"lock_file": "a.lock"}}) # Missing sources

def test_per_source_override():
    cfg = AppConfig(**{
        "settings": {"lock_file": "a.lock"},
        "encoding": {"enabled": True},
        "sources": [
            {"type": "playlist", "name": "test1", "url": "url", "encoding": {"enabled": False}}
        ]
    })
    eff_config = cfg.get_effective_config(cfg.sources[0])
    assert eff_config["encoding"]["enabled"] is False

def test_tilde_expansion():
    cfg = AppConfig(**{
        "settings": {"lock_file": "~/test.lock"},
        "sources": [{"type": "playlist", "name": "test", "url": "url"}]
    })
    assert not cfg.settings.lock_file.startswith("~")
    assert Path(cfg.settings.lock_file).is_absolute()

