# -*- coding: utf-8 -*-
import logging

from config import CARTOCIUDAD_PROVINCES_IDS, Config
from cli import parse_args, logger_format
from process import Process


if __name__ == "__main__":

    # setup a basic logger
    logging.basicConfig(
        level=logging.INFO,
        format=logger_format,
        handlers=[logging.FileHandler("data/dcac-postcodes.log"), logging.StreamHandler()],
    )
    # set up a basic logger
    logger = logging.getLogger()
    logger.name = "main"

    # Get CLI args
    args = parse_args()

    # Reset the logger level
    logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))

    logging.getLogger("requests").setLevel(logging.WARNING)
    logger.debug("Requests log level set to WARNING")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logger.debug("Urllib3 log level set to WARNING")
    logging.getLogger("fiona").setLevel(logging.WARNING)
    logger.debug("Fiona log level set to WARNING")

    config = Config(
        working_dir=args.working_dir,
        province=args.province,
        force=args.force,
        threads=args.threads,
    )
    logger.debug("Configuration:")
    for key, value in config._asdict().items():
        logger.debug(f"\t{key}: {value}")

    # Create the processing object
    process = Process(config)

    # Run the process
    process.process()
