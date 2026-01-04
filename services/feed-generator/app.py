"""
Unified Feed Generator Service

Supports multiple data sources via provider pattern:
- synthetic: Demo/testing with simulated data
- globaldatafeeds: Real market data from Global Datafeeds API

Configure via FEED_PROVIDER environment variable.
"""

import os
import sys

# Configuration
FEED_PROVIDER = os.getenv('FEED_PROVIDER', 'synthetic').lower()

# Import the appropriate provider
if FEED_PROVIDER == 'synthetic':
    from providers.synthetic_provider import SyntheticFeedProvider as FeedProvider
elif FEED_PROVIDER == 'globaldatafeeds':
    from providers.gdf_provider import GlobalDatafeedsProvider as FeedProvider
else:
    print(f"ERROR: Unknown FEED_PROVIDER '{FEED_PROVIDER}'")
    print("Valid options: synthetic, globaldatafeeds")
    sys.exit(1)

import structlog

# Logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


def main():
    """Entry point"""
    logger.info(
        "feed_generator_starting",
        provider=FEED_PROVIDER
    )
    
    try:
        generator = FeedProvider()
        generator.run()
    except KeyboardInterrupt:
        logger.info("shutting_down")
    except Exception as e:
        logger.error("fatal_error", error=str(e), exc_info=True)
        raise


if __name__ == '__main__':
    main()
