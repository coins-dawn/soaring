import sys
import os
import json
from typing import Tuple

# 格子の分割数
DIV_NUM_VERTICAL = 50  # 縦方向の分割数
DIV_NUM_HORIZONTAL = 50  # 横方向の分割数

# KML用ライブラリの読み込み（なければKML出力をスキップ）
try:
    import simplekml

    _HAS_SIMPLEKML = True
except Exception:
    _HAS_SIMPLEKML = False


def generate_grid_points(
    sw_lon: float, sw_lat: float, ne_lon: float, ne_lat: float
) -> list:
    """格子状の点を生成"""
    points = []

    # 経度・緯度の間隔を計算
    lon_step = (ne_lon - sw_lon) / DIV_NUM_HORIZONTAL
    lat_step = (ne_lat - sw_lat) / DIV_NUM_VERTICAL

    # 格子点を生成
    for i in range(DIV_NUM_VERTICAL + 1):
        lat = sw_lat + (lat_step * i)
        for j in range(DIV_NUM_HORIZONTAL + 1):
            lon = sw_lon + (lon_step * j)
            points.append((lat, lon))

    return points


def write_csv(output_path: str, points: list):
    """CSV (lat,lon) を出力"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("lat,lon\n")
        for lat, lon in points:
            f.write(f"{lat:.6f},{lon:.6f}\n")


def write_kml(output_path: str, points: list):
    """KML を出力（simplekml がインストールされている場合）"""
    if not _HAS_SIMPLEKML:
        print("simplekml がインストールされていないため KML 出力をスキップします")
        return
    kml = simplekml.Kml()
    for idx, (lat, lon) in enumerate(points, 1):
        p = kml.newpoint()
        p.coords = [(lon, lat)]
    kml_path = os.path.splitext(output_path)[0] + ".kml"
    kml.save(kml_path)
    print(f"KML written to: {kml_path}")


def read_target_region(file_path: str):
    with open(file_path, "r") as f:
        return json.load(f)


def main():
    input_target_region_file = sys.argv[1]
    output_path = sys.argv[2]
    output_kml_path = sys.argv[3]

    try:
        # 座標のパース
        target_region_dict = read_target_region(input_target_region_file)
        sw_lon = target_region_dict["south-west"]["lon"]
        sw_lat = target_region_dict["south-west"]["lat"]
        ne_lon = target_region_dict["north-east"]["lon"]
        ne_lat = target_region_dict["north-east"]["lat"]

        # 格子点の生成
        points = generate_grid_points(sw_lon, sw_lat, ne_lon, ne_lat)

        # CSV出力
        write_csv(output_path, points)
        print(f"Generated {len(points)} points")
        print(f"CSV output written to: {output_path}")

        # KML出力（可能なら）
        write_kml(output_kml_path, points)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
