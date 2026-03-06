import os
import logging
import argparse
from dotenv import load_dotenv
from scraper import SchoolScraper

load_dotenv()

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.getenv("LOG_FILE", "logs/scraper.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def setup_directories() -> None:
    for d in ("data", "logs"):
        os.makedirs(d, exist_ok=True)
    logger.info("Directories ready")


def parse_args():
    default_subset = int(os.getenv("SCHOOL_SUBSET", "0"))
    default_threads = int(os.getenv("SCHOOL_THREADS", "1"))

    parser = argparse.ArgumentParser(description="School data scraper")
    parser.add_argument(
        "--school-codes",
        type=str,
        nargs="+",
        help='Specific school codes to scrape (e.g. "03012591 03012592")',
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=default_subset,
        help=f"Number of schools to scrape (0 = all, default: {default_subset})",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=default_threads,
        help=f"Concurrent threads for detail fetching (default: {default_threads})",
    )
    return parser.parse_args()


def main() -> None:
    try:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

        setup_directories()
        args = parse_args()

        scraper = SchoolScraper()

        logger.info("Starting school scraping process")
        if args.school_codes:
            logger.info(f"Scraping specific schools: {args.school_codes}")
            schools_data = scraper.scrape_specific_schools(args.school_codes)
        else:
            schools_data = scraper.scrape_schools(
                subset=args.subset, threads=args.threads
            )
        logger.info(f"Successfully scraped {len(schools_data)} schools")

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()
