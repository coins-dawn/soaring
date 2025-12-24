import json
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

BUS_COUNT = 100


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


def random_point_in_mesh(mesh: Dict[str, Any]) -> (float, float):
    coords = mesh["geometry"]["coordinates"][0]
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    lon = random.uniform(min_lon, max_lon)
    lat = random.uniform(min_lat, max_lat)
    return lat, lon


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
    if len(sys.argv) < 5:
        print("使用方法: python select_bus_stop.py <region.json> <mesh.json> <出力JSON> <出力KML>", file=sys.stderr)
        sys.exit(1)

    region_path = Path(sys.argv[1])
    mesh_path = Path(sys.argv[2])
    output_json_path = Path(sys.argv[3])
    output_kml_path = Path(sys.argv[4])

    # 乱数シード設定（再現性）
    random.seed(42)

    # 範囲読み込み（必要に応じて利用）
    load_region(region_path)

    # メッシュ読み込み（population > 0 のみ）
    meshes = load_meshes(mesh_path)
    if not meshes:
        print("population > 0 のメッシュが存在しません。", file=sys.stderr)
        sys.exit(1)

    weights = [m["population"] for m in meshes]
    total = sum(weights)
    if total <= 0:
        print("population 合計が 0 です。", file=sys.stderr)
        sys.exit(1)

    # 重みに比例してメッシュを選び、その内部にバス停を配置
    # 一つのメッシュには最大一つのバス停を配置
    stops = []
    used_mesh_indices = set()
    available_meshes = list(range(len(meshes)))
    
    for i in range(1, BUS_COUNT+1):
        # まだ使用されていないメッシュのみを候補とする
        candidate_indices = [idx for idx in available_meshes if idx not in used_mesh_indices]
        
        if not candidate_indices:
            print(f"⚠️ {i-1}個のバス停を配置しました（メッシュが不足）", file=sys.stderr)
            break
        
        # 候補メッシュから重みに応じて選択
        candidate_weights = [weights[idx] for idx in candidate_indices]
        selected_idx = random.choices(candidate_indices, weights=candidate_weights, k=1)[0]
        
        mesh = meshes[selected_idx]
        used_mesh_indices.add(selected_idx)
        
        lat, lon = random_point_in_mesh(mesh)
        stops.append(
            {"id": f"comstop{i}", "name": f"バス停{i}", "lat": lat, "lon": lon}
        )

    # JSON出力
    output = {"combus-stops": stops}
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    # KML出力
    write_kml(stops, output_kml_path)

    print(f"✅ JSON: {output_json_path}")
    print(f"✅ KML : {output_kml_path}")


if __name__ == "__main__":
    main()
