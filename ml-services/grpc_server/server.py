from common.config import Settings
from common.logging import get_logger


logger = get_logger(__name__)


def serve() -> None:
    settings = Settings()
    logger.info("Starting gRPC stub server on port %s", settings.ml_grpc_port)


if __name__ == "__main__":
    serve()
