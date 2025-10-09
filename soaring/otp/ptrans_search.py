import json
import requests
import sys
import os

MAX_WALK_DISTANCE_M = 1000  # 徒歩の最大距離[m]

def load_spots(json_path):
    """スポットデータを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    spots = []
    for category in data.values():
        spots.extend(category)
    return spots

def load_stops(json_path):
    """バス停データを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("combus-stops", [])

def get_travel_time(from_spot, to_stop):
    """スポットからバス停までの所要時間を取得"""
    base_url = "http://localhost:8080/otp/routers/default/plan"
    
    params = {
        "fromPlace": f"{from_spot['lat']},{from_spot['lon']}",
        "toPlace": f"{to_stop['lat']},{to_stop['lon']}",
        "mode": "WALK,TRANSIT",
        "date": "10-01-2025",
        "time": "10:00:00",
        "maxWalkDistance": f"{MAX_WALK_DISTANCE_M}",
        "numItineraries": 1
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 経路が見つかった場合、所要時間（分）を返す
        if "plan" in data and data["plan"]["itineraries"]:
            itinerary = data["plan"]["itineraries"][0]
            duration_m = itinerary["duration"] / 60  # 秒から分に変換
            walk_distance_m = itinerary["walkDistance"]
            return int(duration_m), int(walk_distance_m)
        return None, None
    
    except Exception as e:
        print(f"Error calculating travel time: {e}")
        return None, None

def main():
    if len(sys.argv) != 4:
        print("Usage: python ptrans_spot_to_stops.py <spots_json> <stops_json> <output_dir>")
        sys.exit(1)

    spots_path = sys.argv[1]
    stops_path = sys.argv[2]
    output_dir = sys.argv[3]
    os.makedirs(output_dir, exist_ok=True)
    
    # データの読み込み
    spots = load_spots(spots_path)
    stops = load_stops(stops_path)
    print(f"Loaded {len(spots)} spots and {len(stops)} stops")

    # 結果を格納するリスト
    routes = []
    
    # すべての組み合わせに対して所要時間を計算
    total_pairs = len(spots) * len(stops)
    current_pair = 0

    for spot in spots:
        for stop in stops:
            current_pair += 1
            print(f"Processing pair {current_pair}/{total_pairs}...")
            
            # 所要時間を計算
            duration_m, walk_distance_m = get_travel_time(spot, stop)
            
            # 結果を追加
            if duration_m is not None:
                routes.append({
                    'from': spot['id'],
                    'to': stop['id'],
                    'duration_m': duration_m,
                    'walk_distance_m': walk_distance_m
                })

    # 結果をJSONファイルに出力
    output = {'spot-to-stops': routes}
    output_path = os.path.join(output_dir, 'spot_to_stops.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"Results written to {output_path}")

if __name__ == "__main__":
    main()