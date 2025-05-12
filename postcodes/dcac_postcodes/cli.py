import logging
import argparse
import os

from .config import CARTOCIUDAD_PROVINCES_IDS, DEFAULTS

logger = logging.getLogger("cli")
logger_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


def parse_args():
    """
    Parse command line arguments.
    """

    # Use argparse to allow for command line arguments
    parser = argparse.ArgumentParser(description="Extract postcodes from Cartociudad.")

    # Log level argument
    parser.add_argument(
        "--log-level",
        "-l",
        type=str,
        default=os.getenv("DCAC_LOG", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level. Default is INFO or the value of DCAC_LOG environment variable.",
    )

    # Province argument
    parser.add_argument(
        "--province",
        "-p",
        metavar="PROVINCE",
        type=str,
        default=os.getenv("DCAC_PROVINCE", DEFAULTS["province"]),
        choices=CARTOCIUDAD_PROVINCES_IDS.keys(),
        help="The province to process. Valid options are: "
        + ", ".join(CARTOCIUDAD_PROVINCES_IDS.keys())
        + ". Default is all or the value of DCAC_PROVINCE environment variable.",
    )
    # Force argument
    parser.add_argument(
        "--force",
        "-f",
        default=os.getenv("DCAC_FORCE", "false").lower() == "true" or DEFAULTS["force"],
        action="store_true",
        help=f"Force download of the dataset even if it already exists. Default is {DEFAULTS['force']} or the value of DCAC_FORCE environment variable.",
    )
    # Working dir argument
    parser.add_argument(
        "--working-dir",
        "-w",
        metavar="WORKING_DIR",
        type=str,
        default=os.getenv("DCAC_WORKING_DIR", DEFAULTS["working_dir"]),
        help="The working directory. Default is the current directory or the value of DCAC_WORKING_DIR environment variable.",
    )
    # Threads argument
    parser.add_argument(
        "--threads",
        "-t",
        metavar="THREADS",
        type=int,
        default=os.getenv("DCAC_THREADS", DEFAULTS["threads"]),
        help=f"The number of threads to use. Default is {DEFAULTS['threads']} or the value of DCAC_THREADS environment variable.",
    )

    return parser.parse_args()
