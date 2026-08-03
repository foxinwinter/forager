from __future__ import annotations
import io
import struct
from pathlib import Path

from PIL import Image


def _rva_to_off(data: bytes, sections: list[tuple], rva: int) -> int | None:
    for _name, vaddr, vsize, rptr, rsize in sections:
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return rptr + (rva - vaddr)
    return None


def extract_exe_icons(path: Path) -> list[Image.Image]:
    """Extract the RT_ICON images embedded as resources in a PE executable.

    Resource-directory offsets are relative to the resource root RVA; the
    language-level entry points at an IMAGE_RESOURCE_DATA_ENTRY whose
    OffsetToData is an absolute RVA. Icon blobs are reassembled into a
    single .ico and decoded with Pillow.
    """
    data = path.read_bytes()
    if data[:2] != b"MZ":
        return []
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        return []
    pe = e_lfanew
    num_sections = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    dd = opt + (96 if magic == 0x10B else 112)
    res_rva, _res_size = struct.unpack_from("<II", data, dd + 2 * 8)
    sections = []
    sec = opt + opt_size
    for _ in range(num_sections):
        _name = data[sec:sec + 8].rstrip(b"\0").decode("latin1", "replace")
        vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", data, sec + 8)
        sections.append((_name, vaddr, vsize, rptr, rsize))
        sec += 40

    def read(rva: int, size: int) -> bytes | None:
        off = _rva_to_off(data, sections, rva)
        return None if off is None else data[off:off + size]

    def walk(rel: int) -> dict[int, int] | None:
        off = _rva_to_off(data, sections, res_rva + rel)
        if off is None:
            return None
        n_named, n_id = struct.unpack_from("<HH", data, off + 12)
        out: dict[int, int] = {}
        for i in range(n_named + n_id):
            eid, offset = struct.unpack_from("<II", data, off + 16 + i * 8)
            out[eid] = offset
        return out

    def data_entry(rel: int) -> bytes | None:
        off = _rva_to_off(data, sections, res_rva + rel)
        if off is None:
            return None
        rva, size = struct.unpack_from("<II", data, off)
        return read(rva, size)

    def get_blobs(type_id: int) -> dict[int, bytes]:
        blobs: dict[int, bytes] = {}
        root = walk(0)
        if root is None:
            return blobs
        for tid, off in root.items():
            if tid != type_id:
                continue
            level2 = walk(off & 0x7FFFFFFF)
            if level2 is None:
                continue
            for nid, off2 in level2.items():
                level3 = walk(off2 & 0x7FFFFFFF)
                if level3 is None:
                    continue
                for _lid, off3 in level3.items():
                    blob = data_entry(off3 & 0x7FFFFFFF)
                    if blob:
                        blobs[nid] = blob
        return blobs

    icons = get_blobs(3)
    groups = get_blobs(14)

    out_images: list[Image.Image] = []
    for grp in groups.values():
        count = struct.unpack_from("<H", grp, 4)[0]
        header = struct.pack("<HHH", 0, 1, count)
        dir_bytes = b""
        blobs = b""
        offset = 6 + 16 * count
        for i in range(count):
            w, h, _c, _r, planes, bitcount, bsize, gid = struct.unpack_from(
                "<BBBBHHIH", grp, 6 + i * 14)
            img = icons.get(gid)
            if not img:
                continue
            dir_bytes += struct.pack("<BBBBHHII", w, h, 0, 0, planes, bitcount, len(img), offset)
            blobs += img
            offset += len(img)
        try:
            icon = Image.open(io.BytesIO(header + dir_bytes + blobs))
            icon.load()
            out_images.append(icon)
        except Exception:
            continue
    return out_images


def best_icon(path: Path) -> Image.Image | None:
    """Best RGBA icon for *path*: loose image files as-is, .exe via PE resources."""
    if path.suffix.lower() in (".png", ".ico"):
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            return None
    icons = extract_exe_icons(path)
    if not icons:
        return None
    return max(icons, key=lambda im: im.width * im.height).convert("RGBA")


def find_exe_with_icon(path: Path) -> Path | None:
    """Pick a .exe in *path* likely to carry an application icon."""
    if path.is_file():
        return path if path.suffix.lower() == ".exe" else None
    game_exe = path / "Game.exe"
    if game_exe.is_file():
        return game_exe
    junk = {"unins000.exe", "UnityCrashHandler64.exe", "UnityCrashHandler32.exe"}
    for exe in sorted(path.glob("*.exe")):
        if exe.name not in junk:
            return exe
    return None
