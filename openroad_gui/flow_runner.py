"""Execute OpenROAD flow stages as subprocesses."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from openroad_gui.config import AppConfig

LogCallback = Callable[[str, str], None]  # (stream, line)
DoneCallback = Callable[[int, str], None]  # (exit_code, stage_name)

class FlowStage(Enum):
    SYNTH = ("synth", "Synthesis (Yosys)")
    FLOORPLAN = ("floorplan", "Floorplan / Macro Placement")
    PLACE = ("place", "Core Placement")
    CTS = ("cts", "Clock Tree Synthesis")
    ROUTE = ("route", "Routing & DRC")
    GDS = ("gds", "GDSII Generation")

    def __init__(self, make_target: str, label: str) -> None:
        self.make_target = make_target
        self.label = label


FULL_PIPELINE = [
    FlowStage.SYNTH,
    FlowStage.FLOORPLAN,
    FlowStage.PLACE,
    FlowStage.CTS,
    FlowStage.ROUTE,
    FlowStage.GDS,
]


@dataclass
class FlowJob:
    stage: FlowStage
    command: str


class FlowRunner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._stop_requested = False

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def build_command(self, stage: FlowStage) -> str:
        cfg = self.config
        design_config = cfg.design_config
        flow_dir = cfg.flow_dir
        env_script = cfg.env_script

        if stage == FlowStage.GDS:
            make_target = cfg.gds_target()
        else:
            make_target = stage.make_target

        extra_exports = "\n".join(
            f'export {key}="{value}"' for key, value in cfg.extra_env.items()
        )
        klayout_export = f'export KLAYOUT_CMD="{cfg.klayout_cmd}"'

        return (
            f'set -e\n'
            f'source "{env_script}"\n'
            f'{klayout_export}\n'
            f'{extra_exports}\n'
            f'cd "{flow_dir}"\n'
            f'echo ">>> Running: make DESIGN_CONFIG={design_config} {make_target}"\n'
            f'make DESIGN_CONFIG={design_config} {make_target}\n'
        )

    def run_stage(
        self,
        stage: FlowStage,
        on_log: LogCallback,
        on_done: DoneCallback,
    ) -> None:
        if self.is_running:
            on_log("stderr", "A flow stage is already running.\n")
            return

        self._stop_requested = False
        command = self.build_command(stage)
        self._thread = threading.Thread(
            target=self._execute,
            args=(command, stage.label, on_log, on_done),
            daemon=True,
        )
        self._thread.start()

    def run_pipeline(
        self,
        stages: list[FlowStage],
        on_log: LogCallback,
        on_done: DoneCallback,
    ) -> None:
        if self.is_running:
            on_log("stderr", "A flow stage is already running.\n")
            return

        self._stop_requested = False
        self._thread = threading.Thread(
            target=self._execute_pipeline,
            args=(stages, on_log, on_done),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_requested = True
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def _execute(
        self,
        command: str,
        label: str,
        on_log: LogCallback,
        on_done: DoneCallback,
    ) -> None:
        exit_code = self._run_shell(command, on_log)
        on_done(exit_code, label)

    def _execute_pipeline(
        self,
        stages: list[FlowStage],
        on_log: LogCallback,
        on_done: DoneCallback,
    ) -> None:
        on_log("stdout", f"=== Starting full pipeline ({len(stages)} stages) ===\n")
        for stage in stages:
            if self._stop_requested:
                on_log("stderr", "Pipeline stopped by user.\n")
                on_done(130, "Pipeline")
                return

            on_log("stdout", f"\n=== Stage: {stage.label} ===\n")
            command = self.build_command(stage)
            exit_code = self._run_shell(command, on_log)
            if exit_code != 0:
                on_log(
                    "stderr",
                    f"Pipeline halted: {stage.label} failed (exit {exit_code}).\n",
                )
                on_done(exit_code, stage.label)
                return

        on_log("stdout", "\n=== Pipeline completed successfully ===\n")
        on_done(0, "Full Pipeline")

    def _run_shell(self, command: str, on_log: LogCallback) -> int:
        try:
            self._process = subprocess.Popen(
                ["/bin/bash", "-lc", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            on_log("stderr", f"Failed to start process: {exc}\n")
            return 1

        assert self._process.stdout is not None
        assert self._process.stderr is not None

        def drain(stream_name: str, pipe) -> None:
            for line in iter(pipe.readline, ""):
                if self._stop_requested:
                    break
                on_log(stream_name, line)

        stdout_thread = threading.Thread(
            target=drain, args=("stdout", self._process.stdout), daemon=True
        )
        stderr_thread = threading.Thread(
            target=drain, args=("stderr", self._process.stderr), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()

        return self._process.wait()
