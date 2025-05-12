import logging
import csv

from sklearn.cluster import DBSCAN
import numpy as np

from .config import CLUSTERING_PARAMETERS

logger = logging.getLogger("compute_centroids")

def compute_centroid(postcode_path: str) -> None:
    # Check the path
    if not postcode_path.endswith(".csv"):
        logger.error(f"Invalid postcode path: {postcode_path}. Must be a .csv file.")
        return

    # Read the CSV file
    try:
        rows = []
        with open(postcode_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)
        logger.debug(f"Read {len(rows)} rows from {postcode_path}")
    except Exception as e:
        logger.error(f"Error reading file {postcode_path}: {e}")
        return
    
    # Create a numpy array from the rows with the x and y coordinates
    postcode = rows[0]["codigo_postal"]
    town = rows[0]["poblacion"]
    try:
        np_rows = np.array([[float(row["x"]), float(row["y"])] for row in rows])
    except KeyError as e:
        logger.error(f"Missing key in row: {e}")
        return
    except ValueError as e:
        logger.error(f"Error converting row to float: {e}")
        return
    except Exception as e:
        logger.error(f"Error processing rows: {e}")
        return
    

    # Compute the DBSCAN clustering in the rows with scikit-learn
    dbscan = DBSCAN(
        eps=CLUSTERING_PARAMETERS["eps"],
        min_samples=CLUSTERING_PARAMETERS["min_samples"],
        metric=CLUSTERING_PARAMETERS["metric"],
    )
    clusters = dbscan.fit_predict(np_rows)

    logger.debug(f"Computed {len(set(clusters))} clusters")
    
    
    labels = np.unique(clusters)
    num_rows = len(rows)

    label_centroids = []

    # Compute the centroids of each cluster
    for label in labels:
        if label != -1:  # ignore noise
            num_points_in_cluster = np.sum(clusters == label)
            centroid = np.mean(np_rows[clusters == label], axis=0)
            label_centroids.append({
                "label": label,
                "centroid": centroid,
                "num_points": num_points_in_cluster,
            })

    # Find the closest point in initial rows list to each centroid
    results = []
    for label_centroid in label_centroids:
        label = label_centroid["label"]
        centroid = label_centroid["centroid"]
        distances = np.linalg.norm(np_rows - centroid, axis=1)
        closest_point_index = np.argmin(distances)
        closest_point = rows[closest_point_index]
        results.append({
            "pct": round(int(label_centroid["num_points"]) / num_rows * 100, 2),
            "num_points": int(label_centroid["num_points"]),
            **closest_point
        })

    # Sort the results by number of points in descending order
    results.sort(key=lambda x: x["num_points"], reverse=True)
    result = results[0] if results else {
        "pct": 0,
        "num_points": 0,
        "codigo_postal": postcode,
        "poblacion": town,
        "x": None,
        "y": None,
    }
    if result:
        logger.debug(f"Postcode {result['codigo_postal']} centroid on {result['pct']}% cluster")
    else:
        logger.debug("No centroids found")
    
    return result
