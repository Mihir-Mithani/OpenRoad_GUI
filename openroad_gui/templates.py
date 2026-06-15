"""File templates for new OpenROAD designs."""

from __future__ import annotations

from pathlib import Path


def verilog_template(module_name: str) -> str:
    return f"""module {module_name} (
  input  wire        clk,
  input  wire        rst_n,
  input  wire [3:0]  data_in,
  output reg  [3:0]  data_out
);
  always @(posedge clk) begin
    if (!rst_n)
      data_out <= 4'b0;
    else
      data_out <= data_in;
  end
endmodule
"""


def testbench_template(module_name: str) -> str:
    return f"""`timescale 1ns / 1ps

module {module_name}_tb;
  reg        clk = 0;
  reg        rst_n = 0;
  reg  [3:0] data_in = 4'b0;
  wire [3:0] data_out;

  {module_name} uut (
    .clk      (clk),
    .rst_n    (rst_n),
    .data_in  (data_in),
    .data_out (data_out)
  );

  always #5 clk = ~clk;

  initial begin
    $dumpfile("{module_name}_tb.vcd");
    $dumpvars(0, {module_name}_tb);

    #20 rst_n = 1;
    #10 data_in = 4'hA;
    #10 data_in = 4'hF;
    #20 $finish;
  end
endmodule
"""


def sdc_template(module_name: str, clock_period: float = 1.0) -> str:
    return f"""create_clock -name clk -period {clock_period} [get_ports clk]
set_input_delay  -clock clk 0.2 [get_ports {{data_in}}]
set_output_delay -clock clk 0.2 [get_ports {{data_out}}]
"""


def config_mk_template(
    design_name: str,
    platform: str,
    core_utilization: int = 20,
    core_margin: int = 4,
) -> str:
    return f"""export DESIGN_NAME = {design_name}
export PLATFORM    = {platform}

export VERILOG_FILES = $(DESIGN_DIR)/{design_name}.v
export SDC_FILE      = $(DESIGN_DIR)/{design_name}.sdc

export CORE_UTILIZATION  = {core_utilization}
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN       = {core_margin}
"""


def design_config_json(
    design_name: str,
    platform: str,
    verilog_file: str,
    sdc_file: str,
) -> str:
    import json

    payload = {
        "design_name": design_name,
        "platform": platform,
        "verilog_files": [verilog_file],
        "sdc_file": sdc_file,
        "core_utilization": 20,
        "core_aspect_ratio": 1,
        "core_margin": 4,
    }
    return json.dumps(payload, indent=2) + "\n"


def create_design(
    designs_dir: Path,
    platform: str,
    design_name: str,
    *,
    include_testbench: bool = True,
    clock_period: float = 1.0,
) -> Path:
    """Create a new design directory with starter files."""
    design_dir = designs_dir / platform / design_name
    design_dir.mkdir(parents=True, exist_ok=True)

    verilog_path = design_dir / f"{design_name}.v"
    sdc_path = design_dir / f"{design_name}.sdc"
    config_path = design_dir / "config.mk"

    verilog_path.write_text(verilog_template(design_name), encoding="utf-8")
    sdc_path.write_text(sdc_template(design_name, clock_period), encoding="utf-8")
    config_path.write_text(
        config_mk_template(design_name, platform), encoding="utf-8"
    )

    if include_testbench:
        tb_path = design_dir / f"{design_name}.tb"
        tb_path.write_text(testbench_template(design_name), encoding="utf-8")

    json_path = design_dir / "config.json"
    json_path.write_text(
        design_config_json(
            design_name,
            platform,
            f"{design_name}.v",
            f"{design_name}.sdc",
        ),
        encoding="utf-8",
    )

    return config_path


def write_template_file(
    target_dir: Path,
    template_type: str,
    module_name: str,
    platform: str = "asap7",
) -> Path:
    """Write a single template file into an existing directory."""
    target_dir.mkdir(parents=True, exist_ok=True)

    writers = {
        "verilog": lambda: (f"{module_name}.v", verilog_template(module_name)),
        "testbench": lambda: (f"{module_name}.tb", testbench_template(module_name)),
        "sdc": lambda: (f"{module_name}.sdc", sdc_template(module_name)),
        "config_mk": lambda: (
            "config.mk",
            config_mk_template(module_name, platform),
        ),
        "config_json": lambda: (
            "config.json",
            design_config_json(
                module_name, platform, f"{module_name}.v", f"{module_name}.sdc"
            ),
        ),
    }

    if template_type not in writers:
        raise ValueError(f"Unknown template type: {template_type}")

    filename, content = writers[template_type]()
    path = target_dir / filename
    path.write_text(content, encoding="utf-8")
    return path
