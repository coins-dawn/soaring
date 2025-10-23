SOUTH_WEST=137.05662344824745,36.550071366242115
NORTH_EAST=137.3963186386241,36.79659576973084


# 富山県のOTP用データをダウンロード
.PHONY: download
download:
	./soaring/download_toyama_data.sh work/input/ $(SOUTH_WEST) $(NORTH_EAST)

# 0.0.0.0:8080でotpサーバを起動
.PHONY: otp
otp:
	java -Xmx3G -jar soaring/otp-1.5.0-shaded.jar --build ./work/input --inMemory

.PHONY: convert-all
convert-all: select-bus-stops area-search geojson-properties car-search ptrans-search

# コミュニティバスのバス停を選定する
.PHONY: select-bus-stops
select-bus-stops:
	python soaring/select_bus_stop.py work/output/combus_stops.json

# 到達圏探索を行いgeojsonを生成
.PHONY: area-search
area-search:
	cp static/population-mesh.json work/input/population-mesh.json
	cp static/toyama_spot_list.json work/input/toyama_spot_list.json
	mkdir -p work/output/geojson work/output/geojson_txt
	python soaring/area_search.py \
		work/output/combus_stops.json \
		work/input/toyama_spot_list.json \
		work/input/population-mesh.json \
		work/output/geojson \
		work/output/geojson_txt \
		work/output/mesh.json
	./soaring/archive_geojson.sh

# 車経路探索を行いコミュニティバスの経路を計算
.PHONY: car-search
car-search:
	python soaring/car_search.py work/output/combus_stops.json work/output/

# 公共交通探索を行いスポット->バス停の経路を計算
.PHONY: ptrans-search
ptrans-search:
	python soaring/ptrans_search.py \
		work/input/toyama_spot_list.json \
		work/output/combus_stops.json \
		work/output/
