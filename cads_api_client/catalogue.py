import datetime
from typing import Any, List, Optional
import urllib

import attrs
from owslib import ogcapi

from . import processing


@attrs.define
class Collections(processing.ApiResponse):
    def collection_ids(self) -> List[str]:
        return [collection["id"] for collection in self.json["collections"]]


@attrs.define
class Collection(processing.ApiResponse):
    def end_datetime(self) -> datetime.datetime:
        try:
            end = self.json["extent"]["temporal"]["interval"][1]
        except Exception:
            end = "2022-07-20T23:00:00"
        return datetime.datetime.fromisoformat(end)

    def retrieve_process(self) -> processing.Process:
        url = self.get_link_href(rel="retrieve")
        return processing.Process.from_request("get", url)

    def submit(self, **request: Any) -> processing.Remote:
        retrieve_process = self.retrieve_process()
        status_info = retrieve_process.execute(inputs=request)
        return status_info.make_remote()

    def retrieve(self, target: Optional[str] = None, **request: Any) -> str:
        remote = self.submit(**request)
        return remote.download(target)


class Catalogue:
    supported_api_version = "v1"

    def __init__(
        self, url: str, force_exact_url: bool = False, *args: Any, **kwargs: Any
    ) -> None:
        if not force_exact_url:
            url = f"{url}/{self.supported_api_version}"
        self.url = url

    def collections(self) -> Collections:
        url = f"{self.url}/collections"
        return Collections.from_request("get", url)

    def collection(self, collection_id: str) -> Collection:
        url = f"{self.url}/collections/{collection_id}"
        return Collection.from_request("get", url)
