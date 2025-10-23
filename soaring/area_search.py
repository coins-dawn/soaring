import sys
import json
import requests
import pickle
import time  # ファイル先頭に追加
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


def load_all_spots(
    input_combus_stpops_json_path: str, input_toyama_spot_list_json_path: str
) -> list[dict]:
    """スポット情報を読み込み、結合してリストとして返す"""
    with open(input_combus_stpops_json_path, "r") as f:
        combus_stop_list_dict = json.load(f)
    with open(input_toyama_spot_list_json_path, "r") as f:
        toyama_spot_list_dict = json.load(f)
    merged_spot_list_dict = combus_stop_list_dict | toyama_spot_list_dict
    return [spot for spots in merged_spot_list_dict.values() for spot in spots]


def find_intersecting_meshes(
    multi_polygon: MultiPolygon, mesh_list: list[Mesh]
) -> set[str]:
    """GeoJSONと交差するメッシュコードの集合を返す"""
    mesh_codes = set()
    for mesh in mesh_list:
        if multi_polygon.intersects(mesh.geometry):
            mesh_codes.add(mesh.mesh_code)
    return mesh_codes


def request_to_otp(spot: dict, time_limits: list) -> dict:
    """
    Open Trip Plannerで到達圏探索を実行する。
    """
    lat = spot["lat"]
    lon = spot["lon"]
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
    for time_limit in time_limits:
        url += f"&cutoffSec={time_limit}"
    response = requests.get(url)
    assert response
    assert response.status_code == 200
    return response.json()


def exec_single_spot(
    spot, all_mesh_list, output_geojson_dir_path, output_geojson_txt_dir_path
) -> set[str]:
    # 時間制限リストの作成
    initial_time_limit = 10 * 60  # 10分
    trial_num = 111  # 10分 -> 120分まで1分刻み
    time_limits = [initial_time_limit + i * 60 for i in range(trial_num)]

    # Open Trip Plannerに問い合わせ
    response_json = request_to_otp(spot, time_limits)

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
        reachable_meshes = find_intersecting_meshes(shape(geometry), all_mesh_list)
        reachable_mesh_code_set.update(reachable_meshes)
        feature = {
            "type": "Feature",
            "properties": {"reachable-mesh": list(reachable_meshes)},
            "geometry": geometry,
        }
        time_limit_min = time_limit // 60
        id = spot["id"]
        output_path = f"{output_geojson_dir_path}/{id}_{time_limit_min}.bin"
        output_txt_path = f"{output_geojson_txt_dir_path}/{id}_{time_limit_min}.json"
        with open(output_path, "wb") as f:
            pickle.dump(feature, f)
        with open(output_txt_path, "w") as f:
            json.dump(feature, f)
        prev_geometry = geometry

    return reachable_mesh_code_set


def write_reachable_meshes(
    mesh_list: list[Mesh], reachable_mesh_code_set: set[str], output_mesh_json_path: str
):
    reachable_meshes = []
    for mesh in mesh_list:
        if mesh.mesh_code not in reachable_mesh_code_set:
            continue
        mesh_feature = {
            "mesh_code": mesh.mesh_code,
            "population": mesh.population,
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[p[0], p[1]] for p in mesh.geometry.exterior.coords]],
            },
        }
        reachable_meshes.append(mesh_feature)
    with open(output_mesh_json_path, "w", encoding="utf-8") as f:
        json.dump({"mesh": reachable_meshes}, f, ensure_ascii=False, indent=4)


def main(
    input_combus_stpops_json_path,
    input_toyama_spot_list_json_path,
    input_population_mesh_json_path,
    output_geojson_dir_path,
    output_geojson_txt_dir_path,
    output_mesh_json_path,
):
    # データ入力データをロード
    all_mesh_list = load_population_mesh(input_population_mesh_json_path)
    all_spot_list = load_all_spots(
        input_combus_stpops_json_path, input_toyama_spot_list_json_path
    )

    # 到達圏探索を実行しgeojsonを取得
    reachable_mesh_code_set = set()
    total_spots = len(all_spot_list)
    for i, spot in enumerate(all_spot_list, 1):
        reachable_mesh_code_set.update(
            exec_single_spot(
                spot,
                all_mesh_list,
                output_geojson_dir_path,
                output_geojson_txt_dir_path,
            )
        )
        progress = (i / total_spots) * 100
        print(f"Progress: {progress:.1f}% ({i}/{total_spots})", end="\r")
        break
    print()

    # 結果を出力する
    write_reachable_meshes(
        all_mesh_list, reachable_mesh_code_set, output_mesh_json_path
    )


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("Invalid arguments")
        sys.exit(1)

    input_combus_stpops_json_path = sys.argv[1]
    input_toyama_spot_list_json_path = sys.argv[2]
    input_population_mesh_json_path = sys.argv[3]
    output_geojson_dir_path = sys.argv[4]
    output_geojson_txt_dir_path = sys.argv[5]
    output_mesh_json_path = sys.argv[6]

    start_time = time.time()
    main(
        input_combus_stpops_json_path,
        input_toyama_spot_list_json_path,
        input_population_mesh_json_path,
        output_geojson_dir_path,
        output_geojson_txt_dir_path,
        output_mesh_json_path,
    )
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"実行時間: {execution_time:.2f}秒")
