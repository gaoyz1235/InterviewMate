import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(router)
    return app


def configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("httpx").propagate = False
    logging.getLogger("httpcore").propagate = False

    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.FileHandler) and Path(getattr(handler, "baseFilename", "")) == log_file.resolve():
            root_logger.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info("logging.configured file=%s", log_file.resolve())


app = create_app()
