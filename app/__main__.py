import uvicorn

from app.core.settings import settings
from app.gunicorn_runner import GunicornApplication


def main() -> None:
    """Entrypoint of the application."""
    if settings.RELOAD:
        uvicorn.run(
            "app.web.application:get_app",
            workers=settings.WORKERS,
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.RELOAD,
            log_level=settings.LOG_LEVEL.value.lower(),
            factory=True,
        )
    else:
        # We choose gunicorn only if reload
        # option is not used, because reload
        # feature doesn't work with gunicorn workers.
        GunicornApplication(
            "app.web.application:get_app",
            host=settings.HOST,
            port=settings.PORT,
            workers=settings.WORKERS,
            factory=True,
            accesslog="-",
            loglevel=settings.LOG_LEVEL.value.lower(),
            access_log_format='%r "-" %s "-" %Tf',
        ).run()


if __name__ == "__main__":
    main()
