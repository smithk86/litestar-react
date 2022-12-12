from pathlib import Path

from pydantic import BaseSettings, validator
from starlite.app import Starlite
from starlite.controller import Controller
from starlite.enums import MediaType
from starlite.handlers import get

from starlite_react import ReactController


_dir = Path(__file__).parent


class Settings(BaseSettings):
    react_directory: Path = _dir / "tests/react-build"

    @validator("react_directory")
    def validate_react_directory(cls, v: Path) -> Path:
        assert v.is_dir(), f"directory does not exist: {v}"
        return v


settings = Settings()


class ApiController(Controller):
    path = "/api"

    @get(media_type=MediaType.TEXT)
    def api_root(self) -> str:
        return "Hello, World!"


class AppReactController(ReactController):
    directory = settings.react_directory


app = Starlite(route_handlers=[AppReactController, ApiController])
