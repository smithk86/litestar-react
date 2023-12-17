from __future__ import annotations

from functools import lru_cache
from mimetypes import guess_type
from pathlib import Path
from typing import TYPE_CHECKING

from litestar.controller import Controller
from litestar.datastructures.response_header import ResponseHeader
from litestar.exceptions import HTTPException, NotFoundException
from litestar.handlers import get
from litestar.response import Response


if TYPE_CHECKING:
    from typing import Any


class ReactFileResponse(Response[bytes]):
    def render(self, content: bytes, *args: Any, **kwargs: Any) -> bytes:
        return content


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


class BaseReactController(Controller):
    directory: Path
    """
        A [Path][pathlib.Path] object to the directory which holds the built React application files.
    """
    default_index: str = "index.html"
    """
        A string to represent the default file to server.
    """
    index_file_headers: list[ResponseHeader] | None = [
        ResponseHeader(
            name="cache-control", value="max-age=0, no-cache, no-store, must-revalidate"
        ),
    ]
    """
        Headers for index file
    """
    replacement_file_suffixes: set[str] = {".css", ".html", ".js", ".json", ".map"}
    """
        A set of file extention strings which may contain replacement values
    """
    replacement_values: dict[str, str] = {}
    """
        Values to replace in the static files
    """
    static_file_path: str = "/static"
    """
        Path to static files
    """
    static_file_headers: list[ResponseHeader] | None = [
        ResponseHeader(
            name="cache-control", value="public, max-age=31536000, immutable"
        ),
    ]
    """
        Headers for static files
    """

    @lru_cache
    def get_file_contents(self, path: Path) -> bytes:
        """
        return the contents of the given file
        """

        # get the contents of the file
        with open(path, "rb") as fh:
            file_content = fh.read()

        for inital_value, replacement_value in self.replacement_values.items():
            file_content = file_content.replace(
                inital_value.encode("utf-8"), replacement_value.encode("utf-8")
            )

        return file_content

    @get(
        path=["/", "/{path:path}"],
        name="react",
        include_in_schema=False,
        sync_to_thread=False,
    )
    def root(self, path: Path | None = None) -> ReactFileResponse:
        filepath = self.directory / str(path)[1:]
        is_static_file = path and path.is_relative_to(self.static_file_path)
        headers: list[ResponseHeader] = []

        if is_static_file:
            if self.static_file_headers:
                headers += self.static_file_headers
            if not filepath.is_file():
                raise NotFoundException()
        else:
            # if the request file does not exist, return the default file
            if not filepath.is_file():
                if self.index_file_headers:
                    headers += self.index_file_headers
                filepath = self.directory / self.default_index

        # detect media type
        media_type = get_media_type(filepath)

        # get the contents of the file
        file_content = self.get_file_contents(filepath)
        return ReactFileResponse(
            content=file_content, headers=headers, media_type=media_type
        )
