import osmium
import sys
import csv
from math import floor
from geopy.distance import geodesic


def calculate_mesh_code(lat, lon):
    """3次メッシュコードを計算"""
    lat = float(lat)
    lon = float(lon)

    primary = floor(lat * 1.5) * 100 + floor(lon - 100)
    secondary = floor((lat * 60) % 40 / 5) * 10 + floor((lon * 60) % 60 / 7.5)
    tertiary = floor((lat * 3600) % 300 / 30) * 10 + floor((lon * 3600) % 450 / 45)

    return int(f"{primary}{secondary}{tertiary}")


class OSMHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.car_ways = []
        self.walk_ways = []

    def node(self, n):
        """ノード情報を取得"""
        self.nodes[n.id] = (
            n.location.lat,
            n.location.lon,
            calculate_mesh_code(n.location.lat, n.location.lon),
        )

    def way(self, w):
        """道路の種類を判別し、車両用・歩行者用に分ける"""
        highway = w.tags.get("highway", "")
        if not highway:
            return

        is_car = highway in {
            "motorway",
            "trunk",
            "primary",
            "secondary",
            "tertiary",
            "motorway_link",
            "trunk_link",
            "primary_link",
            "secondary_link",
            "tertiary_link",
        }

        is_walk = highway in {"footway", "pedestrian", "path", "steps", "cycleway"}

        way_nodes = [node.ref for node in w.nodes]
        segments = []

        for i in range(len(way_nodes) - 1):
            node1 = self.nodes.get(way_nodes[i])
            node2 = self.nodes.get(way_nodes[i + 1])
            if node1 and node2:
                segment_length = geodesic(
                    (node1[0], node1[1]), (node2[0], node2[1])
                ).meters
                segment_length = round(segment_length, 2)
                segments.append((way_nodes[i], way_nodes[i + 1], segment_length))

        for start_node, end_node, length in segments:
            way_data = {
                "start_node": start_node,
                "end_node": end_node,
                "length_m": length,
            }
            if is_car:
                self.car_ways.append(way_data)
            if is_walk:
                self.walk_ways.append(way_data)


def filter_nodes(nodes, ways):
    """ウェイに含まれるノードだけを抽出する"""
    used_nodes = {way["start_node"] for way in ways} | {way["end_node"] for way in ways}
    return {node_id: nodes[node_id] for node_id in used_nodes if node_id in nodes}


def renumber_ids(nodes, ways):
    """ノードIDを0から再採番"""
    node_id_map = {old_id: new_id for new_id, old_id in enumerate(nodes.keys())}

    new_nodes = {node_id_map[old_id]: coords for old_id, coords in nodes.items()}

    new_ways = []
    for way in ways:
        new_ways.append(
            {
                "start_node": node_id_map[way["start_node"]],
                "end_node": node_id_map[way["end_node"]],
                "length_m": way["length_m"],
            }
        )

    return new_nodes, new_ways


def write_csv(output_dir, nodes, ways, prefix):
    """CSVにデータを保存"""
    nodes_csv = f"{output_dir}/{prefix}_nodes.csv"
    ways_csv = f"{output_dir}/{prefix}_ways.csv"

    with open(nodes_csv, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ノード番号", "緯度", "経度", "3次メッシュID"])
        for node_id, (lat, lon, mesh_code) in nodes.items():
            writer.writerow([node_id, lat, lon, mesh_code])

    with open(ways_csv, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["出発地のノード番号", "到着側のノード番号", "ウェイの距離[m]"])
        for way in ways:
            writer.writerow([way["start_node"], way["end_node"], way["length_m"]])


def parse_osm_pbf(file_path):
    handler = OSMHandler()
    handler.apply_file(file_path)
    return handler.nodes, handler.car_ways, handler.walk_ways


if __name__ == "__main__":
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    pbf_file = f"{input_dir}/chubu-latest-filtered.osm.pbf"
    nodes, car_ways, walk_ways = parse_osm_pbf(pbf_file)

    car_nodes = filter_nodes(nodes, car_ways)
    walk_nodes = filter_nodes(nodes, walk_ways)

    car_nodes, car_ways = renumber_ids(car_nodes, car_ways)
    walk_nodes, walk_ways = renumber_ids(walk_nodes, walk_ways)

    write_csv(output_dir, car_nodes, car_ways, "car")
    write_csv(output_dir, walk_nodes, walk_ways, "walk")
