import logging
from src.config.logging_config import setup_logging
from src.db.database import test_connection

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing ETL for Open Data Philippines Datasets pipeline...")
    
    # Test database connection
    logger.info("Testing database connection...")
    if test_connection():
        logger.info("Foundation phase setup is complete and successful.")
    else:
        logger.warning("Foundation phase setup complete, but database connection failed.")
        logger.warning("Please check your .env file and ensure PostgreSQL is running.")

if __name__ == "__main__":
    main()
