from pathlib import Path

from litestar.app import Litestar
from litestar.controller import Controller
from litestar.enums import MediaType
from litestar.exceptions import NotFoundException
from litestar.handlers import get

from litestar_react import BaseReactController


"""
This example uses Pydantic to configure the app using environment variables.

Run example-app.py using Poetry and Uvicorn:

    # point this variable to the build directory of any React app
    export REACT_DIRECTORY="~/tests/react-build"
    poetry run uvicorn --reload example-app:app

"""


_dir = Path(__file__).parent


class ApiController(Controller):
    path = "/api"

    @get(media_type=MediaType.TEXT, sync_to_thread=False)
    def api_root(self) -> str:
        return "Hello, World!"

    @get(path="/{_:path}", sync_to_thread=False)
    def not_found(self) -> None:
        raise NotFoundException()


class ReactController(BaseReactController):
    """
    Subclass ReactController and set the `directory` field
    """

    directory = _dir / "tests/react-build"


"""
The ReactController is going to own its url path -- even if it is root (which it is by default).

Any unspecified route will return the React index instead of throwing a 404. This allows React Router DOM
to work without litestar interfering.

In this example, ApiController has a catch-all route which will properly throw a 404 if a
non-existant API call is attempted within its path (/api).
"""
app = Litestar(route_handlers=[ReactController, ApiController])
