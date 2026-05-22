import logging
import structlog


def configure_logging() -> None:

    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ]
    )

    logging.basicConfig(level=logging.INFO)