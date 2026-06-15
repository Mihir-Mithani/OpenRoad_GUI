"""Minimal GDSII file metadata parser (stdlib only)."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# GDSII record type (high byte when packed as >HH)
RT_LIBNAME = 0x02
RT_UNITS = 0x03
RT_STRNAME = 0x06


@dataclass
class GdsInfo:
    path: Path
    file_size: int
    library_name: str = ""
    structures: list[str] = field(default_factory=list)
    units: str = ""
    error: str = ""

    @property
    def summary(self) -> str:
        lines = [
            f"GDSII File: {self.path.name}",
            f"Path: {self.path}",
            f"Size: {self._format_size(self.file_size)}",
        ]
        if self.library_name:
            lines.append(f"Library: {self.library_name}")
        if self.units:
            lines.append(f"Units: {self.units}")
        if self.structures:
            lines.append(f"Structures ({len(self.structures)}):")
            for name in self.structures[:20]:
                lines.append(f"  • {name}")
            if len(self.structures) > 20:
                lines.append(f"  … and {len(self.structures) - 20} more")
        if self.error:
            lines.append(f"Parse note: {self.error}")
        return "\n".join(lines)

    @staticmethod
    def _format_size(num: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if num < 1024:
                return f"{num:.1f} {unit}" if unit != "B" else f"{num} B"
            num /= 1024
        return f"{num:.1f} TB"


def parse_gds(path: Path, max_structures: int = 100) -> GdsInfo:
    info = GdsInfo(path=path, file_size=path.stat().st_size if path.exists() else 0)
    if not path.is_file():
        info.error = "File not found"
        return info

    try:
        with path.open("rb") as fh:
            while True:
                header = fh.read(4)
                if len(header) < 4:
                    break
                length, record_byte, data_type = struct.unpack(">HBB", header)
                if length < 4:
                    break
                data_len = length - 4
                data = fh.read(data_len)
                if len(data) < data_len:
                    break

                if record_byte == RT_LIBNAME and data_type == 0x06:
                    info.library_name = _decode_ascii(data)
                elif record_byte == RT_UNITS and data_type == 0x05 and len(data) == 16:
                    user, dbu = struct.unpack(">2d", data)
                    info.units = f"user={user:g}, dbu={dbu:g} m"
                elif record_byte == RT_STRNAME and data_type == 0x06:
                    name = _decode_ascii(data)
                    if name and name not in info.structures:
                        info.structures.append(name)
                        if len(info.structures) >= max_structures:
                            info.error = f"Truncated at {max_structures} structures"
                            break
    except OSError as exc:
        info.error = str(exc)

    return info


def _decode_ascii(data: bytes) -> str:
    return data.rstrip(b"\x00").decode("ascii", errors="replace")
