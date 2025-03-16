OSM_INPUT_DIR=osm/input/
OSM_OUTPUT_DIR=osm/output/

.PHONY: convert-osm
convert-osm:
	python soaring/convert_osm.py $(OSM_INPUT_DIR) $(OSM_OUTPUT_DIR)

