import json
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
import math

BUS_COUNT = 100

# 地球の半径（メートル）
EARTH_RADIUS = 6371000


def load_region(path: Path):
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    sw = data["south-west"]
    ne = data["north-east"]
    return float(sw["lat"]), float(sw["lon"]), float(ne["lat"]), float(ne["lon"])


def load_meshes(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    meshes = data.get("mesh", [])
    # population > 0 のみ採用
    return [m for m in meshes if m.get("population", 0) > 0]


def load_spots(path: Path) -> List[Dict[str, Any]]:
    """スポット情報を読み込む"""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    spots = []
    for category, items in data.items():
        if isinstance(items, list):
            spots.extend(items)
    return spots


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """2点間の距離をメートル単位で計算（Haversine公式）"""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS * c


def random_point_in_mesh(mesh: Dict[str, Any]) -> (float, float):
    coords = mesh["geometry"]["coordinates"][0]
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    lon = random.uniform(min_lon, max_lon)
    lat = random.uniform(min_lat, max_lat)
    return lat, lon


def random_point_near_spot(
    spot: Dict[str, Any], radius: float = 50.0
) -> (float, float):
    """スポット付近にランダムな点を生成（半径radius以内）"""
    lat = spot["lat"]
    lon = spot["lon"]

    # ランダムな距離と角度を生成
    distance = random.uniform(0, radius)
    angle = random.uniform(0, 2 * math.pi)

    # 距離と角度から緯度経度の差分を計算
    delta_lat = (distance / EARTH_RADIUS) * math.cos(angle) * (180 / math.pi)
    delta_lon = (
        (distance / EARTH_RADIUS)
        * math.sin(angle)
        / math.cos(math.radians(lat))
        * (180 / math.pi)
    )

    return lat + delta_lat, lon + delta_lon


def write_kml(stops, out_path: Path) -> None:
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    for stop in stops:
        pm = ET.SubElement(doc, "Placemark")
        ET.SubElement(pm, "name").text = stop["name"]
        ET.SubElement(pm, "description").text = stop["id"]
        point = ET.SubElement(pm, "Point")
        ET.SubElement(point, "coordinates").text = f'{stop["lon"]},{stop["lat"]},0'
    ET.ElementTree(kml).write(out_path, encoding="utf-8", xml_declaration=True)


def main():
    # コマンドライン引数の確認
    if len(sys.argv) < 6:
        print(
            "使用方法: python select_bus_stop.py <region.json> <mesh.json> <spots.json> <出力JSON> <出力KML>",
            file=sys.stderr,
        )
        sys.exit(1)

    region_path = Path(sys.argv[1])
    mesh_path = Path(sys.argv[2])
    spots_path = Path(sys.argv[3])
    output_json_path = Path(sys.argv[4])
    output_kml_path = Path(sys.argv[5])

    # 乱数シード設定（再現性）
    random.seed(42)

    # 範囲読み込み（必要に応じて利用）
    load_region(region_path)

    # メッシュ読み込み（population > 0 のみ）
    meshes = load_meshes(mesh_path)
    if not meshes:
        print("population > 0 のメッシュが存在しません。", file=sys.stderr)
        sys.exit(1)

    # スポット読み込み
    spots = load_spots(spots_path)
    print(f"📍 {len(spots)}個のスポットを読み込みました")

    # スポット付近にバス停を配置
    stops = []
    stop_id = 1

    for spot in spots:
        lat, lon = random_point_near_spot(spot, radius=50.0)
        stops.append(
            {
                "id": f"comstop{stop_id}",
                "name": f"バス停{stop_id} ({spot['name']}近く)",
                "lat": lat,
                "lon": lon,
            }
        )
        stop_id += 1

    # メッシュ内にランダムに追加のバス停を配置
    used_mesh_indices = set()
    available_meshes = list(range(len(meshes)))

    for i in range(BUS_COUNT):
        # まだ使用されていないメッシュのみを候補とする
        candidate_indices = [
            idx for idx in available_meshes if idx not in used_mesh_indices
        ]

        if not candidate_indices:
            print(
                f"⚠️ {len(stops)}個のバス停を配置しました（メッシュが不足）",
                file=sys.stderr,
            )
            break

        # 候補メッシュから均等に選択（重み付けなし）
        selected_idx = random.choice(candidate_indices)

        mesh = meshes[selected_idx]
        used_mesh_indices.add(selected_idx)

        lat, lon = random_point_in_mesh(mesh)
        stops.append(
            {
                "id": f"comstop{stop_id}",
                "name": f"バス停{stop_id}",
                "lat": lat,
                "lon": lon,
            }
        )
        stop_id += 1

    # JSON出力
    output = {"combus-stops": stops}
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    # KML出力
    write_kml(stops, output_kml_path)

    print(f"✅ 合計{len(stops)}個のバス停を配置")
    print(f"✅ JSON: {output_json_path}")
    print(f"✅ KML : {output_kml_path}")


if __name__ == "__main__":
    main()
