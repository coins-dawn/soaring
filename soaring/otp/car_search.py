import json
import csv
import requests
import sys
import os
import time

def load_stops(json_path):
    """バス停データを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("combus-stops", [])

def get_travel_time(from_stop, to_stop):
    """2つのバス停間の所要時間と距離を取得"""
    base_url = "http://localhost:8080/otp/routers/default/plan"
    
    # バス停データの検証
    if not all(key in from_stop and key in to_stop for key in ['lat', 'lon']):
        return None, None

    params = {
        "fromPlace": f"{from_stop['lat']},{from_stop['lon']}",
        "toPlace": f"{to_stop['lat']},{to_stop['lon']}",
        "mode": "CAR",
        "date": "10-09-2025",
        "time": "12:00:00",
        "arriveBy": "false",
        "numItineraries": 1
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 経路が見つかった場合、所要時間（分）と距離（メートル）を返す
        if "plan" in data and data["plan"]["itineraries"]:
            itinerary = data["plan"]["itineraries"][0]
            leg = itinerary["legs"][0]
            duration_m = leg["duration"] / 60  # 秒から分に変換
            distance_km = leg["distance"] / 1000  # メートルからキロメートルに変換
            geometry = leg["legGeometry"]["points"]
            return duration_m, distance_km, geometry
        return None, None, None
    
    except Exception as e:
        print(f"Error calculating travel time: {e}")
        return None, None, None

def main():
    if len(sys.argv) != 3:
        print("Usage: python car_search.py <combus_stops.json> <output_dir>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)
    
    # バス停データの読み込み
    stops = load_stops(input_path)
    print(f"Loaded {len(stops)} stops")

    # 結果を格納するリスト
    routes = []
    
    # すべての組み合わせに対して所要時間を計算
    total_pairs = len(stops) * (len(stops) - 1)
    current_pair = 0

    for from_stop in stops:
        for to_stop in stops:
            if from_stop == to_stop:
                continue
                
            current_pair += 1
            print(f"Processing pair {current_pair}/{total_pairs}...")

            # 所要時間と距離を計算
            duration_m, distance_km, geometry = get_travel_time(from_stop, to_stop)
            
            # 結果を追加
            if duration_m is not None and distance_km is not None and geometry is not None:
                routes.append({
                    'from': from_stop.get('id', 'unknown'),
                    'to': to_stop.get('id', 'unknown'),
                    'distance_km': round(distance_km, 2),
                    'duration_m': round(duration_m, 2),
                    "geometry": geometry
                })

    # 結果をJSONファイルに出力
    output = {'combus-routes': routes}
    output_path = os.path.join(output_dir, 'combus_routes.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"Results written to {output_path}")

if __name__ == "__main__":
    main()