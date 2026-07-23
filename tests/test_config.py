"""Tests for configuration management (config.py)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from openroad_gui.config import AppConfig, load_config, save_config, PLATFORMS


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self) -> None:
        config = AppConfig()
        assert config.orfs_root == "/Users/mihirmithani/Documents/Codex/2026-06-02/i-want-you-to-setup-openroad/OpenROAD-flow-scripts"
        assert config.klayout_cmd == "/Applications/KLayout/klayout.app/Contents/MacOS/klayout"
        assert config.design_config == "./designs/asap7/alu4/config.mk"
        assert config.platform == "asap7"
        assert config.design_name == "alu4"
        assert config.extra_env == {}
        assert config.last_project_dir == ""

    def test_custom_values(self) -> None:
        config = AppConfig(
            orfs_root="/custom/path",
            klayout_cmd="/custom/klayout",
            design_config="./designs/sky130hd/my_design/config.mk",
            platform="sky130hd",
            design_name="my_design",
            extra_env={"FOO": "bar"},
            last_project_dir="/last/dir",
        )
        assert config.orfs_root == "/custom/path"
        assert config.platform == "sky130hd"
        assert config.extra_env == {"FOO": "bar"}

    def test_flow_dir_property(self) -> None:
        config = AppConfig(orfs_root="/home/user/OpenROAD-flow-scripts")
        assert config.flow_dir == Path("/home/user/OpenROAD-flow-scripts/flow")

    def test_designs_dir_property(self) -> None:
        config = AppConfig(orfs_root="/home/user/OpenROAD-flow-scripts")
        assert config.designs_dir == Path("/home/user/OpenROAD-flow-scripts/flow/designs")

    def test_env_script_property(self) -> None:
        config = AppConfig(orfs_root="/home/user/OpenROAD-flow-scripts")
        assert config.env_script == Path("/home/user/OpenROAD-flow-scripts/use-openroad.sh")

    def test_results_dir_property(self) -> None:
        config = AppConfig(
            orfs_root="/home/user/OpenROAD-flow-scripts",
            platform="sky130hd",
            design_name="my_design",
        )
        assert config.results_dir == Path("/home/user/OpenROAD-flow-scripts/flow/results/sky130hd/my_design")

    def test_gds_target(self) -> None:
        config = AppConfig(
            orfs_root="/home/user/OpenROAD-flow-scripts",
            platform="sky130hd",
            design_name="my_design",
        )
        target = config.gds_target()
        assert target == "results/sky130hd/my_design/base/6_final.gds"

    def test_update_from_design_config_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            orfs = tmp / "OpenROAD-flow-scripts"
            flow = orfs / "flow"
            designs = flow / "designs" / "sky130hd" / "my_design"
            designs.mkdir(parents=True)
            config_file = designs / "config.mk"
            config_file.write_text("")

            config = AppConfig(orfs_root=str(orfs))
            config.update_from_design_config("./designs/sky130hd/my_design/config.mk")
            assert config.platform == "sky130hd"
            assert config.design_name == "my_design"
            assert config.design_config == "./designs/sky130hd/my_design/config.mk"

    def test_update_from_design_config_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            orfs = tmp / "OpenROAD-flow-scripts"
            flow = orfs / "flow"
            designs = flow / "designs" / "sky130hd" / "my_design"
            designs.mkdir(parents=True)
            config_file = designs / "config.mk"
            config_file.write_text("")

            config = AppConfig(orfs_root=str(orfs))
            abs_path = str(config_file)
            config.update_from_design_config(abs_path)
            assert config.platform == "sky130hd"
            assert config.design_name == "my_design"

    def test_update_from_design_config_nonexistent(self) -> None:
        config = AppConfig(
            orfs_root="/home/user/OpenROAD-flow-scripts",
            platform="asap7",
            design_name="alu4",
        )
        original_platform = config.platform
        original_design = config.design_name
        config.update_from_design_config("./designs/nonexistent/config.mk")
        assert config.platform == original_platform
        assert config.design_name == original_design

    def test_update_from_design_config_outside_flow_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            orfs = tmp / "OpenROAD-flow-scripts"
            orfs.mkdir()
            external = tmp / "external" / "path"
            external.mkdir(parents=True)
            config_file = external / "config.mk"
            config_file.write_text("")

            config = AppConfig(orfs_root=str(orfs))
            config.update_from_design_config(str(config_file))
            assert config.design_config == str(config_file)

    def test_validate_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            orfs = tmp / "OpenROAD-flow-scripts"
            flow = orfs / "flow"
            (flow / "designs").mkdir(parents=True)
            (orfs / "use-openroad.sh").write_text("#!/bin/bash\necho hello")

            config = AppConfig(orfs_root=str(orfs))
            errors = config.validate()
            assert errors == []

    def test_validate_missing_orfs(self) -> None:
        config = AppConfig(orfs_root="/nonexistent/path")
        errors = config.validate()
        assert any("OpenROAD root not found" in e for e in errors)

    def test_validate_missing_flow_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            orfs = Path(tmpdir) / "OpenROAD-flow-scripts"
            orfs.mkdir()
            config = AppConfig(orfs_root=str(orfs))
            errors = config.validate()
            assert any("flow/ directory missing" in e for e in errors)

    def test_validate_missing_env_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            orfs = Path(tmpdir) / "OpenROAD-flow-scripts"
            flow = orfs / "flow"
            flow.mkdir(parents=True)
            config = AppConfig(orfs_root=str(orfs))
            errors = config.validate()
            assert any("use-openroad.sh not found" in e for e in errors)


class TestConfigWithTempDir:
    """Tests for load_config/save_config using temporary config directory."""

    @pytest.fixture(autouse=True)
    def _setup_temp_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Patch CONFIG_DIR and CONFIG_FILE to use temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_config_dir = Path(self.temp_dir.name) / "openroad-gui"
        temp_config_file = temp_config_dir / "config.json"

        import openroad_gui.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)

        yield

        self.temp_dir.cleanup()

    def test_load_nonexistent_returns_default(self) -> None:
        config = load_config()
        assert isinstance(config, AppConfig)
        assert config.orfs_root == AppConfig().orfs_root

    def test_load_valid_config(self) -> None:
        data = {
            "orfs_root": "/custom/path",
            "klayout_cmd": "/custom/klayout",
            "design_config": "./designs/sky130hd/test/config.mk",
            "platform": "sky130hd",
            "design_name": "test",
            "extra_env": {"FOO": "bar"},
            "last_project_dir": "/last",
        }
        # Create config directory and file
        from openroad_gui.config import CONFIG_DIR, CONFIG_FILE
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data))

        config = load_config()
        assert config.orfs_root == "/custom/path"
        assert config.platform == "sky130hd"
        assert config.extra_env == {"FOO": "bar"}

    def test_load_invalid_json_returns_default(self) -> None:
        from openroad_gui.config import CONFIG_DIR, CONFIG_FILE
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text("{ invalid json }")

        config = load_config()
        assert isinstance(config, AppConfig)
        assert config.orfs_root == AppConfig().orfs_root

    def test_load_missing_fields_uses_defaults(self) -> None:
        from openroad_gui.config import CONFIG_DIR, CONFIG_FILE
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"orfs_root": "/custom/path"}  # Only partial
        CONFIG_FILE.write_text(json.dumps(data))

        config = load_config()
        assert config.orfs_root == "/custom/path"
        assert config.platform == "asap7"  # default
        assert config.design_name == "alu4"  # default

    def test_load_extra_env_not_dict(self) -> None:
        from openroad_gui.config import CONFIG_DIR, CONFIG_FILE
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"extra_env": "not a dict"}
        CONFIG_FILE.write_text(json.dumps(data))

        config = load_config()
        assert config.extra_env == {}

    def test_save_creates_file(self) -> None:
        from openroad_gui.config import CONFIG_DIR, CONFIG_FILE
        config = AppConfig(orfs_root="/test/path")
        save_config(config)

        assert CONFIG_FILE.exists()
        data = json.loads(CONFIG_FILE.read_text())
        assert data["orfs_root"] == "/test/path"
        assert data["platform"] == "asap7"

    def test_save_preserves_extra_env(self) -> None:
        from openroad_gui.config import CONFIG_DIR, CONFIG_FILE
        config = AppConfig(extra_env={"FOO": "bar", "BAZ": "qux"})
        save_config(config)

        data = json.loads(CONFIG_FILE.read_text())
        assert data["extra_env"] == {"FOO": "bar", "BAZ": "qux"}


class TestPlatforms:
    """Tests for PLATFORMS list."""

    def test_all_platforms_present(self) -> None:
        expected = {
            "asap7", "nangate45", "sky130hd", "sky130hs",
            "gf12", "gf180", "ihp-sg13g2",
        }
        assert set(PLATFORMS) == expected


class TestConfigIntegration:
    """Integration-style tests."""

    def test_roundtrip_save_load(self, monkeypatch: pytest.MonkeyPatch) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        temp_config_dir = Path(temp_dir.name) / "openroad-gui"
        temp_config_file = temp_config_dir / "config.json"

        import openroad_gui.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_config_file)

        original = AppConfig(
            orfs_root="/custom/orfs",
            klayout_cmd="/custom/klayout",
            design_config="./designs/sky130hd/test/config.mk",
            platform="sky130hd",
            design_name="test",
            extra_env={"ENV1": "val1", "ENV2": "val2"},
            last_project_dir="/last/dir",
        )
        save_config(original)

        loaded = load_config()
        assert loaded.orfs_root == original.orfs_root
        assert loaded.klayout_cmd == original.klayout_cmd
        assert loaded.design_config == original.design_config
        assert loaded.platform == original.platform
        assert loaded.design_name == original.design_name
        assert loaded.extra_env == original.extra_env
        assert loaded.last_project_dir == original.last_project_dir

        temp_dir.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])