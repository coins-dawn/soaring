import json
import sys
import random
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

random.seed(42)

TRYAL_NUM_PER_SETTING = 100  # 一つの設定ごとの試行回数


def solve_tsp(duration_matrix):
    """OR-toolsを使用して巡回セールスマン問題を解く"""
    manager = pywrapcp.RoutingIndexManager(len(duration_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def duration_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return duration_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(duration_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return None, float("inf")

    # 解の取得
    route = []
    index = routing.Start(0)
    total_distance = 0
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        total_distance += duration_matrix[manager.IndexToNode(previous_index)][
            manager.IndexToNode(index)
        ]
    route.append(manager.IndexToNode(index))
    assert route

    return route, total_distance


def create_duration_matrix(stops, duration_dict):
    """所要時間の行列を作成"""
    n = len(stops)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = duration_dict.get((stops[i], stops[j]), float("inf"))
    return matrix


def load_combus_stops(input_combus_stops_file: str):
    with open(input_combus_stops_file, "r") as f:
        combus_stops_dict = json.load(f)
    return [combus_stop["id"] for combus_stop in combus_stops_dict["combus-stops"]]


def load_combus_duration_dict(input_combus_routes_file: str):
    with open(input_combus_routes_file, "r") as f:
        combus_routes_dict = json.load(f)
    return {
        (combus_route["from"], combus_route["to"]): combus_route["duration_m"]
        for combus_route in combus_routes_dict["combus-routes"]
    }


def load_spot_dict(input_toyama_spot_list_file: str):
    with open(input_toyama_spot_list_file, "r") as f:
        return json.load(f)


def generate_combus_stop_sequence_list(
    combus_stops: list[str],
    combus_duration_dict: dict[tuple[str, str], int],
    duration_limit: int,
) -> list[list[str]]:
    candidate_sequences_list = []
    bus_stop_num_min = duration_limit // 20
    bus_stop_num_max = bus_stop_num_min * 2
    while len(candidate_sequences_list) < TRYAL_NUM_PER_SETTING:
        sequence_size = random.randint(bus_stop_num_min, bus_stop_num_max)
        current_stops = random.sample(combus_stops, sequence_size)
        duration_matrix = create_duration_matrix(current_stops, combus_duration_dict)
        route, total_duration = solve_tsp(duration_matrix)
        if total_duration <= duration_limit:
            sequence = [current_stops[i] for i in route[:-1]]
            candidate_sequences_list.append(sequence)
    return candidate_sequences_list


def request_to_prometheus(combus_stop_sequence: list[str], spot_type: str):
    request_body = {
        "target-spots": [spot_type],
        "max-minute": 60,  # TODO: ここもパラメタにする
        "combus-stops": combus_stop_sequence,
    }

    try:
        response = requests.post(
            "http://127.0.0.1:8000/area/search",
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except Exception as e:
        print("prometheusとの通信に失敗しました。")
        print(e)
        return None

    if response.status_code != 200:
        print("prometheusから返却されたステータスコードが200以外です。")
        print(response.json())
        return None

    return response.json()


def best_combus_stops_for_single_duration_limit(
    combus_stops: list[str],
    combus_duration_dict: dict[tuple[str, str], int],
    duration_limit: int,
    spot_type: str,
) -> list[str]:
    combus_stop_sequence_list = generate_combus_stop_sequence_list(
        combus_stops, combus_duration_dict, duration_limit
    )

    best_score = -1
    best_stop_sequence = None
    for combus_stop_sequence in combus_stop_sequence_list:
        response_json = request_to_prometheus(combus_stop_sequence, spot_type)
        if not response_json:
            continue
        score = response_json["result"]["area"][spot_type]["reachable"][
            "with-combus-score"
        ]
        if score > best_score:
            best_score = score
            best_stop_sequence = combus_stop_sequence

    return best_stop_sequence, best_score


def write_best_combus_stop_sequences(best_combus_sequences: dict, output_path: str):
    output_data = {"best-combus-stop-sequences": []}
    for best_combus_sequence in best_combus_sequences:
        output_data["best-combus-stop-sequences"].append(best_combus_sequence)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)


def main(
    input_combus_stops_file: str,
    input_combus_routes_file: str,
    input_toyama_spot_list_file: str,
    output_best_combus_stop_sequences_file: str,
):
    # データのロード
    combus_stops = load_combus_stops(input_combus_stops_file)
    combus_duration_dict = load_combus_duration_dict(input_combus_routes_file)
    spot_dict = load_spot_dict(input_toyama_spot_list_file)

    # 60分から10分刻みで2時間まで
    combus_duration_limits = list(range(60, 121, 10))
    spot_type_duration_limit_list = [
        (spot_type, duration_limit)
        for spot_type in spot_dict.keys()
        for duration_limit in combus_duration_limits
    ]

    best_combus_stop_sequences = []
    total = len(spot_type_duration_limit_list)
    for i, (spot_type, combus_duration_limit) in enumerate(
        spot_type_duration_limit_list
    ):
        best_combus_stop_sequence, score = best_combus_stops_for_single_duration_limit(
            combus_stops, combus_duration_dict, combus_duration_limit, spot_type
        )
        best_combus_stop_sequences.append(
            {
                "spot-type": spot_type,
                "duration-limit-m": combus_duration_limit,
                "stop-sequence": best_combus_stop_sequence,
                "score": score,
            }
        )
        # 進捗を表示
        progress = (i / total) * 100
        print(
            f"Progress: {progress:.1f}% ({i}/{total}) - {spot_type} {combus_duration_limit}min",
            end="\r",
        )
    print()

    write_best_combus_stop_sequences(
        best_combus_stop_sequences, output_best_combus_stop_sequences_file
    )


if __name__ == "__main__":
    input_combus_stops_file = sys.argv[1]
    input_combus_routes_file = sys.argv[2]
    input_toyama_spot_list_file = sys.argv[3]
    output_best_combus_stop_sequences_file = sys.argv[4]
    main(
        input_combus_stops_file,
        input_combus_routes_file,
        input_toyama_spot_list_file,
        output_best_combus_stop_sequences_file,
    )
