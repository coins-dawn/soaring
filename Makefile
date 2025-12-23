# 富山県のOTP用データをダウンロード
.PHONY: download
download:
	./soaring/download_toyama_data.sh work/input/ static/target_region.json

# 0.0.0.0:8080でotpサーバを起動
.PHONY: otp
otp:
	java -Xmx8G -jar soaring/otp-1.5.0-shaded.jar --build ./work/input --inMemory

# コンバートを通しで実行する
.PHONY: convert-all
convert-all: filter-mesh select-spots car-search ptrans-search area-search archive

# メッシュにフィルタをかける
.PHONY: filter-mesh
filter-mesh:
	mkdir -p work/output/archive/
	cp static/population-mesh.json work/input
	cp static/target_region.json work/input
	python soaring/filter_mesh.py \
		work/input/population-mesh.json \
		work/input/target_region.json \
		work/output/archive/mesh.json

.PHONY: generate-mesh
generate-mesh:
	mkdir -p work/output/archive/
	cp static/target_region.json work/input
	python soaring/generate_mesh.py \
		work/input/target_region.json \
		work/input/tblT001102Q06.txt \
		work/output/archive/mesh.json \
		work/output/mesh.kml

# スポット（コミュニティバスのバス停、ref-point）を選定する
.PHONY: select-spots
select-spots:
	mkdir -p work/output/archive/
	cp static/target_region.json work/input
	python soaring/select_bus_stop.py work/output/archive/combus_stops.json
	python soaring/select_ref_points.py \
		work/input/target_region.json \
		work/output/archive/mesh.json \
		work/output/archive/ref_points.json \
		work/output/ref_points.kml \

# 車経路探索を行いコミュニティバスの経路を計算
.PHONY: car-search
car-search:
	mkdir -p work/output/archive/
	python soaring/car_search.py work/output/archive/combus_stops.json work/output/archive/

# 公共交通探索を行いスポット->バス停の経路を計算
.PHONY: ptrans-search
ptrans-search:
	mkdir -p work/output/archive/route
	python soaring/ptrans_search.py \
		work/input/toyama_spot_list.json \
		work/output/archive/combus_stops.json \
		work/output/archive/ref_points.json \
		work/output/
	python soaring/edit_routes.py \
		work/output/spot_to_refpoints.json \
		work/output/spot_to_stops.json \
		work/output/stop_to_refpoints.json \
		work/output/archive/all_routes.csv \
		work/output/archive/route

# 到達圏探索を行いgeojsonを生成
.PHONY: area-search
area-search:
	cp static/toyama_spot_list.json work/input/toyama_spot_list.json
	mkdir -p work/output/archive/geojson work/output/geojson_txt
	python soaring/area_search.py \
		work/output/archive/combus_stops.json \
		work/input/toyama_spot_list.json \
		work/output/archive/mesh.json \
		work/output/archive/geojson \
		work/output/geojson_txt
	find work/output/archive/geojson/ -type f -printf "%f\n" > work/output/archive/all_geojsons.txt

# 生成されたファイルたちをアーカイブする
.PHONY: archive
archive:
	cp static/toyama_spot_list.json work/output/archive/
	cp static/target_region.json work/output/archive/
	cd work/output/archive && zip -q -r ../archive.zip ./*
