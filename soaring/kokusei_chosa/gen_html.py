import pandas as pd
import folium
from jpmesh import parse_mesh_code

# CSVファイルの読み込み
df = pd.read_csv("over60.csv")


# 中心座標・ポリゴン情報の算出
def meshcode_to_bounds(code):
    mesh = parse_mesh_code(str(code))
    sw = mesh.south_west
    size = mesh.size
    lat_min = sw.lat.degree
    lon_min = sw.lon.degree
    lat_max = lat_min + size.lat.degree
    lon_max = lon_min + size.lon.degree

    bounds = [
        [lat_min, lon_min],
        [lat_min, lon_max],
        [lat_max, lon_max],
        [lat_max, lon_min],
    ]
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    return center_lat, center_lon, bounds


# 中心とポリゴンの情報をDataFrameに追加
bounds_data = df["mesh_key"].map(meshcode_to_bounds)
df["lat"], df["lon"], df["bounds"] = zip(*bounds_data)

# foliumマップの中心
map_center = [df["lat"].iloc[0], df["lon"].iloc[0]]
m = folium.Map(location=map_center, zoom_start=15, tiles="OpenStreetMap")

# 最大値で色調整
max_pop = df["over60_population"].max()


def get_color(value):
    if value == 0:
        return "#ffffff00"
    ratio = value / max_pop
    r = 255
    g = int(255 * (1 - ratio))
    b = 0
    return f"#{r:02x}{g:02x}{b:02x}"


# 描画
for _, row in df.iterrows():
    color = get_color(row["over60_population"])
    folium.Polygon(
        locations=row["bounds"],
        color=color,
        fill_color=color,
        fill=True,
        fill_opacity=0.7,
        weight=0,
    ).add_to(m)

# 保存
m.save("heatmap_pyjpmesh_full.html")
