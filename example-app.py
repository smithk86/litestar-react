from pathlib import Path

from pydantic import BaseSettings, validator
from starlite.app import Starlite
from starlite.controller import Controller
from starlite.enums import MediaType
from starlite.exceptions import NotFoundException
from starlite.handlers import get

from starlite_react import ReactController


"""
This example uses Pydantic to configure the app using environment variables.

Run example-app.py using Poetry and Uvicorn:

    # point this variable to the build directory of any React app
    export REACT_DIRECTORY="~/tests/react-build"
    poetry run uvicorn --reload example-app:app

"""


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

    @get(path="/{_:path}")
    def not_found(self) -> None:
        raise NotFoundException()


class AppReactController(ReactController):
    """
    Subclass ReactController and set the `directory` field
    """

    directory = settings.react_directory


"""
The ReactController is going to own its url path -- even if it is root (which it is by default).

Any unspecified route will return the React index instead of throwing a 404. This allows React Router DOM
to work without Starlite interfering.

In this example, ApiController has a catch-all route which will properly throw a 404 if a
non-existant API call is attempted within its path (/api).
"""
app = Starlite(route_handlers=[AppReactController, ApiController])
