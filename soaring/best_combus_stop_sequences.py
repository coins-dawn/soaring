import json
import random
from itertools import combinations
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

random.seed(42)

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
        return None, float('inf')

    # 解の取得
    route = []
    index = routing.Start(0)
    total_distance = 0
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        total_distance += duration_matrix[manager.IndexToNode(previous_index)][manager.IndexToNode(index)]
    route.append(manager.IndexToNode(index))
    assert(route)
    
    return route, total_distance


def create_duration_matrix(stops, duration_dict):
    """所要時間の行列を作成"""
    n = len(stops)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = duration_dict.get((stops[i], stops[j]), float('inf'))
    return matrix


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


def generate_combus_stop_sequence_list(
    combus_stops: list[str],
    combus_duration_dict: dict[tuple[str, str], int],
    duration_limit: int,
) -> list[list[str]]:
    candidate_sequences_list = []
    bus_stop_num_min = duration_limit // 20
    bus_stop_num_max = bus_stop_num_min * 2
    while len(candidate_sequences_list) < 100:
        sequence_size = random.randint(bus_stop_num_min, bus_stop_num_max)
        current_stops = random.sample(combus_stops, sequence_size)
        duration_matrix = create_duration_matrix(current_stops, combus_duration_dict)
        route, total_duration = solve_tsp(duration_matrix)
        if total_duration <= duration_limit:
            sequence = [current_stops[i] for i in route[:-1]]
            candidate_sequences_list.append(sequence)
    return candidate_sequences_list


def best_combus_stops_for_single_duration_limit(
    combus_stops: list[str],
    combus_duration_dict: dict[tuple[str, str], int],
    duration_limit: int,
    spot_type: str,
) -> list[str]:
    combus_stop_sequence_list = generate_combus_stop_sequence_list(
        combus_stops, combus_duration_dict, duration_limit
    )
    print(len(combus_stop_sequence_list))

    return combus_stop_sequence_list[0]


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
        # 60分から10分刻みで2時間まで
        combus_duration_limits = list(range(60, 121, 10))
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
