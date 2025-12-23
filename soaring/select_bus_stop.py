import json
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def load_region(path: Path):
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    sw = data["south-west"]
    ne = data["north-east"]
    return float(sw["lat"]), float(sw["lon"]), float(ne["lat"]), float(ne["lon"])


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
    if len(sys.argv) < 4:
        print("使用方法: python select_bus_stop.py <region.json> <出力JSON> <出力KML>", file=sys.stderr)
        sys.exit(1)

    region_path = Path(sys.argv[1])
    output_json_path = Path(sys.argv[2])
    output_kml_path = Path(sys.argv[3])

    # 乱数シード設定（再現性）
    random.seed(42)

    # 範囲を読み込み
    sw_lat, sw_lon, ne_lat, ne_lon = load_region(region_path)

    # 緯度・経度の最小値と最大値を取得
    min_lat, max_lat = sw_lat, ne_lat
    min_lon, max_lon = sw_lon, ne_lon

    # ランダムに50地点生成
    stops = []
    for i in range(1, 51):
        lat = random.uniform(min_lat, max_lat)
        lon = random.uniform(min_lon, max_lon)
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
