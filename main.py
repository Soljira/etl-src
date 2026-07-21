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
        logger.info("Database connection OK. Starting API server...")
    else:
        logger.warning("Database connection failed. API will start but queries will fail.")
        logger.warning("Please check your .env file and ensure PostgreSQL is running.")

    # Start Flask API
    from src.api import create_app
    app = create_app()
    logger.info("Starting Flask API on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    main()
