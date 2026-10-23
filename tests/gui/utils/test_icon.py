import struct

import pytest

from core.storage.paths import resource_path
from gui.utils import icon
from gui.utils.icon import IconError


def solid(width, height, rgba):
    return bytes(rgba) * (width * height)


def make_ico(images):
    directory, blobs = b"", b""
    offset = 6 + 16 * len(images)
    for width, height, bpp, payload in images:
        directory += struct.pack("<BBBBHHII", width % 256, height % 256, 0, 0, 1, bpp, len(payload), offset + len(blobs))
        blobs += payload
    return struct.pack("<HHH", 0, 1, len(images)) + directory + blobs


def png(width, height, rgba=(10, 20, 30, 255)):
    return icon.encode_png(width, height, solid(width, height, rgba))


def test_png_round_trip():
    pixels = bytes(range(4 * 3 * 2))
    assert icon.decode_png(icon.encode_png(3, 2, pixels)) == (3, 2, pixels)


def test_decode_png_rejects_other_data():
    with pytest.raises(IconError):
        icon.decode_png(b"GIF89a")


def test_decode_png_rejects_unsupported_bit_depths():
    data = bytearray(png(1, 1))
    data[8 + 8 + 8] = 16
    with pytest.raises(IconError):
        icon.decode_png(bytes(data))


@pytest.mark.parametrize("data", [b"", b"\x00\x00\x01\x00", struct.pack("<HHH", 0, 2, 1), struct.pack("<HHH", 0, 1, 0)])
def test_parse_ico_rejects_files_that_are_not_icons(data):
    with pytest.raises(IconError):
        icon.parse_ico(data)


def test_parse_ico_rejects_a_truncated_directory():
    with pytest.raises(IconError):
        icon.parse_ico(struct.pack("<HHH", 0, 1, 3) + b"\x00" * 16)


def test_parse_ico_skips_entries_that_point_outside_the_file():
    data = make_ico([(16, 16, 32, png(16, 16))])
    broken = data[:6 + 12] + struct.pack("<I", 10_000) + data[6 + 16:]
    with pytest.raises(IconError):
        icon.parse_ico(broken)


def test_parse_ico_reads_256_from_a_zero_size():
    entries = icon.parse_ico(make_ico([(256, 256, 32, png(2, 2))]))
    assert (entries[0].width, entries[0].height) == (256, 256)


def test_candidates_prefer_the_smallest_image_that_is_big_enough():
    entries = icon.parse_ico(make_ico([(16, 16, 32, png(16, 16)), (48, 48, 32, png(48, 48)), (32, 32, 32, png(32, 32))]))
    assert [e.side for e in icon.candidates(entries, 32)] == [32, 48, 16]


def test_candidates_fall_back_to_the_largest_smaller_image():
    entries = icon.parse_ico(make_ico([(16, 16, 32, png(16, 16)), (24, 24, 32, png(24, 24))]))
    assert [e.side for e in icon.candidates(entries, 64)] == [24, 16]


def test_downscale_never_enlarges():
    pixels = solid(4, 4, (1, 2, 3, 255))
    assert icon.downscale(4, 4, pixels, 8) == (4, 4, pixels)


def test_downscale_keeps_a_solid_colour():
    assert icon.downscale(4, 4, solid(4, 4, (200, 100, 50, 255)), 2) == (2, 2, solid(2, 2, (200, 100, 50, 255)))


def test_downscale_does_not_bleed_colour_from_transparent_pixels():
    pixels = bytes((255, 0, 0, 255, 0, 255, 0, 0))
    assert icon.downscale(2, 1, pixels, 1) == (1, 1, bytes((255, 0, 0, 128)))


def test_decode_dib_reads_a_bottom_up_32_bit_bitmap():
    header = struct.pack("<IiiHHIIiiII", 40, 1, 2, 1, 32, 0, 0, 0, 0, 0, 0)
    chunk = header + bytes((0x10, 0x20, 0x30, 0xFF)) + b"\x00" * 4
    assert icon.decode_dib(chunk) == (1, 1, bytes((0x30, 0x20, 0x10, 0xFF)))


def test_decode_entry_reports_damaged_images_as_icon_errors():
    payload = png(4, 4)[:30]
    data = make_ico([(4, 4, 32, payload)])
    entry = icon.parse_ico(data)[0]
    with pytest.raises(IconError):
        icon.decode_entry(data, entry)


def test_icon_rgba_falls_back_to_the_next_readable_image():
    data = make_ico([(32, 32, 32, b"\x89PNG\r\n\x1a\nbroken"), (16, 16, 32, png(16, 16))])
    width, height, rgba = icon.icon_rgba(data, 32)
    assert (width, height) == (16, 16)
    assert len(rgba) == 16 * 16 * 4


def test_the_app_icon_can_be_decoded():
    with open(resource_path("assets", "icon.ico"), "rb") as f:
        width, height, rgba = icon.icon_rgba(f.read(), 32)
    assert 0 < width <= 32 and 0 < height <= 32
    assert len(rgba) == width * height * 4
