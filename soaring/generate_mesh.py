import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET


def mesh250m_to_polygon(mesh_code: str) -> Tuple[float, float, float, float, List[List[float]]]:
    """
    10桁の第5次メッシュコード（250mメッシュ）から
    南西端緯度・経度、幅・高さ、およびポリゴン座標を返す。
    """
    if len(mesh_code) != 10 or not mesh_code.isdigit():
        raise ValueError("mesh_code must be a 10-digit numeric string")

    # 1次〜3次メッシュの抽出
    p = int(mesh_code[0:2])    # 緯度 40分単位
    q = int(mesh_code[2:4])    # 経度 1度単位
    r = int(mesh_code[4:5])    # 2次メッシュ緯度 5分単位
    s = int(mesh_code[5:6])    # 2次メッシュ経度 7.5分単位
    t = int(mesh_code[6:7])    # 3次メッシュ緯度 30秒単位
    u = int(mesh_code[7:8])    # 3次メッシュ経度 45秒単位

    # 4次メッシュ (9桁目) と 5次メッシュ (10桁目)
    m4 = int(mesh_code[8])
    m5 = int(mesh_code[9])

    if not (1 <= m4 <= 4 and 1 <= m5 <= 4):
        raise ValueError("4th and 5th mesh digits must be in 1..4")

    # 3次メッシュ（1km）までの南西端を計算
    lat_sw = p * (2/3) + r * (1/12) + t * (1/120)
    lon_sw = (q + 100) + s * (1/8) + u * (1/80)

    # 4次メッシュ(500m)のオフセット計算
    # 1: 南西, 2: 南東, 3: 北西, 4: 北東
    lat_offset_4 = (1/240) if m4 > 2 else 0
    lon_offset_4 = (1/160) if m4 % 2 == 0 else 0

    # 5次メッシュ(250m)のオフセット計算
    lat_offset_5 = (1/480) if m5 > 2 else 0
    lon_offset_5 = (1/320) if m5 % 2 == 0 else 0

    # 最終的な南西端
    sw_lat = lat_sw + lat_offset_4 + lat_offset_5
    sw_lon = lon_sw + lon_offset_4 + lon_offset_5

    # 5次メッシュのサイズ (緯度7.5秒, 経度11.25秒)
    height = 7.5 / 3600
    width = 11.25 / 3600

    polygon = [
        [sw_lon, sw_lat],
        [sw_lon + width, sw_lat],
        [sw_lon + width, sw_lat + height],
        [sw_lon, sw_lat + height],
        [sw_lon, sw_lat],
    ]
    
    return sw_lat, sw_lon, height, width, polygon


def load_region(path: Path) -> Dict[str, float]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    sw = data["south-west"]
    ne = data["north-east"]
    return {
        "sw_lat": float(sw["lat"]),
        "sw_lon": float(sw["lon"]),
        "ne_lat": float(ne["lat"]),
        "ne_lon": float(ne["lon"]),
    }


def row_to_population(row: List[str]) -> int:
    val = row[4].strip()
    if val.isdigit():
        return int(val)
    return 0


def write_kml(meshes: List[Dict], out_path: Path) -> None:
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    for m in meshes:
        pm = ET.SubElement(doc, "Placemark")
        ET.SubElement(pm, "name").text = m["mesh_code"]
        ET.SubElement(pm, "description").text = f"population: {m['population']}"
        polygon = ET.SubElement(pm, "Polygon")
        ET.SubElement(polygon, "tessellate").text = "1"
        outer = ET.SubElement(polygon, "outerBoundaryIs")
        lr = ET.SubElement(outer, "LinearRing")
        coords = ET.SubElement(lr, "coordinates")
        # KMLは "lon,lat,0" の順で、最終点をクローズする
        ring = m["geometry"]["coordinates"][0]
        if ring[0] != ring[-1]:
            ring = ring + [ring[0]]
        coord_lines = [f"{lon},{lat},0" for lon, lat in ring]
        coords.text = " ".join(coord_lines)
    tree = ET.ElementTree(kml)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    if len(sys.argv) != 5:
        print("Usage: python generate_mesh.py <region.json> <input.csv> <output.json> <output.kml>", file=sys.stderr)
        sys.exit(1)

    region_path = Path(sys.argv[1])
    csv_path = Path(sys.argv[2])
    out_json_path = Path(sys.argv[3])
    out_kml_path = Path(sys.argv[4])

    region = load_region(region_path)

    meshes = []
    with csv_path.open(encoding="shift_jis", newline="") as f:
        reader = csv.reader(f)
        # skip first two header lines
        next(reader, None)
        next(reader, None)

        for row in reader:
            if len(row) < 5:
                continue
            mesh_code = row[0].strip()
            population = row_to_population(row)
            if population <= 0:
                continue
            try:
                sw_lat, sw_lon, h, w, polygon = mesh250m_to_polygon(mesh_code)
            except ValueError:
                continue

            min_lat, max_lat = sw_lat, sw_lat + h
            min_lon, max_lon = sw_lon, sw_lon + w
            if (
                min_lat >= region["sw_lat"]
                and max_lat <= region["ne_lat"]
                and min_lon >= region["sw_lon"]
                and max_lon <= region["ne_lon"]
            ):
                meshes.append(
                    {
                        "mesh_code": mesh_code,
                        "population": population,
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [polygon],
                        },
                    }
                )

    out = {"mesh": meshes}
    with out_json_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    write_kml(meshes, out_kml_path)


if __name__ == "__main__":
    main()