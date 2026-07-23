"""Tests for flow_runner.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openroad_gui.config import AppConfig
from openroad_gui.flow_runner import FULL_PIPELINE, FlowRunner, FlowStage


class TestFlowStage:
    """Tests for FlowStage enum."""

    def test_enum_values(self) -> None:
        assert FlowStage.SYNTH.make_target == "synth"
        assert FlowStage.SYNTH.label == "Synthesis (Yosys)"
        assert FlowStage.FLOORPLAN.make_target == "floorplan"
        assert FlowStage.PLACE.make_target == "place"
        assert FlowStage.CTS.make_target == "cts"
        assert FlowStage.ROUTE.make_target == "route"
        assert FlowStage.GDS.make_target == "gds"

    def test_full_pipeline_order(self) -> None:
        assert FULL_PIPELINE == [
            FlowStage.SYNTH,
            FlowStage.FLOORPLAN,
            FlowStage.PLACE,
            FlowStage.CTS,
            FlowStage.ROUTE,
            FlowStage.GDS,
        ]


class TestFlowRunner:
    """Tests for FlowRunner class."""

    @pytest.fixture
    def runner(self) -> FlowRunner:
        config = AppConfig(
            orfs_root="/fake/orfs",
            design_config="./designs/asap7/alu4/config.mk",
            platform="asap7",
            design_name="alu4",
        )
        return FlowRunner(config)

    def test_initial_state(self, runner: FlowRunner) -> None:
        assert runner.is_running is False
        assert runner._process is None
        assert runner._thread is None
        assert runner._stop_requested is False

    def test_build_command_synth(self, runner: FlowRunner) -> None:
        cmd = runner.build_command(FlowStage.SYNTH)
        assert "source" in cmd
        assert "use-openroad.sh" in cmd
        assert "KLAYOUT_CMD" in cmd
        assert 'cd "/fake/orfs/flow"' in cmd
        assert "DESIGN_CONFIG=./designs/asap7/alu4/config.mk" in cmd
        assert "synth" in cmd

    def test_build_command_gds_uses_special_target(self, runner: FlowRunner) -> None:
        cmd = runner.build_command(FlowStage.GDS)
        assert "results/asap7/alu4/base/6_final.gds" in cmd

    def test_build_command_extra_env(self, runner: FlowRunner) -> None:
        runner.config.extra_env = {"FOO": "bar", "BAZ": "qux"}
        cmd = runner.build_command(FlowStage.SYNTH)
        assert 'export FOO="bar"' in cmd
        assert 'export BAZ="qux"' in cmd

    def test_is_running_false_initially(self, runner: FlowRunner) -> None:
        assert runner.is_running is False

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_run_stage_starts_thread(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        log_calls = []
        done_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        def on_done(exit_code: int, label: str) -> None:
            done_calls.append((exit_code, label))

        runner.run_stage(FlowStage.SYNTH, on_log, on_done)

        assert runner._thread is not None
        assert runner._thread.is_alive()
        assert runner._stop_requested is False
        mock_popen.assert_called_once()

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_run_stage_already_running(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        runner._process = mock_process

        log_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        runner.run_stage(FlowStage.SYNTH, on_log, lambda *args: None)

        assert any("already running" in line for _, line in log_calls)
        assert mock_popen.call_count == 0

    def test_stop_sets_flag_and_terminates(self, runner: FlowRunner) -> None:
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        runner._process = mock_process

        runner.stop()

        assert runner._stop_requested is True
        mock_process.terminate.assert_called_once()

    def test_stop_no_process(self, runner: FlowRunner) -> None:
        runner.stop()  # Should not raise
        assert runner._stop_requested is True

    def _make_mock_process(self, stdout_lines: list[str], stderr_lines: list[str], exit_code: int = 0) -> MagicMock:
        """Create a properly mocked process with readable pipes."""
        mock_process = MagicMock()

        # Create file-like objects for stdout/stderr
        stdout_content = "".join(stdout_lines)
        stderr_content = "".join(stderr_lines)

        import io
        mock_process.stdout = io.StringIO(stdout_content)
        mock_process.stderr = io.StringIO(stderr_content)
        mock_process.wait.return_value = exit_code
        mock_process.poll.side_effect = [None, exit_code]  # First call: running, second: done

        return mock_process

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_run_shell_captures_output(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        import io
        mock_process = MagicMock()
        mock_process.stdout = io.StringIO("line1\nline2\n")
        mock_process.stderr = io.StringIO("err1\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        log_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        exit_code = runner._run_shell("test command", on_log)

        assert exit_code == 0
        assert ("stdout", "line1\n") in log_calls
        assert ("stdout", "line2\n") in log_calls
        assert ("stderr", "err1\n") in log_calls

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_run_shell_handles_oserror(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        mock_popen.side_effect = OSError("Permission denied")

        log_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        exit_code = runner._run_shell("test command", on_log)

        assert exit_code == 1
        assert any("Failed to start process" in line for _, line in log_calls)

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_run_shell_stops_on_request(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        import io
        mock_process = MagicMock()
        mock_process.stdout = io.StringIO("line1\nline2\n")
        mock_process.stderr = io.StringIO("")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        log_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        runner._stop_requested = True
        exit_code = runner._run_shell("test command", on_log)

        # Should still process but stop early
        assert exit_code == 0

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_execute_pipeline_runs_all_stages(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        import io
        mock_process = MagicMock()
        mock_process.stdout = io.StringIO("output\n")
        mock_process.stderr = io.StringIO("")
        mock_process.wait.return_value = 0
        mock_process.poll.side_effect = [None, 0] * 6  # 6 stages
        mock_popen.return_value = mock_process

        log_calls = []
        done_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        def on_done(exit_code: int, label: str) -> None:
            done_calls.append((exit_code, label))

        runner._execute_pipeline(FULL_PIPELINE, on_log, on_done)

        # Should run all 6 stages
        assert mock_popen.call_count == 6
        assert len(done_calls) == 1
        assert done_calls[0] == (0, "Full Pipeline")
        assert any("Pipeline completed successfully" in line for _, line in log_calls)

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_execute_pipeline_stops_on_failure(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        import io
        mock_process = MagicMock()
        mock_process.stdout = io.StringIO("output\n")
        mock_process.stderr = io.StringIO("")
        # First stage succeeds, second fails
        mock_process.wait.side_effect = [0, 1]
        mock_process.poll.side_effect = [None, 0, None, 1]  # Running, done, running, done
        mock_popen.return_value = mock_process

        log_calls = []
        done_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        def on_done(exit_code: int, label: str) -> None:
            done_calls.append((exit_code, label))

        runner._execute_pipeline(FULL_PIPELINE, on_log, on_done)

        assert mock_popen.call_count == 2  # Only 2 stages run
        assert len(done_calls) == 1
        assert done_calls[0][0] == 1
        assert "Pipeline halted" in " ".join(line for _, line in log_calls)

    @patch("openroad_gui.flow_runner.subprocess.Popen")
    def test_execute_pipeline_respects_stop_request(self, mock_popen: MagicMock, runner: FlowRunner) -> None:
        import io
        mock_process = MagicMock()
        mock_process.stdout = io.StringIO("output\n")
        mock_process.stderr = io.StringIO("")
        mock_process.wait.return_value = 0
        mock_process.poll.side_effect = [None, 0]
        mock_popen.return_value = mock_process

        log_calls = []
        done_calls = []

        def on_log(stream: str, line: str) -> None:
            log_calls.append((stream, line))

        def on_done(exit_code: int, label: str) -> None:
            done_calls.append((exit_code, label))

        runner._stop_requested = True
        runner._execute_pipeline(FULL_PIPELINE, on_log, on_done)

        assert mock_popen.call_count == 0
        assert len(done_calls) == 1
        assert done_calls[0] == (130, "Pipeline")
        assert any("Pipeline stopped by user" in line for _, line in log_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])