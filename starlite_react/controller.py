from functools import lru_cache
from mimetypes import guess_type
from pathlib import Path

from starlite.connection import Request
from starlite.controller import Controller
from starlite.datastructures import Provide
from starlite.exceptions import HTTPException, NotFoundException
from starlite.handlers import get
from starlite.response import Response
from starlite.types import Dependencies


class ReactFileResponse(Response[bytes]):
    def render(self, content: bytes) -> bytes:
        return content


def get_root_path(request: Request[None, None]) -> str:
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
    dependencies: Dependencies = {"root_path": Provide(get_root_path)}
    """
        Add the "root_path" dependency
    """

    @lru_cache
    def get_file_contents(self, path: Path, root_path: str | None) -> bytes:
        """
        return the contents of the given file
        """

        # get the contents of the file
        with open(path, "rb") as fh:
            file_content = fh.read()

        # detect {{ROOT_PATH}} in the static files and replace it with app.root_path
        if path.suffix in self.root_file_suffixes:
            file_content = file_content.replace(
                b"{{ROOT_PATH}}", root_path.encode("utf-8") if root_path else b""
            )

        return file_content

    @get("/static/{path:path}", name="react-static", include_in_schema=False)
    async def static_files(self, root_path: str, path: Path) -> ReactFileResponse:
        filepath = self.directory / "static" / str(path)[1:]
        if not filepath.is_file():
            raise NotFoundException()
        # detect media type
        media_type = get_media_type(filepath)
        # get the contents of the file
        file_content = self.get_file_contents(filepath, root_path)
        return ReactFileResponse(content=file_content, media_type=media_type)

    @get(path=["/", "/{filename:str}"], name="react-root", include_in_schema=False)
    async def root_files(
        self, root_path: str, filename: Path | None = None
    ) -> ReactFileResponse:
        filepath = self.directory / filename if filename else self.directory
        # if the request file does not exist, return the default file
        if not filepath.is_file():
            filepath = self.directory / self.default_index
        # detect media type
        media_type = get_media_type(filepath)
        # get the contents of the file
        file_content = self.get_file_contents(filepath, root_path)
        return ReactFileResponse(content=file_content, media_type=media_type)
