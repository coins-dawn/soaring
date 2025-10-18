#!/bin/bash

cd work/otp/output/
find geojson/ -type f -printf "%f\n" > all_geojsons.txt
zip -r geojson.zip geojson/*
cd -
