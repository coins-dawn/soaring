import sys
import json
import pickle


def convert_time_for_filename(start_time: str) -> str:
    """時刻をファイル名用の形式に変換（例: 10:00am -> 1000, 3:25pm -> 1525）"""
    is_pm = start_time.endswith("pm")
    time_part = start_time[:-2]  # "am"または"pm"を削除

    # 時間と分を分割
    hours_str, minutes = time_part.split(":")
    hours = int(hours_str)

    # pmの場合は時間に12を足す（ただし12pmは12時のまま）
    if is_pm and hours != 12:
        hours += 12
    elif not is_pm and hours == 12:  # 12amは00時
        hours = 0

    return f"{hours:02d}{minutes}"


def read_json(file_path: str, key_str: str) -> list[dict]:
    with open(file_path) as f:
        data = json.load(f)
        return data[key_str]


def main(
    input_spot_to_refpoints_path: str,
    input_spot_to_stops_path: str,
    input_stop_to_refpoints_path: str,
    output_all_routes_path: str,
    output_route_dir_path: str,
):
    spot_to_refpoints_list = read_json(
        input_spot_to_refpoints_path, "spot_to_refpoints"
    )
    spot_to_spots_list = read_json(input_spot_to_stops_path, "spot_to_stops")
    stop_to_refpoints_list = read_json(
        input_stop_to_refpoints_path, "stop_to_refpoints"
    )
    merged_list = spot_to_refpoints_list + spot_to_spots_list + stop_to_refpoints_list

    keypair_to_duration_dict = {}
    for elem in merged_list:
        from_key = elem["from"]
        to_key = elem["to"]
        duration = elem["duration_m"]
        walk_distance_m = elem["walk_distance_m"]
        start_time = elem["start_time"]
        keypair_to_duration_dict[(from_key, to_key, start_time)] = (
            duration,
            walk_distance_m,
        )

    with open(output_all_routes_path, "w", encoding="utf-8") as f:
        f.write("from,to,start_time,duration_m,walk_distance_m\n")
        for (from_key, to_key, start_time), (
            duration_m,
            walk_distance_m,
        ) in keypair_to_duration_dict.items():
            f.write(
                f"{from_key},{to_key},{start_time},{duration_m},{walk_distance_m}\n"
            )
    for elem in merged_list:
        from_key = elem["from"]
        to_key = elem["to"]
        start_time = elem["start_time"]
        start_time_formatted = convert_time_for_filename(start_time)
        file_path = (
            output_route_dir_path + f"/{from_key}_{to_key}_{start_time_formatted}.bin"
        )
        with open(file_path, "wb") as f:
            pickle.dump(elem, f)


if __name__ == "__main__":
    input_spot_to_refpoints_path = sys.argv[1]
    input_spot_to_stops_path = sys.argv[2]
    input_stop_to_refpoints_path = sys.argv[3]
    output_all_routes_path = sys.argv[4]
    output_route_dir_path = sys.argv[5]
    main(
        input_spot_to_refpoints_path,
        input_spot_to_stops_path,
        input_stop_to_refpoints_path,
        output_all_routes_path,
        output_route_dir_path,
    )
