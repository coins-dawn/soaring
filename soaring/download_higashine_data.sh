#!/bin/bash

set -eux

DSTDIR="$1"
TARGET_REGION_FILE="$2"

SOUTH_WEST=$(cat $TARGET_REGION_FILE | jq -r '."south-west" | [.lon, .lat] | join(",")')
NORTH_EAST=$(cat $TARGET_REGION_FILE | jq -r '."north-east" | [.lon, .lat] | join(",")')

mkdir -p $DSTDIR
rm -rf $DSTDIR/*

### MESH ###
# e-statから山形県のメッシュデータをダウンロード
MESH_URL="https://www.e-stat.go.jp/gis/statmap-search/data?statsId=T001102&code=06&downloadType=2"
MESH_FILE="$DSTDIR/mesh_yamagata.zip"

curl -L -o "$MESH_FILE" "$MESH_URL"
unzip -o "$MESH_FILE" -d "$DSTDIR"

### OSM ###
curl -L https://download.geofabrik.de/asia/japan/tohoku-latest.osm.pbf -o $DSTDIR/tohoku-latest.osm.pbf
docker run --rm \
  -v "$(pwd):/data" \
  custom-osmium \
  extract \
  --bbox=$SOUTH_WEST,$NORTH_EAST \
  -o $DSTDIR/tohoku-latest-filtered.osm.pbf \
  $DSTDIR/tohoku-latest.osm.pbf
rm $DSTDIR/tohoku-latest.osm.pbf

### GTFS ###
# 東根市営バス
curl -L https://api.gtfs-data.jp/v2/organizations/higashinecity/feeds/HigashineCity/files/feed.zip?rid=current -o $DSTDIR/higashine_city-gtfs.zip
