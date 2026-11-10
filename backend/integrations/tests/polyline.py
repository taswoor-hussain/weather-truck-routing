"""Test helper: encode coordinates as a Google polyline (inverse of core.geo.decode_polyline)."""


def encode_polyline(coords: list[tuple[float, float]], precision: int = 6) -> str:
    factor = 10**precision
    out: list[str] = []
    prev_lat = prev_lon = 0
    for lat, lon in coords:
        ilat, ilon = round(lat * factor), round(lon * factor)
        for delta in (ilat - prev_lat, ilon - prev_lon):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                out.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            out.append(chr(value + 63))
        prev_lat, prev_lon = ilat, ilon
    return "".join(out)
