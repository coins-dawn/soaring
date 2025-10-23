import sys
import json
import requests
import pickle
from shapely.geometry import shape, Polygon, MultiPolygon

MAX_WALK_DISTANCE_M = 1000  # 徒歩の最大距離[m]


class Mesh:
    def __init__(self, feature: dict):
        self.mesh_code = feature["properties"]["meshCode"]
        self.geometry = shape(feature["geometry"])
        self.population = int(feature["properties"].get("population"))


def load_population_mesh(input_path: str) -> list[Mesh]:
    """人口メッシュデータを読み込み、Meshオブジェクトのリストとして返す"""
    mesh_list = []
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for feature in data["features"]:
            try:
                mesh = Mesh(feature)
                mesh_list.append(mesh)
            except Exception as e:
                print(f"Error loading mesh: {e}")
    return mesh_list


def find_intersecting_meshes(
    multi_polygon: MultiPolygon, mesh_list: list[Mesh]
) -> set[str]:
    """GeoJSONと交差するメッシュコードの集合を返す"""
    mesh_codes = set()
    for mesh in mesh_list:
        if multi_polygon.intersects(mesh.geometry):
            mesh_codes.add(mesh.mesh_code)
    return mesh_codes


def exec_single_spot(
    spot, mesh_list, output_geojson_dir_path, output_geojson_txt_dir_path
) -> set[str]:
    id = spot["id"]
    lat = spot["lat"]
    lon = spot["lon"]

    initial_time_limit = 10 * 60  # 10分
    trial_num = 111  # 10分 -> 120分まで1分刻み

    # リクエストの構築
    host = "http://localhost:8080"
    path = "/otp/routers/default/isochrone"
    params = {
        "fromPlace": f"{lat},{lon}",
        "mode": "WALK,TRANSIT",
        "date": "10-23-2025",
        "time": "10:00am",
        "maxWalkDistance": f"{MAX_WALK_DISTANCE_M}",
    }
    url = f"{host}{path}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    time_limits = [initial_time_limit + i * 60 for i in range(trial_num)]
    for time_limit in time_limits:
        url += f"&cutoffSec={time_limit}"

    # OpenTripPlannerに問い合わせ
    response = requests.get(url)
    assert response
    assert response.status_code == 200

    # 結果をgeojsonとして保存
    response_json = response.json()
    assert len(response_json["features"]) == trial_num
    result_dict = {}
    for i in range(trial_num):
        feature = response_json["features"][i]
        geometry = feature["geometry"]
        assert geometry["type"] == "MultiPolygon"
        time = int(feature["properties"]["time"])
        result_dict[time] = geometry

    prev_geometry = None
    reachable_mesh_code_set = set()
    for time_limit in time_limits:
        geometry = result_dict[time_limit]
        if prev_geometry != None and geometry == prev_geometry:
            continue
        reachable_meshes = find_intersecting_meshes(shape(geometry), mesh_list)
        reachable_mesh_code_set.update(reachable_meshes)
        feature = {
            "type": "Feature",
            "properties": {"reachable-mesh": list(reachable_meshes)},
            "geometry": geometry,
        }
        time_limit_min = time_limit // 60
        output_path = f"{output_geojson_dir_path}/{id}_{time_limit_min}.bin"
        output_txt_path = f"{output_geojson_txt_dir_path}/{id}_{time_limit_min}.json"
        with open(output_path, "wb") as f:
            pickle.dump(feature, f)
        with open(output_txt_path, "w") as f:
            json.dump(feature, f)
        prev_geometry = geometry

    return reachable_mesh_code_set


def exec_single_category(
    spot_list: list,
    mesh_list: list[Mesh],
    output_geojson_dir_path: str,
    output_geojson_txt_dir_path: str,
) -> set[str]:
    """
    ひとつのカテゴリについて到達圏探索を行いgeojsonを生成する。
    また、到達可能なメッシュの集合を返却する。
    """
    reachable_mesh_code_set = set()
    for spot in spot_list:
        reachable_mesh_code_set.update(
            exec_single_spot(
                spot, mesh_list, output_geojson_dir_path, output_geojson_txt_dir_path
            )
        )
    return reachable_mesh_code_set

def write_reachable_meshes(mesh_list: list[Mesh], reachable_mesh_code_set: set[str]):
    reachable_meshes = []
    for mesh in mesh_list:
        if mesh.mesh_code not in reachable_mesh_code_set:
            continue

        # GeoJSONフォーマットに変換
        mesh_feature = {
            "mesh_code": mesh.mesh_code,
            "population": mesh.population,
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[p[0], p[1]] for p in mesh.geometry.exterior.coords]],
            },
        }
        reachable_meshes.append(mesh_feature)

    # mesh.jsonを出力
    output_mesh_path = f"work/output/mesh.json"
    with open(output_mesh_path, "w", encoding="utf-8") as f:
        json.dump({"mesh": reachable_meshes}, f, ensure_ascii=False, indent=4)


def main(
    input_combus_stpops_json_path,
    input_toyama_spot_list_json_path,
    input_population_mesh_json_path,
    output_geojson_dir_path,
    output_geojson_txt_dir_path,
):
    with open(input_combus_stpops_json_path, "r") as f:
        combus_stop_list_dict = json.load(f)
    with open(input_toyama_spot_list_json_path, "r") as f:
        toyama_spot_list_dict = json.load(f)
    mesh_list = load_population_mesh(input_population_mesh_json_path)
    merged_spot_list_dict = combus_stop_list_dict | toyama_spot_list_dict

    reachable_mesh_code_set = set()
    for spot_list in merged_spot_list_dict.values():
        reachable_mesh_code_set.update(
            exec_single_category(
                spot_list,
                mesh_list,
                output_geojson_dir_path,
                output_geojson_txt_dir_path,
            )
        )

    # 到達可能なメッシュのみを抽出してJSON形式で出力



if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Invalid arguments")
        sys.exit(1)

    input_combus_stpops_json_path = sys.argv[1]
    input_toyama_spot_list_json_path = sys.argv[2]
    input_population_mesh_json_path = sys.argv[3]
    output_geojson_dir_path = sys.argv[4]
    output_geojson_txt_dir_path = sys.argv[5]
    main(
        input_combus_stpops_json_path,
        input_toyama_spot_list_json_path,
        input_population_mesh_json_path,
        output_geojson_dir_path,
        output_geojson_txt_dir_path,
    )
