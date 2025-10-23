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


class Geojson:
    def __init__(
        self,
        id: str,
        time_limit_min: int,
        geometry: MultiPolygon,
        reachable_mesh_codes: set[str],
    ):
        self.id: str = id
        self.time_limit_min: int = time_limit_min
        self.geometry: MultiPolygon = geometry
        self.reachable_mesh_codes: set[str] = reachable_mesh_codes


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
    """Open Trip Plannerで到達圏探索を実行する"""
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
    return response.json()


def calc_geojson_list(
    time_limits: list, time_to_geometry_dict: dict, spot_id: str
) -> list[Geojson]:
    """GeoJSONリストを計算する"""
    prev_geometry = None
    geojson_list = []
    for time_limit in time_limits:
        geometry = time_to_geometry_dict[time_limit]
        # ひとつ前と一緒なら出力しない
        if prev_geometry != None and geometry == prev_geometry:
            continue
        geojson_list.append(
            Geojson(
                id=spot_id,
                time_limit_min=time_limit // 60,
                geometry=geometry,
                reachable_mesh_codes=set(),  # 一旦空で初期化
            )
        )
        prev_geometry = geometry
    return geojson_list


def calc_and_update_reachable_meshs(
    geojson_list: list[Geojson], all_mesh_list: list[Mesh]
) -> set[str]:
    """各GeoJSONに対して到達可能なメッシュコードを計算し、GeoJSONオブジェクトを更新する"""
    # 高速化のため、最初に一番大きなGeojsonを計算
    max_geojson = geojson_list[-1]
    reachable_mesh_code_set = find_intersecting_meshes(
        shape(max_geojson.geometry), all_mesh_list
    )
    geojson_list[-1].reachable_mesh_codes = reachable_mesh_code_set

    # 二番目以降のGeojsonについては、最大geojsonで到達できたメッシュだけを探す
    max_geojson_reachable_mesh_list = [
        mesh for mesh in all_mesh_list if mesh.mesh_code in reachable_mesh_code_set
    ]
    for geojson in geojson_list[:-1]:
        reachable_meshes = find_intersecting_meshes(
            shape(geojson.geometry), max_geojson_reachable_mesh_list
        )
        geojson.reachable_mesh_codes.update(reachable_meshes)
    return reachable_mesh_code_set


def exec_single_spot(
    spot: dict, all_mesh_list: list[Mesh]
) -> tuple[list[Geojson], set[str]]:
    # 時間制限リストの作成
    initial_time_limit = 10 * 60  # 10分
    trial_num = 111  # 10分 -> 120分まで1分刻み
    time_limits = [initial_time_limit + i * 60 for i in range(trial_num)]

    # Open Trip Plannerに問い合わせ
    response_json = request_to_otp(spot, time_limits)
    time_to_geometry_dict = {}
    for i in range(trial_num):
        feature = response_json["features"][i]
        geometry = feature["geometry"]
        time = int(feature["properties"]["time"])
        time_to_geometry_dict[time] = geometry

    # GeoJSONリストを計算
    geojson_list = calc_geojson_list(time_limits, time_to_geometry_dict, spot["id"])
    reachable_mesh_code_set = calc_and_update_reachable_meshs(
        geojson_list, all_mesh_list
    )

    return geojson_list, reachable_mesh_code_set


def write_geojsons(
    geojson_list: list[Geojson],
    output_geojson_dir_path: str,
    output_geojson_txt_dir_path: str,
):
    """GeoJSONリストをファイルに書き出す"""
    for geojson in geojson_list:
        feature = {
            "type": "Feature",
            "properties": {"reachable-mesh": list(geojson.reachable_mesh_codes)},
            "geometry": geojson.geometry,
        }
        time_limit_min = geojson.time_limit_min
        id = geojson.id
        output_path = f"{output_geojson_dir_path}/{id}_{time_limit_min}.bin"
        output_txt_path = f"{output_geojson_txt_dir_path}/{id}_{time_limit_min}.json"
        with open(output_path, "wb") as f:
            pickle.dump(feature, f)
        with open(output_txt_path, "w") as f:
            json.dump(feature, f)


def write_reachable_meshes(
    mesh_list: list[Mesh], reachable_mesh_code_set: set[str], output_mesh_json_path: str
):
    """到達可能なメッシュをファイルに書き出す"""
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
    geojson_list = []
    total_spots = len(all_spot_list)
    for i, spot in enumerate(all_spot_list, 1):
        geojson_list_tmp, reachable_meshes = exec_single_spot(spot, all_mesh_list)
        reachable_mesh_code_set.update(reachable_meshes)
        geojson_list.extend(geojson_list_tmp)
        # 進捗を出力
        progress = (i / total_spots) * 100
        print(f"Progress: {progress:.1f}% ({i}/{total_spots})", end="\r")
    print()

    # 結果を出力する
    write_geojsons(geojson_list, output_geojson_dir_path, output_geojson_txt_dir_path)
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
