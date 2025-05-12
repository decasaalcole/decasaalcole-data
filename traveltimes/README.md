# OSRM routing for De Casa al Cole

This repo contains the resources to compute the travel times for the project.

## Requirements

Docker and Docker Compose

## Set up the routing engine

All the definitions live in the compose file and only the routing server is expected to run indefinitely.

1. Put in the `.env` file the parameters for your execution:
   * The region you want to work with as per the `geofabrik` [identifiers](https://download.geofabrik.de/europe/spain.html). Defaults to Comunitat Valenciana as this project geographical context.
   * The number of threads to make requests against OSRM in your instance
   * The input and output files
   * The parameters in the input file where the id (`codigo_postal`), latitude, and longitude are defined
2. Download the images and build the local image to get the travel times
```
docker compose pull && docker compose build
```

3. Download the dataset. A `data` folder should end up with the `pbf` file.

```
docker compose run download-osm | tee data/travel_times_osm_pbf.log
```

4. Process the OSM data for OSRM. A bunch of datasets should be generated in the `data` folder.

```
docker compose run osrm-prepare | tee data/travel_times_osrm.log
```

5. Start the routing engine

```
docker compose up -d osrm
```

To test the server, pick a couple points with <http://bboxfinder.com> and check the results, for example:

```bash
curl -s "http://127.0.0.1:5000/route/v1/driving/0.479150,40.475022;-0.373020,39.468867" | jq '.routes[] | { duration:.duration, distance:.distance }'
```
```json
{
  "duration": 6390.5,
  "distance": 151124.1
}
```

## Compute the travel times

With the routing engine ready, you can execute the Python script that iterates over all the postcodes in the input file to generate an output with all the combinations, the duration, and the distance of the traveling time between the pair of coordinates.

The script is also defined in the `docker-compose.yaml`. You can view the parameters with the following command:

```bash
docker compose run travel_times --help
```
```text
usage: travel_times.py [-h] [--loglevel LOGLEVEL] [--threads THREADS] [--force] [--input INPUT] [--output OUTPUT] [--id ID] [--lat LAT]
                       [--lon LON] [--osrm OSRM] [--subset SUBSET]

Get travel times from OSRM API.

options:
  -h, --help            show this help message and exit
  --loglevel LOGLEVEL, -l LOGLEVEL
                        Logging level for the script. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL. Default INFO.
  --threads THREADS     Number of threads to use for parallel requests. Default 5.
  --force               Force the script to run even if the output file already exists. Default True.
  --input INPUT         Path to the input CSV file with latitude and longitude coordinates. Default data/postcodes.csv.
  --output OUTPUT       Path to the output CSV file to save the results. Default data/travel_times.csv.
  --id ID               Field in the CSV file that contains the identifier for the origin. Default codigo_postal.
  --lat LAT             Field in the CSV file that contains the latitude coordinates. Default lat.
  --lon LON             Field in the CSV file that contains the longitude coordinates. Default lon.
  --osrm OSRM           URL of the OSRM API server. Default http://osrm:5000.
  --subset SUBSET       Optional argument to process only a subset of the data. Default 0.
```

The help message shows the defaults, modified also by the environment variables in the compose file.

To test the execution you can run the following command to only process the first 5 postal codes:

```bash
docker compose run travel-times --subset 2
```
```text
15:50:00 - INFO - Starting travel time calculation...
15:50:00 - INFO - Read 641 rows from the input file.
15:50:00 - WARNING - Output file data/travel_times.csv already exists. It will be overwritten.
15:50:00 - INFO - Filtered 625 rows with valid lat/lon coordinates.
15:50:00 - INFO - Sorted 625 rows by the id field.
15:50:01 - INFO - Created 195000 permutations of the data.
15:50:01 - INFO - Using 5 threads for parallel requests.
15:50:01 - INFO - Processing only the first 1 postal codes.
15:50:32 - INFO - Processed 624 requests.
15:50:32 - INFO - Finished sending requests.
15:50:32 - INFO - Received 624 results.
15:50:32 - INFO - Results written to data/travel_times.csv.
15:50:32 - INFO - First 10 results:
15:50:32 - INFO - Result: ('03001', '03002', 197.5, 1040.7, 382.3, 2736.2)
15:50:32 - INFO - Result: ('03001', '03003', 108.3, 686, 102.6, 769.4)
15:50:32 - INFO - Result: ('03001', '03004', 120.8, 899.7, 120.7, 911)
15:50:32 - INFO - Result: ('03001', '03005', 191.6, 1893.1, 239, 1751.8)
15:50:32 - INFO - Result: ('03001', '03006', 319.3, 3141.2, 353.8, 3147.5)
15:50:32 - INFO - Result: ('03001', '03007', 266.4, 2609, 269.1, 2410.7)
15:50:32 - INFO - Result: ('03001', '03008', 399.1, 3801.4, 419.8, 3574.2)
15:50:32 - INFO - Result: ('03001', '03009', 386.6, 4212.1, 347.3, 3519.5)
15:50:32 - INFO - Result: ('03001', '03010', 339, 2467.5, 277.7, 2121.4)
15:50:32 - INFO - Result: ('03001', '03011', 496.1, 4912.2, 422.7, 3973.2)
```

The requests are cached in a SQLite database stored in the `data` folder. For this reason, executing the previous command a second time will finish almost immediately.

Finally, to execute the computation of the full dataset, just run:

```bash
docker compose run travel-times 2>&1 | tee data/travel_times.log
```

While running, you may want to check:

* Logs of the server can be inspected as `docker compose logs -f osrm`
* Number of responses stored in the cache with `sqlite3 data/travel_times_cache.sqlite "select count(1) from responses"`

## Results

When the `travel-times` scripts finish, the results are stored in a CSV file located by default at `data/travel_times.csv` with the following schema representing the travel times and distances of the forward and backward routes:

* `cp_from`
* `cp_dist`
* `from_time` and `to_time` in minutes
* `from_dist` and `to_dist` in kilometers

```text
$ head data/travel_times.csv | csvlook -I
| cp_from | cp_to | from_time | from_dist | to_time | to_dist |
| ------- | ----- | --------- | --------- | ------- | ------- |
| 03001   | 03002 | 3         | 1         | 6       | 3       |
| 03001   | 03003 | 2         | 1         | 2       | 1       |
| 03001   | 03004 | 2         | 1         | 2       | 1       |
| 03001   | 03005 | 3         | 2         | 4       | 2       |
| 03001   | 03006 | 5         | 3         | 6       | 3       |
| 03001   | 03007 | 4         | 3         | 4       | 2       |
| 03001   | 03008 | 7         | 4         | 7       | 4       |
| 03001   | 03009 | 6         | 4         | 6       | 4       |
| 03001   | 03010 | 6         | 2         | 5       | 2       |
```

All the assets are stored in the `data` folder but these are probably the ones you should store somewhere for archival purposes

```
ls -lh data/travel_times*
```
```text
-rw-r--r-- 1 j    j    809M may  4 18:33 data/travel_times_cache.sqlite
-rw-r--r-- 1 j    j    5,1M may  4 21:24 data/travel_times.csv
-rw-r--r-- 1 root root  854 may  4 21:24 data/travel_times.json
-rw-rw-r-- 1 j    j    2,8K may  4 21:24 data/travel_times.log
-rw-r--r-- 1 j    j     107 may  4 21:02 data/travel_times_osm_pbf.json
-rw-rw-r-- 1 j    j     491 may  4 21:01 data/travel_times_osm_pbf.log
-rw-r--r-- 1 j    j      78 may  4 21:02 data/travel_times_osrm.json
-rw-rw-r-- 1 j    j     15K may  4 21:02 data/travel_times_osrm.log
```

To tear down all resources and potential orphan containers remember to run:

```
docker compose down --remove-orphans
```
