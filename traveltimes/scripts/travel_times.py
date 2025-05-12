"""
This is a script to traverse a given CSV file with latitude and lonitude
coordinates and sends a request to a local OSRM API server to get the
duration and distance of the route between a given origin and the rest of
destinations from the CSV file. It stores the results in a new CSV file with
the same name as the input file but with a "_results" suffix.
"""

import logging
import os
import csv
import argparse
import json

import requests
from requests_cache import SQLiteCache, CachedSession

# Set up a cache for the requests to avoid sending the same request multiple times
backend = SQLiteCache("data/travel_times_cache.sqlite")
session = CachedSession(backend=backend)

# Define arguments with argparse
parser = argparse.ArgumentParser(description="Get travel times from OSRM API.")

defaults = {
    "loglevel": os.environ.get("LOGLEVEL", "INFO"),
    "threads": os.environ.get("THREADS", 3),
    "force": os.environ.get("FORCE", "false").lower() == "true",
    "input": os.environ.get("INPUT", "data/postcodes.csv"),
    "output": os.environ.get("OUTPUT", "data/travel_times.csv"),
    "id": os.environ.get("ID_FIELD", "codigo_postal"),
    "lat": os.environ.get("LAT_FIELD", "lat"),
    "lon": os.environ.get("LON_FIELD", "lon"),
    "osrm": os.environ.get("OSRM_URL", "http://localhost:5000"),
    "subset": os.environ.get("SUBSET", 0),
}

# Logging level for the script
parser.add_argument(
    "--loglevel",
    "-l",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    metavar="LOGLEVEL",
    default=defaults["loglevel"],
    type=str,
    help=f"Logging level for the script. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL. Default {defaults['loglevel']}.",
)

# Number of threads to use for parallel requests
parser.add_argument(
    "--threads",
    default=os.environ.get("THREADS", 3),
    type=int,
    help=f"Number of threads to use for parallel requests. Default {defaults['threads']}.",
)

# Force the script to run even if the output file already exists
parser.add_argument(
    "--force",
    action="store_true",
    default=os.environ.get("FORCE", "false").lower() == "true",
    help=f"Force the script to run even if the output file already exists. Default {defaults['force']}.",
)

# Input file with the coordinates
parser.add_argument(
    "--input",
    default=os.environ.get("INPUT", "data/postcodes.csv"),
    type=str,
    help=f"Path to the input CSV file with latitude and longitude coordinates. Default {defaults['input']}.",
)

# Output file to save the results
parser.add_argument(
    "--output",
    default=os.environ.get("OUTPUT", "data/travel_times.csv"),
    type=str,
    help=f"Path to the output CSV file to save the results. Default {defaults['output']}.",
)

# Field in the CSV file that contains the identifier for the origin
parser.add_argument(
    "--id",
    default=os.environ.get("ID_FIELD", "codigo_postal"),
    type=str,
    help=f"Field in the CSV file that contains the identifier for the origin. Default {defaults['id']}.",
)

# Fields for latitude and longitude in the CSV file
parser.add_argument(
    "--lat",
    default=os.environ.get("LAT_FIELD", "lat"),
    type=str,
    help=f"Field in the CSV file that contains the latitude coordinates. Default {defaults['lat']}.",
)
parser.add_argument(
    "--lon",
    default=os.environ.get("LON_FIELD", "lon"),
    type=str,
    help=f"Field in the CSV file that contains the longitude coordinates. Default {defaults['lon']}.",
)

# OSRM API URL
parser.add_argument(
    "--osrm",
    default=os.environ.get("OSRM_URL", "http://localhost:5000"),
    type=str,
    help=f"URL of the OSRM API server. Default {defaults['osrm']}.",
)

# Get an optional argument for only processing a subset of the data
parser.add_argument(
    "--subset",
    default=os.environ.get("SUBSET", 0),
    type=int,
    help=f"Optional argument to process only a subset of the data. Default {defaults['subset']}.",
)


def query_osrm(osrm_url, originLon, originLat, destLon, destLat):
    # Create the URL for the OSRM API request
    url = f"{osrm_url}/route/v1/driving/{originLon},{originLat};{destLon},{destLat}?overview=false"
    try:
        # Send the request to the OSRM API
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        if "routes" in data and len(data["routes"]) > 0:
            duration = int(round(data["routes"][0]["duration"] / 60.0, 0))
            distance = int(round(data["routes"][0]["distance"] / 1000.0, 0))
            return (duration, distance)
        else:
            logger.error(f"No routes found for {origin} to {destination}.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending request to OSRM API: {e}")
        return None


# Function to send the request to the OSRM API
def get_travel_time(osrm_url, permutation):
    originId, originLon, originLat = permutation[0]
    destId, destLon, destLat = permutation[1]
    # Log the request
    logger.debug(f"Requesting travel time from {originId} to {destId}...")

    # Check if the coordinates are valid
    if not (originLon and originLat and destLon and destLat):
        logger.error(f"Invalid coordinates for {originId} or {destId}.")
        return (originId, destId, None, None)

    # Check if the coordinates are valid numbers
    try:
        originLon = float(originLon)
        originLat = float(originLat)
        destLon = float(destLon)
        destLat = float(destLat)

        # Forward and backward requests to OSRM API
        forward = query_osrm(osrm_url, originLon, originLat, destLon, destLat)
        backward = query_osrm(osrm_url, destLon, destLat, originLon, originLat)
        if forward and backward:
            # Return the results
            return (originId, destId, forward[0], forward[1], backward[0], backward[1])
        else:
            logger.error(f"Error getting travel time from {originId} to {destId}.")
            return (originId, destId, None, None, None, None)

    except ValueError:
        logger.error(f"Invalid coordinates for {originId} or {destId}.")
        return (originId, destId, None, None)


def get_travel_time_per_postal_code(osrm_url, permutations):
    results = []
    for p in permutations:
        result = get_travel_time(osrm_url, p)
        if result:
            results.append(result)
    return results


if __name__ == "__main__":
    # Parse the arguments
    args = parser.parse_args()

    # Set up basic logging
    logging.basicConfig(
        level=args.loglevel.upper(),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger()
    logger.info("Starting travel time calculation...")

    # Check if the input file exists
    if not os.path.exists(args.input):
        logger.error(f"Input file {args.input} does not exist.")
        exit(1)

    # Read the input CSV file
    with open(args.input, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
        logger.info(f"Read {len(data)} rows from the input file.")
        if len(data) == 0:
            logger.error("Input file is empty.")
            exit(1)

    # Check if the output file already exists
    if os.path.exists(args.output) and not args.force:
        logger.error(
            f"Output file {args.output} already exists. Use --force to overwrite."
        )
        exit(1)
    if args.force and os.path.exists(args.output):
        logger.warning(
            f"Output file {args.output} already exists. It will be overwritten."
        )

    # Filter from the input rows the ones without lat/lon
    data = [row for row in data if row[args.lat] and row[args.lon]]
    logger.info(f"Filtered {len(data)} rows with valid lat/lon coordinates.")
    if len(data) == 0:
        logger.error("No valid lat/lon coordinates found in the input file.")
        exit(1)

    # Sort the data by the id field
    data.sort(key=lambda x: x[args.id])
    logger.info(f"Sorted {len(data)} rows by the id field.")
    if len(data) == 0:
        logger.error("No valid id field found in the input file.")
        exit(1)

    # Create the permutations of the data, where each record is only
    # computed against the records that are after it in the list
    # This is done to avoid computing the same route twice
    # and to avoid computing the route from the origin to itself
    # The result is a list of tuples with the origin and destination
    # coordinates
    permutations = {}
    for i, origin in enumerate(data):
        for j, destination in enumerate(data[i + 1 :]):
            if origin[args.id] != destination[args.id]:
                if not permutations.get(origin[args.id]):
                    permutations[origin[args.id]] = []
                permutations[origin[args.id]].append(
                    (
                        (origin[args.id], origin[args.lon], origin[args.lat]),
                        (
                            destination[args.id],
                            destination[args.lon],
                            destination[args.lat],
                        ),
                    )
                )

    logger.info(
        f"Created {len(sum(permutations.values(), []))} permutations of the data."
    )
    if len(permutations) == 0:
        logger.error("No valid permutations found in the input file.")
        exit(1)

    postal_codes = permutations.keys()

    # Use multiprocessing to create a pool of workers to send the requests
    from multiprocessing import Pool, cpu_count
    from functools import partial

    # Create a pool of workers
    pool = Pool(args.threads)
    logger.info(f"Using {args.threads} threads for parallel requests.")
    # Create a partial function to pass the osrm_url to the worker
    partial_get_travel_times = partial(get_travel_time_per_postal_code, args.osrm)

    # Use Pool.map to send the requests in parallel

    results = []
    try:
        if args.subset > 0:
            logger.info(f"Processing only the first {args.subset} postal codes.")
            # extract from the permutations dict the first args.subset keys
            subset_permutations = {}
            for i, postal_code in enumerate(postal_codes):
                if i >= args.subset:
                    break
                subset_permutations[postal_code] = permutations[postal_code]
            results = pool.map(partial_get_travel_times, subset_permutations.values())
        else:
            logger.info(f"Processing all {len(permutations)} permutations.")
            results = pool.map(partial_get_travel_times, permutations.values())
        # Flatten the list of results
        results = [item for sublist in results for item in sublist]
        logger.info(f"Processed {len(results)} requests.")
    except Exception as e:
        logger.error(f"Error sending requests: {e}")
    finally:
        pool.close()
        pool.join()
        logger.info("Finished sending requests.")
        logger.info(f"Received {len(results)} results.")
        if len(results) == 0:
            logger.error("No results received.")
            exit(1)

    # Write the results to a CSV file
    fieldnames = ["cp_from", "cp_to", "from_time", "from_dist", "to_time", "to_dist"]
    with open(args.output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            originId, destId, from_time, from_dist, to_time, to_dist = result
            writer.writerow(
                {
                    "cp_from": originId,
                    "cp_to": destId,
                    "from_time": from_time,
                    "from_dist": from_dist,
                    "to_time": to_time,
                    "to_dist": to_dist,
                }
            )

    # Write the results to a JSON file with a dictionary of postal codes and the travel times
    # against all the other postal codes in an array of strings

    json_results = {}
    for result in results:
        originId, destId, from_time, from_dist, to_time, to_dist = result
        originId = str(int(originId))
        destId = str(int(destId))
        # Forward
        if not json_results.get(originId):
            json_results[originId] = []

        json_results[originId].append(
            ",".join([str(int(destId)), str(from_time), str(from_dist)])
        )
        # Backward
        if not json_results.get(destId):
            json_results[destId] = []
        json_results[destId].append(
            ",".join([str(int(originId)), str(to_time), str(to_dist)])
        )

    # Sort each array in the json_results dictionary
    for key in json_results.keys():
        json_results[key].sort()

    # Write the json_results to a JSON file
    json_file = args.output.replace(".csv", ".json")
    with open(json_file, "w") as f:
        json.dump(json_results, f, indent=4)

    logger.info(f"Results written to {args.output}.")

    # Print the first 10 results
    logger.info("First 10 results:")
    for r in results[:10]:
        logger.info(f"Result: {r}")

    # Compute some stats on the results
    # For each row, compute the difference in time and distance
    stats = []
    for result in results:
        originId, destId, from_time, from_dist, to_time, to_dist = result
        if from_time and to_time:
            time_diff = abs(from_time - to_time)
            dist_diff = abs(from_dist - to_dist)
            stats.append((originId, destId, time_diff, dist_diff))
        else:
            logger.error(f"Invalid result for {originId} to {destId}.")

    # Compute the average time and distance differences
    avg_time_diff = sum([s[2] for s in stats]) / len(stats) if stats else 0
    avg_dist_diff = sum([s[3] for s in stats]) / len(stats) if stats else 0
    logger.info(f"Average time difference: {avg_time_diff:.2f} minutes.")
    logger.info(f"Average distance difference: {avg_dist_diff:.2f} km.")

    # Find and compute the maximum time and distance differences
    max_time_diff = max([s[2] for s in stats]) if stats else 0
    max_dist_diff = max([s[3] for s in stats]) if stats else 0
    max_time_from_postal_code = list(
        filter(lambda x: abs(x[2] - x[4]) == max_time_diff, results)
    )
    max_dist_from_postal_code = list(
        filter(lambda x: abs(x[3] - x[5]) == max_dist_diff, results)
    )
    logger.info(
        f"Maximum time difference: {max_time_diff:.2f} minutes between {max_time_from_postal_code[0][0]} and {max_time_from_postal_code[0][1]}."
    )
    logger.info(
        f"Maximum distance difference: {max_dist_diff:.2f} km between {max_dist_from_postal_code[0][0]} and {max_dist_from_postal_code[0][1]}."
    )

    # Compute the standard deviation of the time and distance differences
    import statistics

    time_diffs = [s[2] for s in stats]
    dist_diffs = [s[3] for s in stats]
    if len(time_diffs) > 1:
        time_stddev = statistics.stdev(time_diffs)
    else:
        time_stddev = 0
    if len(dist_diffs) > 1:
        dist_stddev = statistics.stdev(dist_diffs)
    else:
        dist_stddev = 0
    logger.info(f"Standard deviation of time differences: {time_stddev:.2f} minutes.")
    logger.info(f"Standard deviation of distance differences: {dist_stddev:.2f} km.")

    # Compute the p95 and p99 of the time and distance differences
    time_diffs.sort()
    dist_diffs.sort()
    p95_time_diff = time_diffs[int(len(time_diffs) * 0.95)] if time_diffs else 0
    p99_time_diff = time_diffs[int(len(time_diffs) * 0.99)] if time_diffs else 0
    p95_dist_diff = dist_diffs[int(len(dist_diffs) * 0.95)] if dist_diffs else 0
    p99_dist_diff = dist_diffs[int(len(dist_diffs) * 0.99)] if dist_diffs else 0
    logger.info(f"95th percentile time difference: {p95_time_diff:.2f} minutes.")
    logger.info(f"99th percentile time difference: {p99_time_diff:.2f} minutes.")
    logger.info(f"95th percentile distance difference: {p95_dist_diff:.2f} km.")
    logger.info(f"99th percentile distance difference: {p99_dist_diff:.2f} km.")
    logger.info("Finished travel time calculation.")

    # Store all the stats in a json file
    import json

    stats_file = args.output.replace(".csv", ".stats.json")
    with open(stats_file, "w") as f:
        json.dump(
            {
                "postal_codes": len(postal_codes),
                "travel_times": len(results),
                "time_diffs": {
                    "avg": round(avg_time_diff, 2),
                    "max": max_time_diff,
                    "max_record": max_time_from_postal_code,
                    "stddev": round(time_stddev, 2),
                    "p95": p95_time_diff,
                    "p99": p99_time_diff,
                },
                "dist_diffs": {
                    "avg": round(avg_dist_diff, 2),
                    "max": max_dist_diff,
                    "max_record": max_dist_from_postal_code,
                    "stddev": round(dist_stddev, 2),
                    "p95": p95_dist_diff,
                    "p99": p99_dist_diff,
                },
            },
            f,
            indent=4,
        )
    logger.info(f"Stats written to {stats_file}.")
    logger.info("Finished travel time calculation.")

    exit(0)
