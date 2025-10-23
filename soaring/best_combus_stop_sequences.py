import json
import os


def load_combus_stops():
    with open("work/output/combus_stops.json", "r") as f:
        combus_stops_dict = json.load(f)
    return [combus_stop["id"] for combus_stop in combus_stops_dict["combus-stops"]]


def load_combus_duration_dict():
    with open("work/output/combus_routes.json", "r") as f:
        combus_routes_dict = json.load(f)
    return {
        (combus_route["from"], combus_route["to"]): combus_route["duration_m"]
        for combus_route in combus_routes_dict["combus-routes"]
    }


def load_spot_dict():
    with open("work/input/toyama_spot_list.json", "r") as f:
        return json.load(f)


def generate_combus_stop_sequence(
    combus_stops: list[str],
    combus_duration_dict: dict[tuple[str, str], int],
    duration_limit: int,
) -> list[str]:
    return []


def best_combus_stops_for_single_duration_limit(
    combus_stops: list[str],
    combus_duration_dict: dict[tuple[str, str], int],
    duration_limit: int,
    spot_type: str,
) -> list[str]:
    combus_stop_sequence = generate_combus_stop_sequence(
        combus_stops, combus_duration_dict, duration_limit
    )

    return []


def write_best_combus_stop_sequences(best_combus_sequences: dict, output_path: str):
    output_data = {"best-combus-stop-sequences": []}
    for best_combus_sequence in best_combus_sequences:
        output_data["best-combus-stop-sequences"].append(best_combus_sequence)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)


def main():
    # データのロード
    combus_stops = load_combus_stops()
    combus_duration_dict = load_combus_duration_dict()
    spot_dict = load_spot_dict()

    best_combus_stop_sequences = []
    for spot_type, _ in spot_dict.items():
        # 30分から10分刻みで2時間まで
        combus_duration_limits = list(range(30, 121, 10))
        for combus_duration_limit in combus_duration_limits:
            best_combus_stop_sequence = best_combus_stops_for_single_duration_limit(
                combus_stops, combus_duration_dict, combus_duration_limit, spot_type
            )
            best_combus_stop_sequences.append(
                {
                    "spot-type": spot_type,
                    "duration-limit-m": combus_duration_limit,
                    "stop-sequence": best_combus_stop_sequence,
                }
            )

    write_best_combus_stop_sequences(
        best_combus_stop_sequences, "work/output/best_combus_stop_sequences.json"
    )


if __name__ == "__main__":
    main()
