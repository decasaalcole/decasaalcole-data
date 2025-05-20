#!/usr/bin/env sh

set -eu

# Check if a parameter has been passed
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <region>"
  exit 1
fi

REGION=$1
if [ -z "$REGION" ]; then
  echo "Usage: $0 <region>"
  exit 1
fi
if [ ! -f "/data/${REGION}-latest.osm.pbf" ]; then
  echo "OSM PBF file not found: /data/${REGION}-latest.osm.pbf"
  exit 1
fi
if [ ! -f "/opt/car.lua" ]; then
  echo "Lua profile not found: /opt/car.lua"
  exit 1
fi

# Get the timestamp of the OSM PBF file
OSM_PBF_TIMESTAMP=$(stat -c %y /data/${REGION}-latest.osm.pbf | cut -d'.' -f1)
if [ -z "$OSM_PBF_TIMESTAMP" ]; then
  echo "Failed to get timestamp of the OSM PBF file"
  exit 1
fi

# Compute the size of the OSM PBF file
OSM_PBF_SIZE=$(stat -c %s /data/${REGION}-latest.osm.pbf)

# Compute md5sum of the OSM PBF file
OSM_PBF_MD5=$(md5sum /data/${REGION}-latest.osm.pbf | awk '{print $1}')
if [ -z "$OSM_PBF_MD5" ]; then
  echo "Failed to compute md5sum of the OSM PBF file"
  exit 1
fi

# Write the OSM PBF file information to a JSON file
OSM_PBF_INFO_FILE="/data/travel_times_osm_pbf.metadata.json"
cat <<EOF > $OSM_PBF_INFO_FILE
{
  "timestamp": "$OSM_PBF_TIMESTAMP",
  "size": $OSM_PBF_SIZE,
  "md5": "$OSM_PBF_MD5"
}
EOF
if [ ! -f $OSM_PBF_INFO_FILE ]; then
  echo "Failed to write OSM PBF file information to JSON file"
  exit 1
fi

# Prepare the OSM PBF file for OSRM
osrm-extract -p /opt/car.lua /data/${REGION}-latest.osm.pbf 
osrm-partition /data/${REGION}-latest.osrm
osrm-customize /data/${REGION}-latest.osrm

# Check if the OSRM files were created successfully
OSRM_FILES=$(ls /data/${REGION}-latest.osrm* 2>/dev/null | wc -l)
if [ "$OSRM_FILES" -eq 0 ]; then
  echo "Failed to create OSRM files"
  exit 1
fi

# Get the total size of the OSRM files
OSRM_FILES_SIZE=$(du -c /data/${REGION}-latest.osrm* | grep total | awk '{print $1}')
if [ -z "$OSRM_FILES_SIZE" ]; then
  echo "Failed to compute size of the OSRM files"
  exit 1
fi

# Store the OSRM results in a JSON file
OSRM_INFO_FILE="/data/travel_times_osrm.metadata.json"
cat <<EOF > $OSRM_INFO_FILE
{
  "timestamp": "$OSM_PBF_TIMESTAMP",
  "files": "$OSRM_FILES",
  "size": "$OSRM_FILES_SIZE"
}
EOF
if [ ! -f $OSRM_INFO_FILE ]; then
  echo "Failed to write OSRM file information to JSON file"
  exit 1
fi

echo "-----------------------------------------"
echo "Results:"
echo "$OSM_PBF_INFO_FILE"
cat $OSM_PBF_INFO_FILE
echo "$OSRM_INFO_FILE"
cat $OSRM_INFO_FILE
echo "-----------------------------------------"
