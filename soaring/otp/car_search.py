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
    """2つのバス停間の所要時間を取得"""
    base_url = "http://localhost:8080/otp/routers/default/plan"
    
    # バス停データの検証
    if not all(key in from_stop and key in to_stop for key in ['lat', 'lon']):
        return None

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
        
        # 経路が見つかった場合、所要時間（分）を返す
        if "plan" in data and data["plan"]["itineraries"]:
            return data["plan"]["itineraries"][0]["duration"] / 60
        return None
    
    except Exception as e:
        print(f"Error calculating travel time: {e}")
        return None

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
    results = []
    
    # すべての組み合わせに対して所要時間を計算
    total_pairs = len(stops) * (len(stops) - 1)
    current_pair = 0

    count = 0

    for from_stop in stops:
        for to_stop in stops:
            if from_stop == to_stop:
                continue
        
            count += 1
            if count > 30:
                break
                
            current_pair += 1
            print(f"Processing pair {current_pair}/{total_pairs}...")

            # 所要時間を計算
            duration = get_travel_time(from_stop, to_stop)
            
            # 結果を追加
            results.append({
                'stop_from': from_stop.get('id', 'unknown'),
                'stop_to': to_stop.get('id', 'unknown'),
                'average_travel_time': round(duration, 2) if duration is not None else ''
            })

    # 結果をCSVファイルに出力
    output_path = os.path.join(output_dir, 'car_travel_times.csv')
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['stop_from', 'stop_to', 'average_travel_time'])
        writer.writeheader()
        writer.writerows(results)

    print(f"Results written to {output_path}")

if __name__ == "__main__":
    main()