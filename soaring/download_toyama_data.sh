#!/bin/bash

DSTDIR="$1"
TARGET_REGION_FILE="$2"

SOUTH_WEST=$(cat $TARGET_REGION_FILE | jq -r '."south-west" | [.lon, .lat] | join(",")')
NORTH_EAST=$(cat $TARGET_REGION_FILE | jq -r '."north-east" | [.lon, .lat] | join(",")')

mkdir -p $DSTDIR
rm $DSTDIR/*

### OSM ###

# 北陸全体のデータをダウンロード
curl -L https://download.geofabrik.de/asia/japan/chubu-latest.osm.pbf -o $DSTDIR/chubu-latest.osm.pbf

# 北陸全体から富山市周辺のみを抽出
docker build -t custom-osmium -f Dockerfile_filter_network .
docker run --rm \
  -v "$(pwd):/data" \
  custom-osmium \
  extract \
  --bbox=$SOUTH_WEST,$NORTH_EAST \
  -o $DSTDIR/chubu-latest-filtered.osm.pbf \
  $DSTDIR/chubu-latest.osm.pbf
rm $DSTDIR/chubu-latest.osm.pbf

### GTFS ###

# 富山地方鉄道バス
curl -L https://api.gtfs-data.jp/v2/organizations/chitetsu/feeds/chitetsubus/files/feed.zip?rid=current -o $DSTDIR/chitetsubus-gtfs.zip

# 富山地方鉄道市内電車
curl -L https://api.gtfs-data.jp/v2/organizations/chitetsu/feeds/chitetsushinaidensha/files/feed.zip?rid=current -o $DSTDIR/chitetsushinaidensha-gtfs.zip

# 婦中コミュニティバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/fuchucommunitybus/files/feed.zip?rid=current -o $DSTDIR/fuchucommunitybus-gtfs.zip

# 大山コミュニティバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/oyamacommunitybus/files/feed.zip?rid=current -o $DSTDIR/oyamacommunitybus-gtfs.zip

# 水橋ふれあいコミュニティバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/mizuhashifureaicommunitybus/files/feed.zip?rid=current -o $DSTDIR/mizuhashifureaicommunitybus-gtfs.zip

# 堀川南地域コミュニティバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/horikawaminamicommunitybus/files/feed.zip?rid=current -o $DSTDIR/horikawaminamicommunitybus-gtfs.zip

# 八尾コミュニティバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/yatsuocommunitybus/files/feed.zip?rid=current -o $DSTDIR/yatsuocommunitybus-gtfs.zip

# 呉羽いきいきバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/kurehaikiikibus/files/feed.zip?rid=current -o $DSTDIR/kurehaikiikibus-gtfs.zip

# 山田コミュニティバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/yamadacommunitybus/files/feed.zip?rid=current -o $DSTDIR/yamadacommunitybus-gtfs.zip

# 上条コミバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/jojocommunitybus/files/feed.zip?rid=current -o $DSTDIR/jojocommunitybus-gtfs.zip

# まいどはやバス
curl -L https://api.gtfs-data.jp/v2/organizations/toyamacity/feeds/maidohayabus/files/feed.zip?rid=current -o $DSTDIR/maidohayabus-gtfs.zip
