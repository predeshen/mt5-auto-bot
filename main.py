"""Main entry point for MT5 Auto Scalper application."""

from src.app_controller import ApplicationController
from src.logger import logger


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("MT5 Auto Scalper Starting...")
    logger.info("=" * 60)
    
    try:
        app = ApplicationController()
        app.run()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
