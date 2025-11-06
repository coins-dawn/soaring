# 富山県のOTP用データをダウンロード
.PHONY: download
download:
	./soaring/download_toyama_data.sh work/input/ static/target_region.json

# 0.0.0.0:8080でotpサーバを起動
.PHONY: otp
otp:
	java -Xmx3G -jar soaring/otp-1.5.0-shaded.jar --build ./work/input --inMemory

# コンバートを通しで実行する
.PHONY: convert-all
convert-all: select-spots area-search car-search ptrans-search best-combus-stop-sequences archive

# スポット（コミュニティバスのバス停、ref-point）を選定する
.PHONY: select-spots
select-spots:
	mkdir -p work/output/archive/
	cp static/target_region.json work/input
	python soaring/select_bus_stop.py work/output/archive/combus_stops.json
	python soaring/select_ref_points.py \
		work/input/target_region.json \
		work/output/archive/select_ref_points.csv \
		work/output/select_ref_points.kml \


# 到達圏探索を行いgeojsonを生成
.PHONY: area-search
area-search:
	cp static/population-mesh.json work/input/population-mesh.json
	cp static/toyama_spot_list.json work/input/toyama_spot_list.json
	mkdir -p work/output/archive/geojson work/output/geojson_txt
	python soaring/area_search.py \
		work/output/archive/combus_stops.json \
		work/input/toyama_spot_list.json \
		work/input/population-mesh.json \
		work/output/archive/geojson \
		work/output/geojson_txt \
		work/output/archive/mesh.json
	find work/output/archive/geojson/ -type f -printf "%f\n" > work/output/archive/all_geojsons.txt

# 車経路探索を行いコミュニティバスの経路を計算
.PHONY: car-search
car-search:
	mkdir -p work/output/archive/
	python soaring/car_search.py work/output/archive/combus_stops.json work/output/archive/

# 公共交通探索を行いスポット->バス停の経路を計算
.PHONY: ptrans-search
ptrans-search:
	mkdir -p work/output/archive/
	python soaring/ptrans_search.py \
		work/input/toyama_spot_list.json \
		work/output/archive/combus_stops.json \
		work/output/archive/

# 最適なコミュニティバス巡回経路を作成する
.PHONY: best-combus-stop-sequences
best-combus-stop-sequences:
	python soaring/best_combus_stop_sequences.py \
		work/output/archive/combus_stops.json \
		work/output/archive/combus_routes.json \
		work/input/toyama_spot_list.json \
		work/output/archive/best_combus_stop_sequences.json

# 生成されたファイルたちをアーカイブする
.PHONY: archive
archive:
	cp static/toyama_spot_list.json work/output/archive/
	cp static/target_region.json work/output/archive/
	cd work/output/archive && zip -q -r ../archive.zip ./*
