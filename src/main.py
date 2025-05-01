import os
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from scraper import SchoolScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='School data scraper')
    parser.add_argument('--local', action='store_true',
                      help='Use local files from tmp/ directory instead of making HTTP requests')
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
        USE_LOCAL: Set to '1' to enable local mode
        Other variables are defined in the .env file
    
    Raises:
        Exception: If any error occurs during the scraping process
    """
    try:
        # Setup directories
        setup_directories()
        
        # Initialize scraper
        use_local = os.getenv('USE_LOCAL', '0') == '1'
        scraper = SchoolScraper(use_local=use_local)
        
        # Run scraper
        logger.info("Starting school scraping process")
        schools_data = scraper.scrape_schools()
        logger.info(f"Successfully scraped {len(schools_data)} schools")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 