"""Read native executable metadata without executing foreign-platform code.

Only the thin, little-endian 64-bit formats produced by this project's Go
packager are accepted. Header facts are build evidence, not native OS/runtime
acceptance or a promise that every OS at an upstream minimum is supported.
"""

import struct


def inspect_binary(data, goos, goarch):
    def require(condition, description):
        if not condition:
            raise ValueError(description)

    require(goarch in ("amd64", "arm64") and len(data) >= 64,
            "unsupported target or truncated executable")
    if goos == "linux":
        require(data[:6] == b"\x7fELF\x02\x01", "Linux executable is not little-endian ELF64")
        kind, machine = struct.unpack_from("<HH", data, 16)
        require(machine == {"amd64": 62, "arm64": 183}[goarch] and kind == 2,
                "ELF target or executable type differs")
        offset = struct.unpack_from("<Q", data, 32)[0]
        size, count = struct.unpack_from("<HH", data, 54)
        require(size >= 56 and 0 < count <= 128 and offset + size * count <= len(data),
                "ELF program header table is invalid")
        kinds = [struct.unpack_from("<I", data, offset + size * index)[0] for index in range(count)]
        require(2 not in kinds and 3 not in kinds,
                "CGO-disabled Linux binary unexpectedly requires a dynamic loader or dynamic segment")
        return {"format": "ELF64", "cpu": goarch, "executableType": "EXEC",
                "interpreter": False, "dynamicSegment": False,
                "systemLibcRequired": False}
    if goos == "darwin":
        require(data[:4] == b"\xcf\xfa\xed\xfe", "Darwin executable is not a thin little-endian Mach-O64")
        cpu, _, kind, count, size = struct.unpack_from("<IIIII", data, 4)
        require(cpu == {"amd64": 0x01000007, "arm64": 0x0100000C}[goarch] and kind == 2,
                "Mach-O target or executable type differs")
        require(count <= 4096 and 32 + size <= len(data), "Mach-O load command table is invalid")
        offset, minimum = 32, None
        for _ in range(count):
            require(offset + 8 <= 32 + size, "Mach-O load command is truncated")
            command, length = struct.unpack_from("<II", data, offset)
            require(length >= 8 and offset + length <= 32 + size, "Mach-O load command length is invalid")
            if command in (0x24, 0x32):
                require(length >= (24 if command == 0x32 else 16), "Mach-O OS version command is truncated")
                version = struct.unpack_from("<I", data, offset + (12 if command == 0x32 else 8))[0]
                minimum = "{}.{}.{}".format(version >> 16, (version >> 8) & 255, version & 255)
            offset += length
        return {"format": "Mach-O64", "cpu": goarch, "executableType": "EXECUTE",
                "minimumOsHeader": minimum}
    require(goos == "windows" and data[:2] == b"MZ", "Windows executable has no DOS/PE header")
    offset = struct.unpack_from("<I", data, 60)[0]
    require(offset <= len(data) - 24 and data[offset:offset + 4] == b"PE\0\0", "PE header is invalid")
    machine = struct.unpack_from("<H", data, offset + 4)[0]
    optional_size = struct.unpack_from("<H", data, offset + 20)[0]
    optional = offset + 24
    require(machine == {"amd64": 0x8664, "arm64": 0xAA64}[goarch]
            and optional_size >= 112 and optional + optional_size <= len(data)
            and struct.unpack_from("<H", data, optional)[0] == 0x20B,
            "PE target or PE32+ optional header differs")
    major, minor = struct.unpack_from("<HH", data, optional + 40)
    subsystem_major, subsystem_minor = struct.unpack_from("<HH", data, optional + 48)
    require(struct.unpack_from("<H", data, optional + 68)[0] == 3,
            "Windows CLI executable does not declare the console subsystem")
    return {"format": "PE32+", "cpu": goarch, "subsystem": "WINDOWS_CUI",
            "osVersionHeader": "{}.{}".format(major, minor),
            "subsystemVersionHeader": "{}.{}".format(subsystem_major, subsystem_minor)}
