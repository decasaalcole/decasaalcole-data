import os
import fiona
import logging
import csv
from pyproj import Transformer

from .config import STREET_NUMBERS_FIELDS

logger = logging.getLogger("extract_postcodes")

# Initialize a transformer (e.g., EPSG:4258 to UTM Zone 33N)
transformer = Transformer.from_crs("EPSG:4258", "EPSG:25830", always_xy=True)

def transform_coordinates(geometry):
    """
    Transform the coordinates from WGS84 to UTM Zone 33N
    """
    if geometry["type"] != "Point":
        logger.warning(f"Unsupported geometry type: {geometry['type']}")
        return None

    lon, lat = geometry["coordinates"]

    return transformer.transform(lon, lat)

def create_feature_dict(feature):
    """
    Create a dictionary from the feature properties and geometry
    """
    # Extract the properties and geometry from the feature
    x, y = transform_coordinates(feature["geometry"])

    # Extract the properties defined in STREET_NUMBERS_FIELDS
    properties = {key: feature["properties"].get(key) for key in STREET_NUMBERS_FIELDS}

    # Create a dictionary with the properties and geometry
    feature_dict = {
        "x": round(x, 3) if x is not None else None,
        "y": round(y, 3) if y is not None else None,
        **properties,
    }

    # Remove the 'geometry' key from the properties
    if "geometry" in feature_dict:
        del feature_dict["geometry"]

    return feature_dict


def extract_postcodes(gpkg_path, output_path):
    """
    Extract the street number points from the dataset and save them into a CSV file per postcode
    """
    # Object to store the features per postcode
    features_per_postcode = {}

    # Load the dataset with fiona
    with fiona.open(gpkg_path) as src:
        # Get the schema and crs
        schema = src.schema
        crs = src.crs
        logger.debug(f"Schema: {schema}")
        logger.debug(f"CRS: {crs}")

        # Iterate over the features in the dataset
        for feature in src:
            feature_dict = create_feature_dict(feature)

            # Extract the postcode from the properties
            postcode = feature_dict.get("codigo_postal")
            if postcode:
                # If the postcode is not in the dictionary, create a new list
                if postcode not in features_per_postcode:
                    features_per_postcode[postcode] = []

                # Append the feature to the list for the postcode
                features_per_postcode[postcode].append(feature_dict)
            else:
                logger.debug(f"Feature without postcode: {feature_dict}")
                continue
    
    # Create the output CSV files
    for postcode, features in features_per_postcode.items():
        # Create the output file path
        output_file = os.path.join(output_path, f"{postcode}.csv")

        # Write the features to the CSV file
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=features[0].keys())
            writer.writeheader()
            writer.writerows(features)

    return list(features_per_postcode.keys())
