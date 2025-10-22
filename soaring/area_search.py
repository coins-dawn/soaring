import sys
import json
import requests
import pickle
from shapely.geometry import shape, Polygon, MultiPolygon

MAX_WALK_DISTANCE_M = 1000  # 徒歩の最大距離[m]

MESH_FILE_PATH = "work/input/population-mesh.json"


class Mesh:
    def __init__(self, feature: dict):
        self.mesh_code = feature["properties"]["meshCode"]
        self.geometry = shape(feature["geometry"])
        if not isinstance(self.geometry, Polygon):
            raise ValueError(f"Geometry must be Polygon, got {type(self.geometry)}")


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


def exec_single_spot(spot: dict, output_dir_path: str, mesh_list: list[Mesh]):
    id = spot["id"]
    name = spot["name"]
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
    for time_limit in time_limits:
        geometry = result_dict[time_limit]
        if prev_geometry != None and geometry == prev_geometry:
            continue
        reachable_meshes = find_intersecting_meshes(shape(geometry), mesh_list)
        feature = {
            "type": "Feature",
            "properties": {
                "reachable-mesh": list(reachable_meshes)
            },
            "geometry": geometry,
        }
        time_limit_min = time_limit // 60
        output_path = f"{output_dir_path}/{id}_{time_limit_min}.bin"
        output_txt_path = f"{output_dir_path}_txt/{id}_{time_limit_min}.json"
        with open(output_path, "wb") as f:
            pickle.dump(feature, f)
        with open(output_txt_path, "w") as f:
            json.dump(feature, f)
        prev_geometry = geometry


def exec_single_category(
    spot_list: list, output_dir_path: str, mesh_list: list
):
    for spot in spot_list:
        exec_single_spot(spot, output_dir_path, mesh_list)


def main(area_search_json_path, output_dir_path):
    with open(area_search_json_path, "r") as f:
        area_search_json = json.load(f)

    mesh_list = load_population_mesh(MESH_FILE_PATH)

    for _, spot_list in area_search_json.items():
        exec_single_category(spot_list, output_dir_path, mesh_list)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python area_search.py <arg1> <arg2>")
        sys.exit(1)

    area_search_json_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    main(area_search_json_path, output_dir_path)
