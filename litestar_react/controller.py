from functools import lru_cache
from mimetypes import guess_type
from pathlib import Path
from typing import Any

from litestar.connection import Request
from litestar.controller import Controller
from litestar.di import Provide
from litestar.exceptions import HTTPException, NotFoundException
from litestar.handlers import get
from litestar.response import Response
from litestar.types import Dependencies


class ReactFileResponse(Response[bytes]):
    def render(self, content: bytes, *args: Any, **kwargs: Any) -> bytes:
        return content


def get_root_path(request: Request[Any, Any, Any]) -> str:
    return request.scope.get("root_path", "/")


@lru_cache
def get_media_type(path: Path) -> str:
    """
    auto-detect the correct media type using the name of the file
    """

    if path.name.endswith(".css.map") or path.name.endswith(".js.map"):
        return "application/json"
    else:
        media_type, _ = guess_type(path.name)
        if isinstance(media_type, str):
            return media_type
        else:
            raise HTTPException(
                detail=f"unknown media type for {path.name}", status_code=400
            )


class ReactController(Controller):
    directory: Path
    """
        A [Path][pathlib.Path] object to the directory which holds the built React application files.
    """
    default_index: str = "index.html"
    """
        A string to represent the default file to server.
    """
    root_file_suffixes: set[str] = {".css", ".html", ".js", ".json", ".map"}
    """
        A set of strings which may contain the "{{ROOT_FILE}}" variable.
    """
    dependencies: Dependencies = {
        "root_path": Provide(get_root_path, sync_to_thread=False)
    }
    """
        Add the "root_path" dependency
    """

    @lru_cache
    def get_file_contents(self, path: Path, root_path: str) -> bytes:
        """
        return the contents of the given file
        """

        # get the contents of the file
        with open(path, "rb") as fh:
            file_content = fh.read()

        # detect {{ROOT_PATH}} in the static files and replace it with app.root_path
        if path.suffix in self.root_file_suffixes:
            root_path_set: list[str] = []
            root_path_set.extend(filter(None, root_path.split("/")))
            root_path_set.extend(filter(None, self.path.split("/")))
            full_root_path = "/" + "/".join(root_path_set) if root_path_set else ""
            file_content = file_content.replace(
                b"{{ROOT_PATH}}", full_root_path.encode("utf-8")
            )

        return file_content

    @get(
        path=["/", "/{path:path}"],
        name="react",
        include_in_schema=False,
        sync_to_thread=False,
    )
    def root(self, root_path: str, path: Path | None = None) -> ReactFileResponse:
        filepath = self.directory / str(path)[1:]
        is_static_file = str(path).startswith("/static")

        if is_static_file:
            if not filepath.is_file():
                raise NotFoundException()
        else:
            # if the request file does not exist, return the default file
            if not filepath.is_file():
                filepath = self.directory / self.default_index

        # detect media type
        media_type = get_media_type(filepath)

        # get the contents of the file
        file_content = self.get_file_contents(filepath, root_path)
        return ReactFileResponse(content=file_content, media_type=media_type)
