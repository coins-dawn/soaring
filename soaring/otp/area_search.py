import sys
import json


def exec_single_spot(spot: dict):
    pass


def exec_single_category(category_name: str, spot_list: list):
    for spot in spot_list:
        exec_single_spot(spot)


def main(area_search_json_path, output_dir_path):
    with open(area_search_json_path, "r") as f:
        area_search_json = json.load(f)

    for category_name, spot_list in area_search_json.items():
        exec_single_category(category_name, spot_list)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python area_search.py <arg1> <arg2>")
        sys.exit(1)

    area_search_json_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    main(area_search_json_path, output_dir_path)
