#!/usr/bin/env python3
"""
===============================================================================
ORFS Data Collection Master Script
===============================================================================
Master orchestration script for collecting ORFS run data across multiple
platforms and designs. Designed for distributed execution across multiple
machines with resume capability, progress tracking, and automatic result
aggregation.

Features:
- Multi-platform support (asap7, sky130hd, nangate45, gf180, etc.)
- Parallel execution with configurable workers
- Resume capability with checkpointing
- Progress tracking with ETA
- Automatic result aggregation
- Failed run detection and retry logic
- Integration with existing OpenRoad-GUI data pipeline
- Remote execution support via SSH

Usage:
    python orfs_data_collection_master.py --orfs-root ~/OpenROAD-flow-scripts \\
        --platforms asap7 sky130hd gf180 --workers 4 --output ./collected_data

For remote execution:
    python orfs_data_collection_master.py --remote-host user@remote.host \\
        --remote-orfs-root ~/OpenROAD-flow-scripts --platforms sky130hd
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import signal
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import threading
import queue

# Try to import optional dependencies
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_PLATFORMS = ["asap7", "sky130hd", "nangate45", "gf180"]
DEFAULT_WORKERS = 4
CHECKPOINT_INTERVAL = 10  # Save checkpoint every N designs
DEFAULT_TIMEOUT = 7200  # 2 hours per design

# Supported platforms with their design directories
PLATFORM_DESIGNS = {
    "asap7": ["alu4", "adder", "multiplier", "divider", "fpu", "riscv32i"],
    "sky130hd": ["gcd", "uart", "spi", "i2c", "pwm", "riscv32i"],
    "nangate45": ["picorv32", "aes", "des", "sha256", "riscv32i"],
    "gf180": ["riscv32i", "jpeg", "aes", "gcd", "uart-blocks", "ibex"],
    "ihp-sg13g2": ["adc", "dac", "pll", "ldo"],
    "sky130hs": ["gcd", "uart", "spi"],
}

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CollectionConfig:
    """Configuration for data collection run."""
    orfs_root: str
    platforms: List[str]
    designs: Optional[Dict[str, List[str]]] = None
    output_dir: str = "./collected_data"
    workers: int = DEFAULT_WORKERS
    timeout: int = DEFAULT_TIMEOUT
    retry_failed: bool = True
    max_retries: int = 2
    remote_host: Optional[str] = None
    remote_user: Optional[str] = None
    remote_orfs_root: Optional[str] = None
    ssh_key_path: Optional[str] = None
    resume: bool = True
    checkpoint_interval: int = CHECKPOINT_INTERVAL
    log_level: str = "INFO"


@dataclass
class DesignResult:
    """Result of collecting data for a single design."""
    platform: str
    design: str
    success: bool
    record: Optional[Dict] = None
    error: Optional[str] = None
    runtime_sec: float = 0.0
    retries: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CollectionState:
    """Persistent state for resume capability."""
    config: CollectionConfig
    completed: Dict[str, DesignResult] = field(default_factory=dict)
    failed: Dict[str, DesignResult] = field(default_factory=dict)
    pending: List[tuple] = field(default_factory=list)  # (platform, design)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checkpoint: str = field(default_factory=lambda: datetime.now().isoformat())
    total_designs: int = 0
    version: str = "1.0"


# =============================================================================
# Remote Execution
# =============================================================================

class RemoteExecutor:
    """Execute commands on remote host via SSH."""

    def __init__(self, host: str, user: str, key_path: Optional[str] = None):
        if not HAS_PARAMIKO:
            raise RuntimeError("paramiko required for remote execution. Install: pip install paramiko")

        self.host = host
        self.user = user
        self.key_path = key_path
        self.client: Optional[paramiko.SSHClient] = None
        self._connect()

    def _connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if self.key_path:
            key = paramiko.RSAKey.from_private_key_file(self.key_path)
            self.client.connect(self.host, username=self.user, pkey=key)
        else:
            self.client.connect(self.host, username=self.user)

    def execute(self, command: str, timeout: int = 300) -> tuple:
        """Execute command on remote host. Returns (stdout, stderr, exit_code)."""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_code

    def upload_file(self, local_path: str, remote_path: str):
        """Upload file to remote host."""
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()

    def download_file(self, remote_path: str, local_path: str):
        """Download file from remote host."""
        sftp = self.client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()

    def close(self):
        if self.client:
            self.client.close()


# =============================================================================
# Local Collector
# =============================================================================

class LocalCollector:
    """Collect data from local ORFS installation."""

    def __init__(self, orfs_root: str):
        from openroad_gui.intelligence.data.collect_real_data import RealDataCollector
        self.collector = RealDataCollector(orfs_root)

    def collect_design(self, platform: str, design: str, timeout: int = 7200) -> Optional[Dict]:
        """Collect data for a single design."""
        try:
            record = self.collector._collect_design(platform, design)
            if record:
                return asdict(record)
            return None
        except Exception as e:
            logging.error(f"Collection failed for {platform}/{design}: {e}")
            return None


# =============================================================================
# Main Orchestrator
# =============================================================================

class DataCollectionOrchestrator:
    """Main orchestrator for multi-platform, multi-design data collection."""

    def __init__(self, config: CollectionConfig):
        self.config = config
        self.state_file = Path(config.output_dir) / "collection_state.pkl"
        self.results_dir = Path(config.output_dir) / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.state: Optional[CollectionState] = None
        self.remote_executor: Optional[RemoteExecutor] = None
        self.local_collector: Optional[LocalCollector] = None

        # Setup logging
        self.logger = logging.getLogger("DataCollectionOrchestrator")
        self.logger.setLevel(getattr(logging, config.log_level))
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

        # Initialize collectors
        if config.remote_host:
            self.remote_executor = RemoteExecutor(
                config.remote_host, config.remote_user, config.ssh_key_path
            )
        else:
            self.local_collector = LocalCollector(config.orfs_root)

        # Load or initialize state
        self._load_or_initialize_state()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._shutdown_requested = False

    def _signal_handler(self, signum, frame):
        self.logger.info("Shutdown requested, saving state...")
        self._shutdown_requested = True
        self.save_state()
        sys.exit(0)

    def _load_or_initialize_state(self):
        """Load existing state or initialize new."""
        if self.config.resume and self.state_file.exists():
            try:
                with open(self.state_file, 'rb') as f:
                    self.state = pickle.load(f)
                self.logger.info(f"Resumed from checkpoint: {len(self.state.completed)} completed, "
                               f"{len(self.state.pending)} pending")
                return
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}, starting fresh")

        # Initialize new state
        self.state = CollectionState(config=self.config)
        self._initialize_pending()
        self.save_state()

    def _initialize_pending(self):
        """Initialize pending designs list."""
        pending = []
        for platform in self.config.platforms:
            designs = self._get_designs_for_platform(platform)
            for design in designs:
                pending.append((platform, design))
        self.state.pending = pending
        self.state.total_designs = len(pending)
        self.logger.info(f"Initialized {len(pending)} designs across {len(self.config.platforms)} platforms")

    def _get_designs_for_platform(self, platform: str) -> List[str]:
        """Get list of designs for a platform."""
        if self.config.designs and platform in self.config.designs:
            return self.config.designs[platform]
        return PLATFORM_DESIGNS.get(platform, [])

    def save_state(self):
        """Save current state to checkpoint file."""
        self.state.last_checkpoint = datetime.now().isoformat()
        try:
            with open(self.state_file, 'wb') as f:
                pickle.dump(self.state, f)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def run_collection(self) -> Dict[str, Any]:
        """Main collection loop."""
        self.logger.info("Starting data collection...")
        start_time = time.time()

        if self.config.remote_host:
            return self._run_remote_collection()
        else:
            return self._run_local_collection()

    def _run_local_collection(self) -> Dict[str, Any]:
        """Run collection locally with thread pool."""
        self.logger.info(f"Starting local collection with {self.config.workers} workers")

        with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            # Submit initial batch
            future_to_design = {}
            for _ in range(min(self.config.workers, len(self.state.pending))):
                if not self.state.pending:
                    break
                platform, design = self.state.pending.pop(0)
                future = executor.submit(self._collect_single_design, platform, design)
                future_to_design[future] = (platform, design)

            # Process completed futures
            while future_to_design and not self._shutdown_requested:
                done, _ = wait(future_to_design, return_when=FIRST_COMPLETED)

                for future in done:
                    platform, design = future_to_design.pop(future)
                    try:
                        result = future.result(timeout=self.config.timeout)
                        self._handle_result(platform, design, result)
                    except Exception as e:
                        self.logger.error(f"Error collecting {platform}/{design}: {e}")
                        self._handle_error(platform, design, str(e))

                    # Submit next pending design
                    if self.state.pending and not self._shutdown_requested:
                        platform, design = self.state.pending.pop(0)
                        future = executor.submit(self._collect_single_design, platform, design)
                        future_to_design[future] = (platform, design)

                # Checkpoint
                if len(self.state.completed) % self.config.checkpoint_interval == 0:
                    self.save_state()

        # Final save
        self.save_state()

        elapsed = time.time() - self._start_time
        return self._generate_summary(elapsed)

    def _collect_single_design(self, platform: str, design: str) -> DesignResult:
        """Collect data for a single design with retries."""
        start_time = time.time()
        retries = 0

        while retries <= self.config.max_retries:
            try:
                if self.local_collector:
                    record = self.local_collector.collect_design(
                        platform, design, timeout=self.config.timeout
                    )
                    if record:
                        runtime = time.time() - start_time
                        return DesignResult(
                            platform=platform, design=design, success=True,
                            record=record, runtime_sec=time.time() - start_time,
                            retries=retries
                        )

                retries += 1
                if retries <= self.config.max_retries:
                    time.sleep(5 * retries)  # Exponential backoff

            except Exception as e:
                self.logger.error(f"Collection failed for {platform}/{design}: {e}")
                retries += 1
                if retries <= self.config.max_retries:
                    time.sleep(5 * retries)

        return DesignResult(
            platform=platform, design=design, success=False,
            error=f"Failed after {retries} retries", retries=retries,
            runtime_sec=time.time() - start_time
        )

    def _handle_result(self, platform: str, design: str, result: DesignResult):
        """Handle successful collection result."""
        key = f"{platform}/{design}"
        self.state.completed[key] = result
        self.logger.info(f"✅ Completed {key} in {result.runtime_sec:.1f}s")

    def _handle_error(self, platform: str, design: str, error: str):
        """Handle collection error."""
        key = f"{platform}/{design}"
        result = DesignResult(
            platform=platform, design=design, success=False,
            error=error, runtime_sec=0
        )
        self.state.failed[key] = result
        self.logger.error(f"❌ Failed {key}: {error}")

    def _generate_summary(self, elapsed: float) -> Dict[str, Any]:
        """Generate collection summary."""
        return {
            "total_designs": self.state.total_designs,
            "completed": len(self.state.completed),
            "failed": len(self.state.failed),
            "pending": len(self.state.pending),
            "success_rate": len(self.state.completed) / max(1, self.state.total_designs),
            "elapsed_time_sec": elapsed,
            "avg_time_per_design": elapsed / max(1, len(self.state.completed)),
            "platforms": self.config.platforms,
            "output_dir": self.config.output_dir,
        }

    def _run_remote_collection(self) -> Dict[str, Any]:
        """Run collection on remote host."""
        self.logger.info(f"Starting remote collection on {self.config.remote_host}")

        # Create remote collection script
        remote_script = self._generate_remote_script()

        # Upload and execute
        remote_script_path = f"/tmp/orfs_collect_{int(time.time())}.py"
        self.remote_executor.upload_file(
            "/tmp/orfs_collect.py", remote_script_path
        )

        # Execute
        cmd = f"cd {self.config.remote_orfs_root} && python3 {remote_script_path} " \
              f"--platforms {' '.join(self.config.platforms)} " \
              f"--output /tmp/collected_results.json"

        stdout, stderr, exit_code = self.remote_executor.execute(
            cmd, timeout=self.config.timeout * len(self.config.platforms)
        )

        if exit_code != 0:
            raise RuntimeError(f"Remote collection failed: {stderr}")

        # Download results
        local_results = Path(self.config.output_dir) / "remote_results.json"
        self.remote_executor.download_file("/tmp/collected_results.json", str(local_results))

        # Process results
        with open(local_results) as f:
            results = json.load(f)

        # Convert to state format
        for record in results:
            key = f"{record['platform']}/{record['design_name']}"
            self.state.completed[key] = DesignResult(
                platform=record['platform'],
                design=record['design_name'],
                success=True,
                record=record,
                runtime_sec=0
            )

        self.save_state()
        return self._generate_summary(time.time() - self._start_time)

    def _generate_remote_script(self) -> str:
        """Generate remote collection script."""
        script = '''
#!/usr/bin/env python3
import sys
sys.path.insert(0, "{orfs_root}/openroad_gui/intelligence/data")
from collect_real_data import RealDataCollector, main
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--platforms", nargs="+", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

collector = RealDataCollector("{orfs_root}")
all_records = []
for platform in args.platforms:
    records = collector.collect_all(platform)
    all_records.extend([r.__dict__ for r in records])

with open(args.output, "w") as f:
    json.dump(all_records, f, indent=2)
print(f"Collected {{len(all_records)}} records")
'''
        return script.format(
            orfs_root=self.config.remote_orfs_root or self.config.orfs_root
        )


def wait(futures, return_when=FIRST_COMPLETED):
    """Simple wait implementation for futures."""
    from concurrent.futures import FIRST_COMPLETED
    done = set()
    not_done = set()
    for f in futures:
        if f.done():
            done.add(f)
        else:
            not_done.add(f)
    return done, not_done


# =============================================================================
# CLI Interface
# =============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ORFS Data Collection Master Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local collection with 4 workers
  python orfs_data_collection_master.py --orfs-root ~/OpenROAD-flow-scripts \\
      --platforms asap7 sky130hd gf180 --workers 4

  # Remote collection via SSH
  python orfs_data_collection_master.py --remote-host user@server \\
      --remote-orfs-root ~/OpenROAD-flow-scripts --platforms sky130hd

  # Resume interrupted collection
  python orfs_data_collection_master.py --orfs-root ~/OpenROAD-flow-scripts \\
      --platforms asap7 sky130hd --resume

  # Custom designs per platform
  python orfs_data_collection_master.py --orfs-root ~/OpenROAD-flow-scripts \\
      --designs '{"asap7": ["alu4", "adder"], "gf180": ["riscv32i", "jpeg"]}'
        """
    )

    parser.add_argument("--orfs-root", type=str, default=os.environ.get("ORFS_ROOT", "~/OpenROAD-flow-scripts"),
                        help="ORFS root directory")
    parser.add_argument("--platforms", nargs="+", default=DEFAULT_PLATFORMS,
                        help="Platforms to collect")
    parser.add_argument("--designs", type=str, help="JSON dict of platform->designs")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help="Number of parallel workers")
    parser.add_argument("--output", type=str, default="./collected_data",
                        help="Output directory")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Timeout per design (seconds)")
    parser.add_argument("--retry-failed", action="store_true", default=True,
                        help="Retry failed designs")
    parser.add_argument("--max-retries", type=int, default=2,
                        help="Max retries per design")
    parser.add_argument("--remote-host", type=str, help="Remote SSH host")
    parser.add_argument("--remote-user", type=str, help="Remote SSH user")
    parser.add_argument("--remote-orfs-root", type=str, help="Remote ORFS root")
    parser.add_argument("--ssh-key", type=str, help="SSH private key path")
    parser.add_argument("--resume", action="store_true", default=True,
                        help="Resume from checkpoint")
    parser.add_argument("--checkpoint-interval", type=int, default=CHECKPOINT_INTERVAL,
                        help="Checkpoint interval")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    return parser


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    # Parse designs JSON if provided
    designs = None
    if args.designs:
        designs = json.loads(args.designs)

    # Expand paths
    orfs_root = os.path.expanduser(args.orfs_root)

    # Create config
    config = CollectionConfig(
        orfs_root=orfs_root,
        platforms=args.platforms,
        designs=designs,
        output_dir=args.output,
        workers=args.workers,
        timeout=args.timeout,
        retry_failed=args.retry_failed,
        max_retries=args.max_retries,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        remote_orfs_root=args.remote_orfs_root,
        ssh_key_path=args.ssh_key,
        resume=args.resume,
        checkpoint_interval=args.checkpoint_interval,
        log_level=args.log_level,
    )

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create orchestrator and run
    orchestrator = DataCollectionOrchestrator(config)
    summary = orchestrator.run_collection()

    # Print summary
    print("\n" + "="*60)
    print("COLLECTION SUMMARY")
    print("="*60)
    print(f"Total Designs:     {summary['total_designs']}")
    print(f"Completed:         {summary['completed']}")
    print(f"Failed:            {summary['failed']}")
    print(f"Pending:           {summary['pending']}")
    print(f"Success Rate:      {summary['success_rate']:.1%}")
    print(f"Elapsed Time:      {summary['elapsed_time_sec']:.1f}s")
    print(f"Avg Time/Design:   {summary['avg_time_per_design']:.1f}s")
    print(f"Output Directory:  {summary['output_dir']}")

    # Save final summary
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = Path(args.output) / "collection_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")

    # Save all collected records
    all_records = []
    orchestrator = DataCollectionOrchestrator(config)  # Recreate to access state
    orchestrator._load_or_initialize_state()
    for key, result in orchestrator.state.completed.items():
        if result.record:
            all_records.append(result.record)

    records_file = Path(args.output) / "all_collected_records.json"
    with open(records_file, 'w') as f:
        json.dump(all_records, f, indent=2)
    print(f"All records saved to: {records_file}")

    # Generate training data if requested
    if len(all_records) > 0:
        print("\nGenerating training data...")
        prepare_training_data_script = Path(__file__).parent / "openroad_gui" / "intelligence" / "data" / "prepare_real_training_data.py"
        if prepare_training_data_script.exists():
            subprocess.run([
                sys.executable, str(prepare_training_data_script),
                "--input", str(Path(args.output) / "all_collected_records.json"),
                "--output", str(Path(args.output) / "training_data.json")
            ])
            print("Training data generated!")


if __name__ == "__main__":
    main()