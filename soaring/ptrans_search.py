import json
import requests
import sys
import datetime
import polyline
import concurrent.futures
import threading
import os

MAX_WALK_DISTANCE_M = 100000  # 徒歩の最大距離[m]


def load_spots(json_path):
    """スポットデータを読み込む"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    spots = []
    for category in data.values():
        spots.extend(category)
    return spots


def load_stops(json_path):
    """バス停データを読み込む"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("combus-stops", [])


def load_refpoints(json_path):
    """参照点データを読み込む"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("ref-points", [])


def merge_geometry(geometry_list: list[str]) -> str:
    coords = []
    for geom in geometry_list:
        coords.extend(polyline.decode(geom))
    merged_geom = polyline.encode(coords)
    return merged_geom


def get_travel_time(from_spot, to_stop, max_walk_distance_m: int):
    """スポットからバス停までの所要時間と経路形状を取得"""
    base_url = "http://localhost:8080/otp/routers/default/plan"

    # 現在の日付を取得してMM-DD-YYYYフォーマットに変換
    current_date = datetime.datetime.now().strftime("%m-%d-%Y")

    params = {
        "fromPlace": f"{from_spot['lat']},{from_spot['lon']}",
        "toPlace": f"{to_stop['lat']},{to_stop['lon']}",
        "mode": "WALK,TRANSIT",
        "date": current_date,
        "time": "10:00:00",
        "maxWalkDistance": max_walk_distance_m,
        "numItineraries": 1,
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 経路が見つかった場合、所要時間（分）と形状を返す
        if "plan" in data and data["plan"]["itineraries"]:
            itinerary = data["plan"]["itineraries"][0]
            duration_m = itinerary["duration"] / 60  # 秒から分に変換
            walk_distance_m = itinerary["walkDistance"]
            # geometry = itinerary["legs"][0]["legGeometry"][
            #     "points"
            # ]  # Google Polyline形式
            geometry_list = []

            # 区間情報の取得
            sections = []
            for leg in itinerary["legs"]:
                section = {
                    "mode": leg["mode"],
                    "from": {
                        "name": leg["from"].get("name", ""),
                        "lat": leg["from"]["lat"],
                        "lon": leg["from"]["lon"],
                    },
                    "to": {
                        "name": leg["to"].get("name", ""),
                        "lat": leg["to"]["lat"],
                        "lon": leg["to"]["lon"],
                    },
                    "duration_m": int(leg["duration"] / 60),  # 秒から分に変換
                    "distance_m": int(leg["distance"]),
                    "geometry": leg["legGeometry"]["points"],
                }
                sections.append(section)
                geometry_list.append(leg["legGeometry"]["points"])
            geometry = merge_geometry(geometry_list)

            return int(duration_m), int(walk_distance_m), geometry, sections
        return None, None, None, None

    except Exception as e:
        print(f"Error calculating travel time: {e}")
        return None, None, None, None


def _process_pair(args):
    spot, stop, max_walk_distance_m = args
    duration_m, walk_distance_m, geometry, sections = get_travel_time(
        spot, stop, max_walk_distance_m
    )
    if duration_m is None:
        return None
    return {
        "from": spot["id"],
        "to": stop["id"],
        "duration_m": duration_m,
        "walk_distance_m": walk_distance_m,
        "geometry": geometry,
        "sections": sections,
    }


def execute(elem_list_1: list, elem_list_2: list, max_walk_distance_m: int):
    """
    与えられたリストの掛け合わせの数だけ公共交通探索を行う。
    並列実行でスループットを向上させる。
    """
    routes = []
    total_pairs = len(elem_list_1) * len(elem_list_2)
    if total_pairs == 0:
        return routes

    pairs_iter = (
        (spot, stop, max_walk_distance_m) for spot in elem_list_1 for stop in elem_list_2
    )

    processed = 0
    last_percentage = -1
    lock = threading.Lock()

    max_workers = min(32, (os.cpu_count() or 4) * 5)  # I/O主体なのでスレッド数を多めに
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_pair, args) for args in pairs_iter]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                routes.append(result)

            with lock:
                processed += 1
                current_percentage = int((processed / total_pairs) * 100)
                if current_percentage > last_percentage:
                    print(f"Progress: {current_percentage}%")
                    last_percentage = current_percentage

    if last_percentage < 100:
        print("Progress: 100%")

    return routes


def write_json(output_dir: str, key: str, routes: list):
    output = {key: routes}
    with open(output_dir + f"/{key}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)


def main(
    input_spots_path: str,
    input_stops_path: str,
    input_refpoint_path: str,
    output_dir: str,
):
    # データの読み込み
    spots = load_spots(input_spots_path)
    stops = load_stops(input_stops_path)
    refpoints = load_refpoints(input_refpoint_path)

    spots_to_stops = execute(spots, stops, MAX_WALK_DISTANCE_M)
    write_json(output_dir, "spot_to_stops", spots_to_stops)

    # # spots to refpointsは徒歩距離が上限を超えることを許容する
    # spots_to_refpoints = execute(spots, refpoints, MAX_WALK_DISTANCE_M)
    # write_json(output_dir, "spot_to_refpoints", spots_to_refpoints)

    # stops_to_refpoints = execute(stops, refpoints, MAX_WALK_DISTANCE_M)
    # write_json(output_dir, "stop_to_refpoints", stops_to_refpoints)


if __name__ == "__main__":
    input_spots_path = sys.argv[1]
    input_stops_path = sys.argv[2]
    input_refpoint_path = sys.argv[3]
    output_dir = sys.argv[4]
    main(input_spots_path, input_stops_path, input_refpoint_path, output_dir)
