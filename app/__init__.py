from flask import Flask

from app.api.routes import api
from app.core.config import settings
from app.repositories.result_repository import ResultRepository
from app.services.lottery_service import LotteryService
from app.services.result_service import ResultService


def create_app(test_config=None):
    app = Flask(__name__)

    config = {
        "APP_ENV": settings.app_env,
        "HOST": settings.host,
        "PORT": settings.port,
        "API_TOKEN": settings.api_token,
        "DATABASE_URL": settings.database_url,
        "REQUEST_TIMEOUT": settings.request_timeout,
        "TESTING": False,
    }
    if test_config:
        config.update(test_config)
    app.config.update(config)

    repository = ResultRepository(app.config["DATABASE_URL"])
    repository.initialize()

    result_service = ResultService(repository, app.config["REQUEST_TIMEOUT"])
    lottery_service = LotteryService(repository)

    app.extensions["result_service"] = result_service
    app.extensions["lottery_service"] = lottery_service
    app.register_blueprint(api)

    return app
