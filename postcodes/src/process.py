import os
import logging
import csv
from multiprocessing import Pool
from pyproj import Transformer

from config import CARTOCIUDAD_PROVINCES_IDS, Config, DEFAULTS
from download import download_dataset
from extract_postcodes import extract_postcodes
from compute_centroids import compute_centroid

logger = logging.getLogger("process")


# A class that stores the configuration and contains the methods to process the datasets
class Process:
    def __init__(self, config: Config):
        self.config = config
        self.processes = min(self.config.threads, os.cpu_count())

    def get_province_data(self, province: str):
        # Check if the province is valid
        if province not in CARTOCIUDAD_PROVINCES_IDS:
            logger.error(
                f"Invalid province: {province}. Valid options are: {', '.join(CARTOCIUDAD_PROVINCES_IDS.keys())}"
            )
            return

        # Check if the dataset already exists
        data_dir = os.path.join(self.config.working_dir, "data", "provinces")
        os.makedirs(data_dir, exist_ok=True)

        gpkg_filename = f"{province}.gpkg"
        gpkg_path = os.path.join(data_dir, gpkg_filename)
        gpkg_path_exists = os.path.exists(gpkg_path)
        logger.debug(f"Checking if dataset exists at {gpkg_path}: {gpkg_path_exists}")

        if self.config.force and gpkg_path_exists:
            # Remove the existing file if force is set
            logger.info(f"Removing existing dataset {province}...")
            os.remove(gpkg_path)
            gpkg_path_exists = False

        if not gpkg_path_exists:
            # Download the dataset if the file is missing
            download_dataset(data_dir, CARTOCIUDAD_PROVINCES_IDS[province])
        else:
            logger.debug(f"Dataset {province} already exists. Skipping download.")

        return gpkg_path

    def get_data(self):
        logger.info("Getting datasets...")
        provinces = (
            [self.config.province]
            if self.config.province != DEFAULTS["province"]
            else CARTOCIUDAD_PROVINCES_IDS.keys()
        )

        # Use a multiprocessing pool to download the datasets in parallel
        logger.debug(f"Using {self.processes} processes for downloading datasets.")
        with Pool(self.processes) as pool:
            # Map the get_province_data function to the provinces
            results = pool.map(self.get_province_data, provinces)

        logger.info("All datasets ready for processing.")
        for result in results:
            logger.info(f"\t{result}")

        return results

    def get_points(self, datasets):
        # Use a multiprocessing pool to download the datasets in parallel
        logger.debug(f"Using {self.processes} processes for traversing the datasets.")
        with Pool(self.processes) as pool:
            # Map the get_province_data function to the provinces
            results = pool.map(self.extract_province, datasets)

            # Merge all the results into a single list
            results_merged = [item for sublist in results for item in sublist]

        logger.info(
            f"All datasets processed generating {len(results_merged)} CSV postcodes."
        )

    def extract_province(self, dataset):
        """
        Extract the street_number points from the dataset.
        """
        # Get the file name from the dataset path
        province = os.path.basename(dataset).replace(".gpkg", "")
        logger.info(f"Extracting points into data/{province}...")
        output_dir = os.path.join(
            self.config.working_dir, "data", "postcodes", province
        )
        os.makedirs(output_dir, exist_ok=True)
        return extract_postcodes(dataset, output_dir)

    def get_centroids(self):
        """
        Generate the centroids of the postcodes
        """
        logger.info("Generating centroids...")
        # Get the list of postcodes
        postcodes_dir = os.path.join(self.config.working_dir, "data", "postcodes")
        # Walk the postcodes_dir to get all CSV files
        postcodes = []
        for root, _, files in os.walk(postcodes_dir):
            for file in files:
                if file.endswith(".csv"):
                    postcodes.append(os.path.join(root, file))
        logger.info(f"Found {len(postcodes)} postcodes to process.")

        # Use a multiprocessing pool to generate the centroids in parallel
        logger.debug(f"Using {self.processes} processes for generating centroids.")
        with Pool(self.processes) as pool:
            results = pool.map(compute_centroid, postcodes)
        
        # Write the results in a CSV file using the keys from the results
        logger.info("Writing the centroids to a single CSV file...")
        output_dir = os.path.join(self.config.working_dir, "data")
        output_file = os.path.join(output_dir, "postcodes.csv")

        # Transform back from EPSG:25830 to EPSG:4258
        transformer = Transformer.from_crs("EPSG:25830", "EPSG:4258", always_xy=True)
        for result in results:
            if result is not None:
                x,y = result["x"], result["y"]
                lon, lat = None, None
                if x is not None and y is not None:
                    lon, lat = transformer.transform(x, y)
                    lon = round(lon, 6)
                    lat = round(lat, 6)
                result["lon"] = lon
                result["lat"] = lat

        with open(output_file, "w") as f:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        logger.info(f"Centroids written to {output_file}")


    def process(self):
        """
        Process the datasets.
        """

        # Get the data
        logger.info("===========================")
        logger.info("[1] Processing datasets...")
        logger.info("===========================")
        datasets = self.get_data()

        # Extract the postcodes from the datasets
        logger.info("===========================")
        logger.info("[2] Extracting street number points from datasets...")
        logger.info("===========================")
        self.get_points(datasets)

        # Generate the centroid of each postcode
        logger.info("===========================")
        logger.info("[3] Generating centroids...")
        logger.info("===========================")
        self.get_centroids()
