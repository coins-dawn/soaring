import csv
import sys
from collections import defaultdict


def parse_time(time_str):
    """HH:MM:SS形式の文字列を分単位の数値に変換する"""
    h, m, s = map(int, time_str.split(":"))
    return h * 60 + m


def process_stop_times(file_path, output_file):
    """stop_times.txtを解析し、停留所ペアごとの平均所要時間を算出"""
    stop_times = defaultdict(list)

    # データを読み込む
    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            trip_id = row["trip_id"]
            arrival_time = parse_time(row["arrival_time"])
            stop_id = row["stop_id"]
            stop_sequence = int(row["stop_sequence"])
            stop_times[trip_id].append((stop_id, arrival_time, stop_sequence))

    # 各trip_idごとに停留所ペアの所要時間を計算
    travel_times = defaultdict(list)

    for trip_id, stops in stop_times.items():
        stops.sort(key=lambda x: x[2])  # stop_sequenceでソート
        for i in range(len(stops)):
            for j in range(i + 1, len(stops)):
                stop_a, time_a, _ = stops[i]
                stop_b, time_b, _ = stops[j]
                travel_time = time_b - time_a
                travel_times[(stop_a, stop_b)].append(travel_time)

    # 平均所要時間を計算
    avg_travel_times = []
    for (stop_a, stop_b), times in travel_times.items():
        avg_time = sum(times) / len(times)
        avg_travel_times.append((stop_a, stop_b, round(avg_time, 2)))

    # ファイルに出力
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["stop_from", "stop_to", "average_travel_time"])
        writer.writerows(avg_travel_times)


if __name__ == "__main__":
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    input_file = input_dir + "/stop_times.txt"  # 読み込むGTFSファイル
    output_file = output_dir + "/average_travel_times.csv"  # 出力ファイル
    print(">>> バス停間の平均所要時間の計算を開始...")
    process_stop_times(input_file, output_file)
    print("<<< 完了しました。")
