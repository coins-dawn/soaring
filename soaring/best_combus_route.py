import json


def load_combus_stops():
    with open("work/output/combus_stops.json", "r") as f:
        combus_stops_dict = json.load(f)
    return [combus_stop["id"] for combus_stop in combus_stops_dict["combus-stops"]]


def load_combus_distance_dict():
    with open("work/output/combus_routes.json", "r") as f:
        combus_routes_dict = json.load(f)
    return {
        (combus_route["from"], combus_route["to"]): combus_route["distance_km"]
        for combus_route in combus_routes_dict["combus-routes"]
    }


def main():
    # データのロード
    combus_stops = load_combus_stops()
    combus_distance_dict = load_combus_distance_dict()


if __name__ == "__main__":
    main()
