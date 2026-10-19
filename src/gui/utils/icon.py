import base64
import logging
import math
import struct
import tkinter as tk
import zlib
from typing import NamedTuple

logger = logging.getLogger(__name__)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_SIDE = 1024


class IconError(ValueError):
    """The file is not an .ico (or an image inside it) that we know how to read"""


class Entry(NamedTuple):
    width: int
    height: int
    bpp: int
    offset: int
    size: int

    @property
    def side(self) -> int:
        return max(self.width, self.height)


def parse_ico(data: bytes) -> list:
    if len(data) < 6:
        raise IconError("file too short")
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or kind != 1 or count == 0:
        raise IconError("not an .ico file")
    if len(data) < 6 + 16 * count:
        raise IconError("truncated directory")
    entries = []
    for i in range(count):
        width, height, _colors, _reserved, _planes, bpp, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        if size == 0 or offset + size > len(data):
            continue
        entries.append(Entry(width or 256, height or 256, bpp, offset, size))
    if not entries:
        raise IconError("no readable images")
    return entries


def candidates(entries, target: int) -> list:
    bigger = sorted((e for e in entries if e.side >= target), key=lambda e: (e.side, -e.bpp))
    smaller = sorted((e for e in entries if e.side < target), key=lambda e: (-e.side, -e.bpp))
    return bigger + smaller


def _unfilter(raw: bytes, stride: int, height: int, bpp: int) -> bytearray:
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        kind = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if kind == 0:
            pass
        elif kind == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif kind == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif kind == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                predictor = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + predictor) & 255
        else:
            raise IconError(f"bad PNG filter {kind}")
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def decode_png(chunk: bytes):
    if not chunk.startswith(PNG_SIGNATURE):
        raise IconError("not a PNG")
    pos, header, idat = 8, None, []
    while pos + 8 <= len(chunk):
        length, tag = struct.unpack_from(">I4s", chunk, pos)
        body = chunk[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat.append(body)
        elif tag == b"IEND":
            break
    if header is None or not idat:
        raise IconError("PNG without header or data")
    width, height, depth, color_type, compression, filter_method, interlace = header
    if depth != 8 or color_type not in (2, 6) or interlace or compression or filter_method:
        raise IconError(f"unsupported PNG (depth={depth}, type={color_type}, interlace={interlace})")
    if not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE):
        raise IconError("PNG too large for an icon")
    channels = 4 if color_type == 6 else 3
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    if len(raw) != (stride + 1) * height:
        raise IconError("PNG data has the wrong length")
    pixels = _unfilter(raw, stride, height, channels)
    if channels == 4:
        return width, height, bytes(pixels)
    rgba = bytearray(width * height * 4)
    rgba[0::4], rgba[1::4], rgba[2::4] = pixels[0::3], pixels[1::3], pixels[2::3]
    rgba[3::4] = b"\xff" * (width * height)
    return width, height, bytes(rgba)


def decode_dib(chunk: bytes):
    if len(chunk) < 40:
        raise IconError("bitmap header too short")
    header_size, width, height_field, _planes, bpp, compression, *_ = struct.unpack_from("<IiiHHIIiiII", chunk, 0)
    if header_size < 40 or not (0 < width <= MAX_SIDE):
        raise IconError("bad bitmap header")
    if bpp not in (24, 32) or compression not in (0, 3):
        raise IconError(f"unsupported bitmap ({bpp} bpp, compression {compression})")
    top_down = height_field < 0
    full = abs(height_field)
    height = full // 2 if full >= 2 * width else full
    if not (0 < height <= MAX_SIDE):
        raise IconError("bad bitmap height")

    start = header_size + (12 if compression == 3 and header_size == 40 else 0)
    bytes_pp = bpp // 8
    stride = ((width * bpp + 31) // 32) * 4
    xor_end = start + stride * height
    if len(chunk) < xor_end:
        raise IconError("truncated bitmap")

    def source_row(y):
        return y if top_down else height - 1 - y

    rgba = bytearray(width * height * 4)
    for y in range(height):
        row_start = start + source_row(y) * stride
        row = chunk[row_start:row_start + width * bytes_pp]
        out = y * width * 4
        rgba[out:out + width * 4:4] = row[2::bytes_pp]
        rgba[out + 1:out + width * 4:4] = row[1::bytes_pp]
        rgba[out + 2:out + width * 4:4] = row[0::bytes_pp]
        rgba[out + 3:out + width * 4:4] = row[3::4] if bpp == 32 else b"\xff" * width

    no_alpha = bpp == 24 or not any(rgba[3::4])
    if no_alpha:
        mask_stride = ((width + 31) // 32) * 4
        if len(chunk) >= xor_end + mask_stride * height:
            for y in range(height):
                mask_row = xor_end + source_row(y) * mask_stride
                for x in range(width):
                    transparent = (chunk[mask_row + (x >> 3)] >> (7 - (x & 7))) & 1
                    rgba[(y * width + x) * 4 + 3] = 0 if transparent else 255
        else:
            rgba[3::4] = b"\xff" * (width * height)
    return width, height, bytes(rgba)


def decode_entry(data: bytes, entry: Entry):
    chunk = data[entry.offset:entry.offset + entry.size]
    try:
        return decode_png(chunk) if chunk.startswith(PNG_SIGNATURE) else decode_dib(chunk)
    except (struct.error, zlib.error, IndexError) as exc:
        raise IconError(f"damaged image: {exc}") from exc


def _axis_weights(source: int, target: int) -> list:
    scale = source / target
    table = []
    for index in range(target):
        start, end = index * scale, (index + 1) * scale
        pairs = []
        for i in range(int(start), min(math.ceil(end), source)):
            overlap = min(end, i + 1) - max(start, i)
            if overlap > 0:
                pairs.append((i, overlap / scale))
        table.append(pairs)
    return table


def downscale(width: int, height: int, rgba: bytes, side: int):
    ratio = side / max(width, height)
    if ratio >= 1:
        return width, height, rgba
    new_w, new_h = max(1, round(width * ratio)), max(1, round(height * ratio))

    alpha = rgba[3::4]
    channels = [[c * a for c, a in zip(rgba[k::4], alpha)] for k in range(3)]
    channels.append(list(alpha))
    columns, rows = _axis_weights(width, new_w), _axis_weights(height, new_h)

    reduced = []
    for chan in channels:
        horizontal = []
        for y in range(height):
            line = chan[y * width:(y + 1) * width]
            horizontal.extend(sum(line[i] * w for i, w in pairs) for pairs in columns)
        vertical = [0.0] * (new_w * new_h)
        for dy, pairs in enumerate(rows):
            for x in range(new_w):
                vertical[dy * new_w + x] = sum(horizontal[i * new_w + x] * w for i, w in pairs)
        reduced.append(vertical)

    out = bytearray(new_w * new_h * 4)
    red, green, blue, alpha_avg = reduced
    for n in range(new_w * new_h):
        a = alpha_avg[n]
        if a > 0:
            out[n * 4] = min(255, round(red[n] / a))
            out[n * 4 + 1] = min(255, round(green[n] / a))
            out[n * 4 + 2] = min(255, round(blue[n] / a))
        out[n * 4 + 3] = min(255, round(a))
    return new_w, new_h, bytes(out)


def encode_png(width: int, height: int, rgba: bytes) -> bytes:
    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(height))
    return (PNG_SIGNATURE
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6))
            + chunk(b"IEND", b""))


def icon_rgba(data: bytes, side: int):
    problems = []
    for entry in candidates(parse_ico(data), side):
        try:
            return downscale(*decode_entry(data, entry), side)
        except IconError as exc:
            problems.append(f"{entry.side}px: {exc}")
    raise IconError("; ".join(problems))


def load_icon_photo(path: str, side: int = 32, master=None):
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise IconError("file too large")
        width, height, rgba = icon_rgba(data, side)
        png = encode_png(width, height, rgba)
        return tk.PhotoImage(master=master, data=base64.b64encode(png).decode("ascii"))
    except Exception:
        logger.warning("Could not load icon %s", path, exc_info=True)
        return None
