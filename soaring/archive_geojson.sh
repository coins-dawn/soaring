#!/bin/bash

cd work/output/
find geojson/ -type f -printf "%f\n" > all_geojsons.txt
zip -r geojson.zip geojson/*
cd -
