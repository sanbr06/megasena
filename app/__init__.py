from flask import Flask

from app.api.routes import api
from app.api.v1 import api_v1
from app.core.config import settings
from app.providers.caixa import CaixaLotteryProvider
from app.repositories.portfolio_repository import PortfolioRepository
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
        "LOTTERY_API_BASE_URL": settings.lottery_api_base_url,
        "TESTING": False,
    }
    if test_config:
        config.update(test_config)
    app.config.update(config)

    repository = ResultRepository(app.config["DATABASE_URL"])
    repository.initialize()
    portfolio_repository = PortfolioRepository(repository.connection)
    portfolio_repository.initialize()

    provider = CaixaLotteryProvider(
        base_url=app.config["LOTTERY_API_BASE_URL"],
        timeout=app.config["REQUEST_TIMEOUT"],
    )
    result_service = ResultService(repository, provider)
    lottery_service = LotteryService(repository)

    app.extensions["result_repository"] = repository
    app.extensions["portfolio_repository"] = portfolio_repository
    app.extensions["lottery_provider"] = provider
    app.extensions["result_service"] = result_service
    app.extensions["lottery_service"] = lottery_service
    app.register_blueprint(api)
    app.register_blueprint(api_v1)

    return app
