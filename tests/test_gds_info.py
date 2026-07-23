"""Tests for GDSII parser (gds_info.py)."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest

from openroad_gui.gds_info import GdsInfo, parse_gds, _decode_ascii


class TestDecodeAscii:
    """Tests for the _decode_ascii helper."""

    def test_simple_ascii(self) -> None:
        assert _decode_ascii(b"hello") == "hello"

    def test_null_terminated(self) -> None:
        assert _decode_ascii(b"hello\x00\x00") == "hello"

    def test_empty_bytes(self) -> None:
        assert _decode_ascii(b"") == ""

    def test_invalid_utf8_replacement(self) -> None:
        # Non-ASCII bytes should be replaced
        result = _decode_ascii(b"hello\xff\xfe")
        assert "hello" in result


class TestGdsInfo:
    """Tests for GdsInfo dataclass."""

    def test_summary_no_data(self) -> None:
        info = GdsInfo(path=Path("test.gds"), file_size=0)
        summary = info.summary
        assert "GDSII File: test.gds" in summary
        assert "Size: 0 B" in summary

    def test_summary_with_data(self) -> None:
        info = GdsInfo(
            path=Path("test.gds"),
            file_size=1024,
            library_name="mylib",
            structures=["TOP", "CELL1", "CELL2"],
            units="user=1e-06, dbu=1e-09 m",
        )
        summary = info.summary
        assert "GDSII File: test.gds" in summary
        assert "Size: 1.0 KB" in summary
        assert "Library: mylib" in summary
        assert "Units: user=1e-06, dbu=1e-09 m" in summary
        assert "Structures (3):" in summary
        assert "  • TOP" in summary
        assert "  • CELL1" in summary
        assert "  • CELL2" in summary

    def test_summary_many_structures_truncates(self) -> None:
        structures = [f"CELL{i}" for i in range(25)]
        info = GdsInfo(
            path=Path("test.gds"),
            file_size=100,
            structures=structures,
        )
        summary = info.summary
        assert "Structures (25):" in summary
        assert "  • CELL19" in summary
        assert "and 5 more" in summary

    def test_summary_with_error(self) -> None:
        info = GdsInfo(
            path=Path("test.gds"),
            file_size=100,
            error="Truncated at 100 structures",
        )
        summary = info.summary
        assert "Parse note: Truncated at 100 structures" in summary

    def test_format_size(self) -> None:
        assert GdsInfo._format_size(0) == "0 B"
        assert GdsInfo._format_size(512) == "512 B"
        assert GdsInfo._format_size(1024) == "1.0 KB"
        assert GdsInfo._format_size(1536) == "1.5 KB"
        assert GdsInfo._format_size(1024 * 1024) == "1.0 MB"
        assert GdsInfo._format_size(1024 * 1024 * 1024) == "1.0 GB"


class TestParseGds:
    """Tests for parse_gds function."""

    def _write_gds(self, path: Path, records: list[tuple[int, int, bytes]]) -> None:
        """Helper to write a synthetic GDSII file."""
        with path.open("wb") as f:
            for rec_type, data_type, data in records:
                length = 4 + len(data)
                f.write(struct.pack(">HBB", length, rec_type, data_type))
                f.write(data)

    def test_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
        try:
            info = parse_gds(path)
            assert info.path == path
            assert info.file_size == 0
            # Empty file exists but has no content, error may vary
            assert info.error in ("", "File not found")
        finally:
            path.unlink(missing_ok=True)

    def test_nonexistent_file(self) -> None:
        info = parse_gds(Path("/nonexistent/path.gds"))
        assert info.error == "File not found"
        assert info.file_size == 0

    def test_minimal_valid_gds(self) -> None:
        # HEADER (record 0x00, not parsed but consumed)
        # LIBNAME (0x02, type 0x06)
        libname = b"mylib\x00"
        # UNITS (0x03, type 0x05) - 2 doubles
        units = struct.pack(">2d", 1e-6, 1e-9)
        # ENDLIB (0x04)
        records = [
            (0x00, 0x00, b"\x00\x02"),  # HEADER (dummy)
            (0x02, 0x06, libname),      # LIBNAME
            (0x03, 0x05, units),        # UNITS
            (0x04, 0x00, b""),          # ENDLIB
        ]
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
        try:
            self._write_gds(path, records)
            info = parse_gds(path)
            assert info.library_name == "mylib"
            assert "user=1e-06, dbu=1e-09 m" in info.units
            assert info.structures == []
        finally:
            path.unlink(missing_ok=True)

    def test_gds_with_structures(self) -> None:
        libname = b"mylib\x00"
        units = struct.pack(">2d", 1e-6, 1e-9)
        strname1 = b"TOP\x00"
        strname2 = b"CELL1\x00"
        records = [
            (0x00, 0x00, b"\x00\x02"),
            (0x02, 0x06, libname),
            (0x03, 0x05, units),
            (0x06, 0x06, strname1),  # STRNAME
            (0x06, 0x06, strname2),  # STRNAME
            (0x04, 0x00, b""),
        ]
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
        try:
            self._write_gds(path, records)
            info = parse_gds(path)
            assert info.library_name == "mylib"
            assert info.structures == ["TOP", "CELL1"]
        finally:
            path.unlink(missing_ok=True)

    def test_structure_limit_truncation(self) -> None:
        libname = b"mylib\x00"
        units = struct.pack(">2d", 1e-6, 1e-9)
        records = [(0x00, 0x00, b"\x00\x02"), (0x02, 0x06, libname), (0x03, 0x05, units)]
        for i in range(105):
            records.append((0x06, 0x06, f"CELL{i:03d}\x00".encode()))
        records.append((0x04, 0x00, b""))
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
        try:
            self._write_gds(path, records)
            info = parse_gds(path, max_structures=100)
            assert len(info.structures) == 100
            assert "Truncated at 100 structures" in info.error
        finally:
            path.unlink(missing_ok=True)

    def test_malformed_record_length(self) -> None:
        # Record with length < 4
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
            f.write(struct.pack(">HBB", 3, 0x02, 0x06))  # length=3 (invalid)
        try:
            info = parse_gds(path)
            assert info.file_size > 0
        finally:
            path.unlink(missing_ok=True)

    def test_truncated_file(self) -> None:
        libname = b"mylib\x00"
        # Write partial record
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
            f.write(struct.pack(">HBB", 10, 0x02, 0x06))
            f.write(b"mylib")  # Only 5 bytes, need 6
        try:
            info = parse_gds(path)
            # Should handle gracefully
            assert info.path == path
        finally:
            path.unlink(missing_ok=True)

    def test_default_max_structures(self) -> None:
        """Test default max_structures=100 limit."""
        libname = b"mylib\x00"
        units = struct.pack(">2d", 1e-6, 1e-9)
        records = [(0x00, 0x00, b"\x00\x02"), (0x02, 0x06, libname), (0x03, 0x05, units)]
        for i in range(101):
            records.append((0x06, 0x06, f"CELL{i:03d}\x00".encode()))
        records.append((0x04, 0x00, b""))
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
        try:
            self._write_gds(path, records)
            info = parse_gds(path)  # default max=100
            assert len(info.structures) == 100
            assert "Truncated at 100 structures" in info.error
        finally:
            path.unlink(missing_ok=True)


class TestGdsInfoEdgeCases:
    """Additional edge case tests."""

    def test_parse_gds_with_non_ascii_in_strings(self) -> None:
        libname = b"mylib\xff\x00"
        units = struct.pack(">2d", 1e-6, 1e-9)
        records = [
            (0x00, 0x00, b"\x00\x02"),
            (0x02, 0x06, libname),
            (0x03, 0x05, units),
            (0x04, 0x00, b""),
        ]
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = Path(f.name)
        try:
            self._write_gds(path, records)
            info = parse_gds(path)
            assert "mylib" in info.library_name
        finally:
            path.unlink(missing_ok=True)

    def _write_gds(self, path: Path, records: list[tuple[int, int, bytes]]) -> None:
        with path.open("wb") as f:
            for rec_type, data_type, data in records:
                length = 4 + len(data)
                f.write(struct.pack(">HBB", length, rec_type, data_type))
                f.write(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])