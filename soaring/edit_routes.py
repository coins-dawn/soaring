import sys
import json
import pickle


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
        keypair_to_duration_dict[(from_key, to_key)] = (duration, walk_distance_m)

    with open(output_all_routes_path, "w", encoding="utf-8") as f:
        f.write("from,to,duration_m,walk_distance_m\n")
        for (from_key, to_key), (
            duration_m,
            walk_distance_m,
        ) in keypair_to_duration_dict.items():
            f.write(f"{from_key},{to_key},{duration_m},{walk_distance_m}\n")

    for elem in merged_list:
        from_key = elem["from"]
        to_key = elem["to"]
        file_path = output_route_dir_path + f"/{from_key}_{to_key}.bin"
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
