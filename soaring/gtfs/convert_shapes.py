import csv
import json
import sys
from collections import defaultdict

def load_stops(stops_file):
    """ stops.txt を読み込み、stop_id ごとの緯度・経度を取得 """
    stop_locations = {}

    with open(stops_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stop_id = row['stop_id']
            lat = float(row['stop_lat'])
            lon = float(row['stop_lon'])
            stop_locations[stop_id] = (lat, lon)

    return stop_locations

def load_trips(trips_file):
    """ trips.txt を読み込み、trip_id ごとの shape_id を取得 """
    trip_shapes = {}

    with open(trips_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            trip_id = row['trip_id']
            shape_id = row['shape_id']
            trip_shapes[trip_id] = shape_id

    return trip_shapes

def load_stop_times(stop_times_file, trips_file):
    """ stop_times.txt を読み込み、trip_idごとのstop_sequenceを取得 """
    trip_stops = defaultdict(list)
    trip_shapes = load_trips(trips_file)  # trips.txt から shape_id を取得

    with open(stop_times_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            trip_id = row['trip_id']
            stop_id = row['stop_id']
            stop_sequence = int(row['stop_sequence'])
            trip_stops[trip_id].append((stop_id, stop_sequence))

    # stop_sequenceでソート
    for trip_id in trip_stops:
        trip_stops[trip_id].sort(key=lambda x: x[1])

    return trip_stops, trip_shapes

def load_shapes(shapes_file):
    """ shapes.txt を読み込み、shape_idごとの緯度・経度リストを取得 """
    shapes = defaultdict(list)

    with open(shapes_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            shape_id = row['shape_id']
            lat = float(row['shape_pt_lat'])
            lon = float(row['shape_pt_lon'])
            shape_pt_sequence = int(row['shape_pt_sequence'])
            shapes[shape_id].append((shape_pt_sequence, lat, lon))

    # shape_pt_sequenceでソート
    for shape_id in shapes:
        shapes[shape_id].sort(key=lambda x: x[0])

    return shapes

stop_cache = {}

def find_nearest_shape_point(stop_lat, stop_lon, shape_points, stop, trip_id):
    """ 停留所の緯度経度に最も近いshapeポイントを見つける """
    if cache := stop_cache.get((stop, trip_id)):
        return cache
    
    min_distance = float('inf')
    nearest_index = -1

    for i, (_, shape_lat, shape_lon) in enumerate(shape_points):
        dx = stop_lon - shape_lon
        dy = stop_lat - shape_lat
        distance = dx**2 + dy**2  # 近似距離計算 (軽量)

        if distance < min_distance:
            min_distance = distance
            nearest_index = i
    
    stop_cache[(stop, trip_id)] = nearest_index

    return nearest_index

def get_shape_between_stops(stop_a, stop_b, stop_locations, trip_stops, trip_shapes, shapes):
    """ stop_a から stop_b までの最も短い shape を取得 """
    if stop_a not in stop_locations or stop_b not in stop_locations:
        return None

    lat_a, lon_a = stop_locations[stop_a]
    lat_b, lon_b = stop_locations[stop_b]

    shortest_shape = None
    shortest_length = float('inf')

    for trip_id, stops in trip_stops.items():
        stop_indices = {stop_id: i for i, (stop_id, _) in enumerate(stops)}

        if stop_a in stop_indices and stop_b in stop_indices:
            if stop_indices[stop_a] < stop_indices[stop_b]:
                shape_id = trip_shapes.get(trip_id)

                if shape_id and shape_id in shapes:
                    shape_points = shapes[shape_id]

                    index_a = find_nearest_shape_point(lat_a, lon_a, shape_points, stop_a, trip_id)
                    index_b = find_nearest_shape_point(lat_b, lon_b, shape_points, stop_b, trip_id)

                    if index_a < index_b:
                        shape_segment = [(lat, lon) for _, lat, lon in shape_points[index_a:index_b + 1]]

                        # 最も点の数が少ない shape を選択
                        if len(shape_segment) < shortest_length:
                            shortest_length = len(shape_segment)
                            shortest_shape = shape_segment

    return shortest_shape


def process_stop_pairs(input_file, output_json, stops_file, stop_times_file, trips_file, shapes_file):
    """ 大量の停留所ペアを処理し、結果をJSONに出力 """
    results = []    
    stop_locations = load_stops(stops_file)
    trip_stops, trip_shapes = load_stop_times(stop_times_file, trips_file)
    shapes = load_shapes(shapes_file)

    with open(input_file, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader, start=1):
            stop_from = row['stop_from']
            stop_to = row['stop_to']
            shape = get_shape_between_stops(stop_from, stop_to, stop_locations, trip_stops, trip_shapes, shapes)
            if shape:
                results.append({
                    "stop_from": stop_from,
                    "stop_to": stop_to,
                    "shape": shape
                })
    
    with open(output_json, 'w', encoding='utf-8') as jsonfile:
        json.dump(results, jsonfile, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    stops_file = input_dir + "/stops.txt"
    stop_times_file = input_dir + "/stop_times.txt"
    trips_file = input_dir + "/trips.txt"
    shapes_file = input_dir + "/shapes.txt"
    input_file = output_dir + "/average_travel_times.csv"
    output_json = output_dir + "/shapes.json"

    print(">>> 軌跡データの作成を開始...")
    process_stop_pairs(input_file, output_json, stops_file, stop_times_file, trips_file, shapes_file)
    print("<<< 完了しました。")
