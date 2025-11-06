import sys
import json
from shapely.geometry import Polygon, box


def is_mesh_in_region(mesh_coords: list, region_box: Polygon) -> bool:
    """メッシュが指定された領域に完全に含まれているかチェック"""
    mesh_polygon = Polygon(mesh_coords[0])  # coordinatesは二重リストなので[0]を使用
    return region_box.contains(mesh_polygon)


def main(
    input_population_mesh_file: str,
    input_target_region_file: str,
    output_mesh_file: str,
):
    # population meshの読み込み
    with open(input_population_mesh_file, "r", encoding="utf-8") as f:
        population_mesh = json.load(f)

    # target regionの読み込み
    with open(input_target_region_file, "r", encoding="utf-8") as f:
        target_region = json.load(f)

    # 対象領域のbounding boxを作成
    sw = target_region["south-west"]
    ne = target_region["north-east"]
    region_box = box(sw["lon"], sw["lat"], ne["lon"], ne["lat"])

    # 領域内のメッシュを抽出
    filtered_meshes = []
    for feature in population_mesh["features"]:
        if is_mesh_in_region(feature["geometry"]["coordinates"], region_box):
            mesh_data = {
                "mesh_code": feature["properties"]["meshCode"],
                "population": feature["properties"]["population"],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": feature["geometry"]["coordinates"],
                },
            }
            filtered_meshes.append(mesh_data)

    # 結果を出力
    output = {"mesh": filtered_meshes}
    with open(output_mesh_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(
        f"✅ Filtered {len(filtered_meshes)} meshes out of {len(population_mesh['features'])} total meshes"
    )


if __name__ == "__main__":
    input_population_mesh_file = sys.argv[1]
    input_target_region_file = sys.argv[2]
    output_mesh_file = sys.argv[3]

    main(input_population_mesh_file, input_target_region_file, output_mesh_file)
