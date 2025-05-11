import os
import logging
import argparse
from scraper import SchoolScraper

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_directories() -> None:
    """
    Create necessary directories for the scraper.
    
    Creates the following directories if they don't exist:
    - data/: For storing scraped data
    - logs/: For log files
    - tmp/: For local HTML files during development
    
    Raises:
        OSError: If directory creation fails
    """
    try:
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        os.makedirs('tmp', exist_ok=True)
        logger.info("Directories created successfully")
    except OSError as e:
        logger.error(f"Failed to create directories: {str(e)}")
        raise

def setup_logging():
    """Configure logging based on environment variables."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', './logs/scraper.log')
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def parse_args():
    DEFAULT_SUBSET = os.getenv('SCHOOL_SUBSET', 0)
    DEFAULT_THREADS = os.getenv('SCHOOL_THREADS', 1)

    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='School data scraper')
    parser.add_argument('--local', action='store_true',
                      help='Use local files from tmp/ directory instead of making HTTP requests')
    parser.add_argument('--school-codes', type=str, nargs='+',
                      help='List of school codes to scrape (e.g., "03012591 03012592")')
    parser.add_argument('--subset', type=int, default=DEFAULT_SUBSET,
                      help=f"Number of schools to scrape ({DEFAULT_SUBSET} for all schools)")
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS,
                        help="Number of threads to use for scraping (default: {DEFAULT_THREADS})")
    return parser.parse_args()

def main() -> None:
    """
    Main entry point for the school scraper application.
    
    This function:
    1. Sets up necessary directories
    2. Initializes the SchoolScraper
    3. Runs the scraping process
    4. Handles any errors that occur during execution
    
    The scraper can run in two modes:
    - Normal mode: Makes HTTP requests to the education portal
    - Local mode: Uses pre-downloaded HTML files from the tmp/ directory
    
    Environment Variables:
        LOCAL_MODE: Set to '1' to enable local mode
        Other variables are defined in the .env file
    
    Raises:
        Exception: If any error occurs during the scraping process
    """
    try:
        # Disable debug logging from some external libraries
        logging.getLogger("requests_cache").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

        # Setup directories
        setup_directories()
        
        # Parse command line arguments
        args = parse_args()
        
        # Check if local mode is enabled
        local_mode = os.getenv('LOCAL_MODE', '0') == '1' or args.local
        logger.info(f"Running in {'local' if local_mode else 'normal'} mode")
        
        # Initialize scraper
        scraper = SchoolScraper(use_local=local_mode)
        
        # Run scraper
        logger.info("Starting school scraping process")
        if args.school_codes:
            logger.info(f"Scraping specific schools: {args.school_codes}")
            schools_data = scraper.scrape_specific_schools(args.school_codes)
        else:
            schools_data = scraper.scrape_schools(subset=args.subset, threads=args.threads)
        logger.info(f"Successfully scraped {len(schools_data)} schools")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
