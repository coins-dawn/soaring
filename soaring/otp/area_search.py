import sys
import json
import requests

MAX_WALK_DISTANCE_M = 1000  # 徒歩の最大距離[m]

def exec_single_spot(spot: dict, output_dir_path: str):
    id = spot["id"]
    name = spot["name"]
    lat = spot["lat"]
    lon = spot["lon"]

    initial_time_limit = 10 * 60  # 10分
    trial_num = 111 # 10分 -> 120分まで1分刻み

    # リクエストの構築
    host = "http://localhost:8080"
    path = "/otp/routers/default/isochrone"
    params = {
        "fromPlace": f"{lat},{lon}",
        "mode": "WALK,TRANSIT",
        "date": "10-01-2025",
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
        time = int(feature["properties"]["time"])
        result_dict[time] = geometry

    prev_geometry = None
    for time_limit in time_limits:
        geometry = result_dict[time_limit]
        if prev_geometry != None and geometry == prev_geometry:
            continue
        time_limit_min = time_limit // 60
        output_path = f"{output_dir_path}/{id}_{time_limit_min}.geojson"
        with open(output_path, "w") as f:
            json.dump(geometry, f, ensure_ascii=False, indent=2)
        prev_geometry = geometry


def exec_single_category(category_name: str, spot_list: list, output_dir_path: str):
    for spot in spot_list:
        exec_single_spot(spot, output_dir_path)


def main(area_search_json_path, output_dir_path):
    with open(area_search_json_path, "r") as f:
        area_search_json = json.load(f)

    for category_name, spot_list in area_search_json.items():
        exec_single_category(category_name, spot_list, output_dir_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python area_search.py <arg1> <arg2>")
        sys.exit(1)

    area_search_json_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    main(area_search_json_path, output_dir_path)
