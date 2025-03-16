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
