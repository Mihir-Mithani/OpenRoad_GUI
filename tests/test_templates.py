"""Tests for templates (templates.py)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from openroad_gui.templates import (
    config_mk_template,
    create_design,
    design_config_json,
    sdc_template,
    testbench_template as _testbench_template,
    verilog_template,
    write_template_file,
)


class TestVerilogTemplate:
    """Tests for verilog_template."""

    def test_basic_template(self) -> None:
        result = verilog_template("my_module")
        assert "module my_module" in result
        assert "input  wire        clk" in result
        assert "input  wire        rst_n" in result
        assert "input  wire [3:0]  data_in" in result
        assert "output reg  [3:0]  data_out" in result
        assert "always @(posedge clk)" in result
        assert "endmodule" in result

    def test_different_names(self) -> None:
        for name in ["alu", "fifo", "controller", "MyModule_123"]:
            result = verilog_template(name)
            assert f"module {name}" in result
            assert "endmodule" in result


class TestTestbenchTemplate:
    """Tests for testbench_template."""

    def test_basic_template(self) -> None:
        result = _testbench_template("my_module")
        assert "`timescale 1ns / 1ps" in result
        assert "module my_module_tb" in result
        assert "my_module uut" in result
        assert "always #5 clk = ~clk" in result
        assert "$dumpfile(\"my_module_tb.vcd\")" in result
        assert "$dumpvars(0, my_module_tb)" in result
        assert "$finish" in result

    def test_different_names(self) -> None:
        for name in ["alu", "fifo", "controller"]:
            result = _testbench_template(name)
            assert f"module {name}_tb" in result
            assert f"{name} uut" in result
            assert f"$dumpfile(\"{name}_tb.vcd\")" in result


class TestSdcTemplate:
    """Tests for sdc_template."""

    def test_basic_template(self) -> None:
        result = sdc_template("my_module", 2.5)
        assert 'create_clock -name clk -period 2.5 [get_ports clk]' in result
        assert 'set_input_delay  -clock clk 0.2 [get_ports {data_in}]' in result
        assert 'set_output_delay -clock clk 0.2 [get_ports {data_out}]' in result

    def test_default_period(self) -> None:
        result = sdc_template("my_module")
        assert 'create_clock -name clk -period 1.0 [get_ports clk]' in result

    def test_custom_period(self) -> None:
        result = sdc_template("my_module", 5.0)
        assert 'create_clock -name clk -period 5.0 [get_ports clk]' in result


class TestConfigMkTemplate:
    """Tests for config_mk_template."""

    def test_basic_template(self) -> None:
        result = config_mk_template("my_design", "sky130hd")
        assert "export DESIGN_NAME = my_design" in result
        assert "export PLATFORM    = sky130hd" in result
        assert "export VERILOG_FILES = $(DESIGN_DIR)/my_design.v" in result
        assert "export SDC_FILE      = $(DESIGN_DIR)/my_design.sdc" in result
        assert "export CORE_UTILIZATION  = 20" in result
        assert "export CORE_ASPECT_RATIO = 1" in result
        assert "export CORE_MARGIN       = 4" in result

    def test_custom_utilization_and_margin(self) -> None:
        result = config_mk_template("my_design", "sky130hd", core_utilization=30, core_margin=6)
        assert "export CORE_UTILIZATION  = 30" in result
        assert "export CORE_MARGIN       = 6" in result

    def test_different_platforms(self) -> None:
        for platform in ["asap7", "sky130hd", "nangate45", "gf180"]:
            result = config_mk_template("my_design", platform)
            assert f"export PLATFORM    = {platform}" in result


class TestDesignConfigJson:
    """Tests for design_config_json."""

    def test_basic_json(self) -> None:
        result = design_config_json("my_design", "sky130hd", "my_design.v", "my_design.sdc")
        data = json.loads(result)
        assert data["design_name"] == "my_design"
        assert data["platform"] == "sky130hd"
        assert data["verilog_files"] == ["my_design.v"]
        assert data["sdc_file"] == "my_design.sdc"
        assert data["core_utilization"] == 20
        assert data["core_aspect_ratio"] == 1
        assert data["core_margin"] == 4

    def test_valid_json(self) -> None:
        result = design_config_json("my_design", "sky130hd", "my_design.v", "my_design.sdc")
        # Should not raise
        json.loads(result)
        assert result.endswith("\n")


class TestCreateDesign:
    """Tests for create_design function."""

    @pytest.fixture
    def temp_designs_dir(self) -> Path:
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_creates_design_directory(self, temp_designs_dir: Path) -> None:
        config_path = create_design(temp_designs_dir, "sky130hd", "my_design")
        expected_dir = temp_designs_dir / "sky130hd" / "my_design"
        assert expected_dir.is_dir()
        assert config_path == expected_dir / "config.mk"

    def test_creates_verilog_file(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design")
        verilog_path = temp_designs_dir / "sky130hd" / "my_design" / "my_design.v"
        assert verilog_path.is_file()
        content = verilog_path.read_text()
        assert "module my_design" in content

    def test_creates_sdc_file(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design")
        sdc_path = temp_designs_dir / "sky130hd" / "my_design" / "my_design.sdc"
        assert sdc_path.is_file()
        content = sdc_path.read_text()
        assert "create_clock" in content

    def test_creates_config_mk(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design")
        config_path = temp_designs_dir / "sky130hd" / "my_design" / "config.mk"
        assert config_path.is_file()
        content = config_path.read_text()
        assert "export DESIGN_NAME = my_design" in content
        assert "export PLATFORM    = sky130hd" in content

    def test_creates_testbench_by_default(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design")
        tb_path = temp_designs_dir / "sky130hd" / "my_design" / "my_design.tb"
        assert tb_path.is_file()
        content = tb_path.read_text()
        assert "module my_design_tb" in content

    def test_skips_testbench_when_false(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design", include_testbench=False)
        tb_path = temp_designs_dir / "sky130hd" / "my_design" / "my_design.tb"
        assert not tb_path.exists()

    def test_creates_config_json(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design")
        json_path = temp_designs_dir / "sky130hd" / "my_design" / "config.json"
        assert json_path.is_file()
        data = json.loads(json_path.read_text())
        assert data["design_name"] == "my_design"
        assert data["platform"] == "sky130hd"
        assert data["verilog_files"] == ["my_design.v"]
        assert data["sdc_file"] == "my_design.sdc"

    def test_custom_clock_period(self, temp_designs_dir: Path) -> None:
        create_design(temp_designs_dir, "sky130hd", "my_design", clock_period=5.0)
        sdc_path = temp_designs_dir / "sky130hd" / "my_design" / "my_design.sdc"
        content = sdc_path.read_text()
        assert "create_clock -name clk -period 5.0" in content

    def test_returns_config_path(self, temp_designs_dir: Path) -> None:
        config_path = create_design(temp_designs_dir, "sky130hd", "my_design")
        assert config_path.name == "config.mk"
        assert config_path.parent.name == "my_design"

    def test_idempotent(self, temp_designs_dir: Path) -> None:
        # Call twice - should not raise
        create_design(temp_designs_dir, "sky130hd", "my_design")
        create_design(temp_designs_dir, "sky130hd", "my_design")
        assert (temp_designs_dir / "sky130hd" / "my_design").is_dir()


class TestWriteTemplateFile:
    """Tests for write_template_file function."""

    @pytest.fixture
    def temp_target_dir(self) -> Path:
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_write_verilog(self, temp_target_dir: Path) -> None:
        path = write_template_file(temp_target_dir, "verilog", "my_module")
        assert path.name == "my_module.v"
        content = path.read_text()
        assert "module my_module" in content

    def test_write_testbench(self, temp_target_dir: Path) -> None:
        path = write_template_file(temp_target_dir, "testbench", "my_module")
        assert path.name == "my_module.tb"
        content = path.read_text()
        assert "module my_module_tb" in content

    def test_write_sdc(self, temp_target_dir: Path) -> None:
        path = write_template_file(temp_target_dir, "sdc", "my_module")
        assert path.name == "my_module.sdc"
        content = path.read_text()
        assert "create_clock" in content

    def test_write_config_mk(self, temp_target_dir: Path) -> None:
        path = write_template_file(temp_target_dir, "config_mk", "my_module", platform="sky130hd")
        assert path.name == "config.mk"
        content = path.read_text()
        assert "export DESIGN_NAME = my_module" in content
        assert "export PLATFORM    = sky130hd" in content

    def test_write_config_json(self, temp_target_dir: Path) -> None:
        path = write_template_file(temp_target_dir, "config_json", "my_module", platform="sky130hd")
        assert path.name == "config.json"
        content = path.read_text()
        data = json.loads(content)
        assert data["design_name"] == "my_module"
        assert data["platform"] == "sky130hd"

    def test_unknown_template_type(self, temp_target_dir: Path) -> None:
        with pytest.raises(ValueError, match="Unknown template type"):
            write_template_file(temp_target_dir, "unknown_type", "my_module")

    def test_creates_target_directory(self, temp_target_dir: Path) -> None:
        subdir = temp_target_dir / "subdir"
        path = write_template_file(subdir, "verilog", "my_module")
        assert path.parent == subdir
        assert subdir.is_dir()


class TestTemplateIntegration:
    """Integration-style tests for templates."""

    def test_create_design_then_write_additional_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            designs_dir = Path(tmpdir)
            create_design(designs_dir, "sky130hd", "my_design")
            # Add extra verilog file
            write_template_file(designs_dir / "sky130hd" / "my_design", "verilog", "extra_module")
            extra_path = designs_dir / "sky130hd" / "my_design" / "extra_module.v"
            assert extra_path.is_file()
            content = extra_path.read_text()
            assert "module extra_module" in content

    def test_all_templates_produce_valid_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            for template_type in ["verilog", "testbench", "sdc", "config_mk", "config_json"]:
                if template_type in ["config_mk", "config_json"]:
                    path = write_template_file(target, template_type, "test", platform="sky130hd")
                else:
                    path = write_template_file(target, template_type, "test")
                assert path.is_file()
                content = path.read_text()
                assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])