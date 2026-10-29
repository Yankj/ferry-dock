#!/usr/bin/env python3
"""Exercise target/header/linker checks using small synthetic byte fixtures."""

import struct
import unittest

from native_format import inspect_binary


def elf(arch="amd64", segment=1):
    data = bytearray(120)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", data, 16, 2, {"amd64": 62, "arm64": 183}[arch])
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<HH", data, 54, 56, 1)
    struct.pack_into("<I", data, 64, segment)
    return data


def macho(arch="arm64"):
    data = bytearray(64)
    data[:4] = b"\xcf\xfa\xed\xfe"
    struct.pack_into("<IIIII", data, 4, {"amd64": 0x01000007, "arm64": 0x0100000C}[arch], 0, 2, 1, 24)
    struct.pack_into("<IIIIII", data, 32, 0x32, 24, 1, 0x000D0000, 0x000F0000, 0)
    return data


def pe(arch="amd64"):
    data = bytearray(248)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, {"amd64": 0x8664, "arm64": 0xAA64}[arch])
    struct.pack_into("<H", data, 84, 112)
    struct.pack_into("<H", data, 88, 0x20B)
    struct.pack_into("<HH", data, 128, 6, 1)
    struct.pack_into("<HH", data, 136, 6, 1)
    struct.pack_into("<H", data, 156, 3)
    return data


class Headers(unittest.TestCase):
    def test_all_six_targets(self):
        for arch in ("amd64", "arm64"):
            for goos, factory in (("linux", elf), ("darwin", macho), ("windows", pe)):
                with self.subTest(os=goos, arch=arch):
                    self.assertEqual(inspect_binary(factory(arch), goos, arch)["cpu"], arch)

    def test_linux_no_libc_claim_requires_static_program_headers(self):
        for segment in (2, 3):
            with self.assertRaisesRegex(ValueError, "dynamic"):
                inspect_binary(elf(segment=segment), "linux", "amd64")
        self.assertIs(inspect_binary(elf(), "linux", "amd64")["systemLibcRequired"], False)

    def test_foreign_cpu_is_rejected(self):
        for goos, factory in (("linux", elf), ("darwin", macho), ("windows", pe)):
            with self.subTest(os=goos), self.assertRaises(ValueError):
                inspect_binary(factory("amd64"), goos, "arm64")

    def test_metadata_versions_are_header_facts(self):
        self.assertEqual(inspect_binary(macho(), "darwin", "arm64")["minimumOsHeader"], "13.0.0")
        self.assertEqual(inspect_binary(pe(), "windows", "amd64")["osVersionHeader"], "6.1")

    def test_truncated_or_unbounded_tables_rejected(self):
        for goos, factory, offset in (("linux", elf, 32), ("darwin", macho, 20), ("windows", pe, 60)):
            data = factory()
            struct.pack_into("<I", data, offset, 0x7FFFFFFF)
            with self.subTest(os=goos), self.assertRaises(ValueError):
                inspect_binary(data, goos, "amd64" if goos != "darwin" else "arm64")

    def test_windows_console_subsystem_required(self):
        data = pe()
        struct.pack_into("<H", data, 156, 2)
        with self.assertRaisesRegex(ValueError, "console"):
            inspect_binary(data, "windows", "amd64")


if __name__ == "__main__":
    unittest.main()
