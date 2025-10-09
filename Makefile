OSM_INPUT_DIR=osm/input/
OSM_OUTPUT_DIR=osm/output/
GTFS_INPUT_DIR=gtfs/input/
GTFS_OUTPUT_DIR=gtfs/output/

.PHONY: convert-osm
convert-osm:
	python soaring/osm/convert.py $(OSM_INPUT_DIR) $(OSM_OUTPUT_DIR)

.PHONY: convert-gtfs
convert-gtfs:
	python soaring/gtfs/convert_transit_times.py $(GTFS_INPUT_DIR) $(GTFS_OUTPUT_DIR)
	python soaring/gtfs/convert_shapes.py $(GTFS_INPUT_DIR) $(GTFS_OUTPUT_DIR)

.PHONY: download
download:
	./soaring/otp/download_toyama_data.sh work/otp/input/

# 0.0.0.0:8080でotpサーバを起動
.PHONY: otp
otp:
	java -Xmx3G -jar soaring/otp/otp-1.5.0-shaded.jar --build ./work/otp/input --inMemory

# 到達圏探索を行いgeojsonを生成
.PHONY: area-search
area-search:
	# バス停
	python soaring/otp/select_bus_stop.py work/otp/output/combus_stops.json
	python soaring/otp/area_search.py work/otp/output/combus_stops.json work/otp/output/geojson/
	# spot
	cp static/otp/area_search/toyama_spot_list.json work/otp/input/toyama_spot_list.json
	python soaring/otp/area_search.py work/otp/input/toyama_spot_list.json work/otp/output/geojson/

# 車経路探索を行いコミュニティバスの経路を計算
.PHONY: car-search
car-search:
	python soaring/otp/car_search.py work/otp/output/combus_stops.json work/otp/output/

# 公共交通探索を行いスポット->バス停の経路を計算
.PHONY: ptrans-search
ptrans-search:
	python soaring/otp/ptrans_search.py work/otp/input/toyama_spot_list.json work/otp/output/combus_stops.json work/otp/output/
