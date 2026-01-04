#!/usr/bin/env python3

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def load_csv(path: Path) -> Iterable[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def format_time(value: str) -> str:
    if not value:
        return ""
    # Keep hours beyond 24 as-is and trim seconds.
    parts = value.split(":")
    if len(parts) >= 2:
        return f"{parts[0]}:{parts[1]}"
    return value


def encode_polyline(coords: Sequence[Tuple[float, float]]) -> str:
    # Google polyline encoder (lat, lon order expected by the format).
    def encode_value(value: int) -> str:
        value = ~(value << 1) if value < 0 else value << 1
        chunks = []
        while value >= 0x20:
            chunks.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        chunks.append(chr(value + 63))
        return "".join(chunks)

    output: List[str] = []
    prev_lat = 0
    prev_lon = 0
    for lat, lon in coords:
        lat_i = int(round(lat * 1e5))
        lon_i = int(round(lon * 1e5))
        output.append(encode_value(lat_i - prev_lat))
        output.append(encode_value(lon_i - prev_lon))
        prev_lat, prev_lon = lat_i, lon_i
    return "".join(output)


def decode_polyline(poly: str) -> List[Tuple[float, float]]:
    coords: List[Tuple[float, float]] = []
    index = 0
    lat = 0
    lon = 0
    length = len(poly)

    while index < length:
        shift = 0
        result = 0
        while True:
            b = ord(poly[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        delta_lat = ~(result >> 1) if result & 1 else result >> 1
        lat += delta_lat

        shift = 0
        result = 0
        while True:
            b = ord(poly[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        delta_lon = ~(result >> 1) if result & 1 else result >> 1
        lon += delta_lon

        coords.append((lat / 1e5, lon / 1e5))
    return coords


def build_stops(stops_path: Path) -> Dict[str, dict]:
    stops: Dict[str, dict] = {}
    for row in load_csv(stops_path):
        stop_id = row.get("stop_id", "")
        if not stop_id:
            continue
        stops[stop_id] = {
            "id": stop_id,
            "name": row.get("stop_name", ""),
            "lat": float(row.get("stop_lat", 0) or 0),
            "lon": float(row.get("stop_lon", 0) or 0),
        }
    return stops


def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: visualize_gtfs.py <gtfs_dir> <output.json> <output.kml>")
        sys.exit(1)

    gtfs_dir = Path(sys.argv[1])
    json_path = Path(sys.argv[2])
    kml_path = Path(sys.argv[3])

    stops = build_stops(gtfs_dir / "stops.txt")

    trips_route: Dict[str, str] = {}
    route_trips: Dict[str, List[str]] = defaultdict(list)
    for row in load_csv(gtfs_dir / "trips.txt"):
        trip_id = row.get("trip_id", "")
        route_id = row.get("route_id", "")
        if not trip_id or not route_id:
            continue
        trips_route[trip_id] = route_id
        route_trips[route_id].append(trip_id)

    stop_times_by_trip: Dict[str, List[dict]] = defaultdict(list)
    stop_times_by_stop: Dict[str, List[str]] = defaultdict(list)
    route_stop_times: Dict[str, Dict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for row in load_csv(gtfs_dir / "stop_times.txt"):
        trip_id = row.get("trip_id", "")
        stop_id = row.get("stop_id", "")
        if not trip_id or not stop_id:
            continue
        arr = format_time(row.get("arrival_time", ""))
        dep = format_time(row.get("departure_time", ""))
        time_val = arr or dep
        try:
            seq = int(row.get("stop_sequence", "0"))
        except ValueError:
            seq = 0
        entry = {
            "trip_id": trip_id,
            "stop_id": stop_id,
            "time": time_val,
            "sequence": seq,
        }
        stop_times_by_trip[trip_id].append(entry)
        if time_val:
            stop_times_by_stop[stop_id].append(time_val)
            route_id = trips_route.get(trip_id)
            if route_id:
                route_stop_times[route_id][stop_id].append(time_val)

    for trip_entries in stop_times_by_trip.values():
        trip_entries.sort(key=lambda x: x["sequence"])

    routes_meta: Dict[str, dict] = {}
    for row in load_csv(gtfs_dir / "routes.txt"):
        route_id = row.get("route_id", "")
        if not route_id:
            continue
        name = row.get("route_long_name") or row.get("route_short_name") or route_id
        routes_meta[route_id] = {"id": route_id, "name": name}

    # Build global geometry by concatenating all trip paths with simple dedupe of consecutive points.
    all_coords: List[Tuple[float, float]] = []
    for trip_id, entries in stop_times_by_trip.items():
        coords = []
        for e in entries:
            stop = stops.get(e["stop_id"])
            if stop:
                coords.append((stop["lat"], stop["lon"]))
        if not coords:
            continue
        for lat, lon in coords:
            if all_coords and all_coords[-1] == (lat, lon):
                continue
            all_coords.append((lat, lon))

    global_geometry = encode_polyline(all_coords) if all_coords else ""

    stops_payload = []
    for stop_id, stop in stops.items():
        times = sorted(set(stop_times_by_stop.get(stop_id, [])))
        stops_payload.append(
            {
                "id": stop_id,
                "name": stop["name"],
                "lat": stop["lat"],
                "lon": stop["lon"],
                "times": times,
            }
        )
    stops_payload.sort(key=lambda x: x["id"])

    routes_payload = []
    for route_id, meta in routes_meta.items():
        trip_ids = sorted(route_trips.get(route_id, []))
        if not trip_ids:
            continue
        rep_trip = trip_ids[0]
        entries = stop_times_by_trip.get(rep_trip, [])
        route_coords = []
        route_stops = []
        for e in entries:
            stop = stops.get(e["stop_id"])
            if not stop:
                continue
            route_coords.append((stop["lat"], stop["lon"]))
            times = sorted(set(route_stop_times[route_id].get(e["stop_id"], [])))
            route_stops.append(
                {
                    "id": stop["id"],
                    "name": stop["name"],
                    "lat": stop["lat"],
                    "lon": stop["lon"],
                    "times": times,
                }
            )
        routes_payload.append(
            {
                "name": meta["name"],
                "geometry": encode_polyline(route_coords) if route_coords else "",
                "stops": route_stops,
            }
        )

    output = {
        "geometry": global_geometry,
        "stops": stops_payload,
        "routes": routes_payload,
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    def xml_escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    decoded_coords = decode_polyline(global_geometry) if global_geometry else []
    coords_str = " ".join([f"{lon},{lat},0" for lat, lon in decoded_coords])

    kml_parts: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        "    <name>GTFS Visualization</name>",
    ]

    if coords_str:
        kml_parts.extend(
            [
                "    <Placemark>",
                "      <name>Network</name>",
                "      <Style>",
                "        <LineStyle><color>ff0000ff</color><width>3</width></LineStyle>",
                "      </Style>",
                "      <LineString>",
                "        <tessellate>1</tessellate>",
                f"        <coordinates>{coords_str}</coordinates>",
                "      </LineString>",
                "    </Placemark>",
            ]
        )

    for stop in stops_payload:
        desc_times = ", ".join(stop["times"])
        description = xml_escape(desc_times)
        name = xml_escape(f"{stop['name']} ({stop['id']})")
        kml_parts.extend(
            [
                "    <Placemark>",
                f"      <name>{name}</name>",
                f"      <description>{description}</description>",
                "      <Point>",
                f"        <coordinates>{stop['lon']},{stop['lat']},0</coordinates>",
                "      </Point>",
                "    </Placemark>",
            ]
        )

    kml_parts.extend(["  </Document>", "</kml>"])

    kml_path.parent.mkdir(parents=True, exist_ok=True)
    with kml_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(kml_parts))


if __name__ == "__main__":
    main()
