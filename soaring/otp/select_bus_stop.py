import json
import random
import sys


def main():
    # コマンドライン引数の確認
    if len(sys.argv) < 2:
        print("使用方法: python generate_stops.py <出力ファイルパス>")
        sys.exit(1)

    output_path = sys.argv[1]

    # 乱数シード設定（再現性をもたせる）
    random.seed(42)

    # 範囲を指定
    top_left = (36.73830582466276, 137.12149544206085)
    bottom_right = (36.60374523969972, 137.3029988825348)

    # 緯度・経度の最小値と最大値を取得
    min_lat, max_lat = bottom_right[0], top_left[0]
    min_lon, max_lon = top_left[1], bottom_right[1]

    # ランダムに50地点生成
    stops = []
    for i in range(1, 51):
        lat = random.uniform(min_lat, max_lat)
        lon = random.uniform(min_lon, max_lon)
        stops.append(
            {"id": f"comstop{i}", "name": f"バス停{i}", "lat": lat, "lon": lon}
        )

    # JSON形式に整形
    output = {"combus-stops": stops}

    # ファイルに出力
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"✅ {output_path} に書き出しました。")


if __name__ == "__main__":
    main()
