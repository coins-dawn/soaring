import sys
import json
import requests


def exec_area_search(lat: float, lon: float, time_limit: int):
    host = "http://localhost:8080"
    path = "/otp/routers/default/isochrone"
    params = {
        "fromPlace": f"{lat},{lon}",
        "mode": "WALK,TRANSIT",
        "date": "10-01-2025",
        "time": "10:00am",
        "maxWalkDistance": "200",
        "cutoffSec": f"{time_limit}"
    }

    url = f"{host}{path}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    response = requests.get(url)
    assert response
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json["features"]) == 1

    geometry = response_json["features"][0]["geometry"]
    return geometry


def exec_single_spot(spot: dict, output_dir_path: str):
    id = spot["id"]
    name = spot["name"]
    lat = spot["lat"]
    lon = spot["lon"]
    
    # 10分から2時間まで10分刻み（秒）
    time_limit_set_list = [
        i * 60 for i in range(10, 121, 10)
    ]
    for time_limit in time_limit_set_list:
        geometry = exec_area_search(lat, lon, time_limit)
        time_limit_minute = time_limit // 60
        output_path = f"{output_dir_path}/{id}_{time_limit_minute}.geojson"
        with open(output_path, "w") as f:
            json.dump(geometry, f, ensure_ascii=False, indent=2)

    
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
