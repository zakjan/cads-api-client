from typing import Any, Dict, List, Optional

import attrs

from cads_api_client.api_response import ApiResponse
from cads_api_client.processes import Process


# TODO as iterator
@attrs.define
class Collections(ApiResponse):
    def collection_ids(self) -> List[str]:
        return [collection["id"] for collection in self.json["collections"]]

    def next(self) -> Optional[ApiResponse]:
        return self.from_rel_href(rel="next")

    def prev(self) -> Optional[ApiResponse]:
        return self.from_rel_href(rel="prev")


@attrs.define
class Collection(ApiResponse):

    headers: Dict[str, Any] = {}

    # def end_datetime(self) -> datetime.datetime:
    #     try:
    #         end = self.json["extent"]["temporal"]["interval"][1]
    #     except Exception:
    #         end = "2022-07-20T23:00:00"
    #     return datetime.datetime.fromisoformat(end)

    @property
    def id(self) -> str:
        collection_id = self.json["id"]
        assert isinstance(collection_id, str)
        return collection_id

    def retrieve_process(self) -> Process:
        url = self.get_link_href(rel="retrieve")
        return Process.from_request(
            "get", url, headers=self.headers, session=self.session
        )

    # def submit(
    #     self, accepted_licences: List[Dict[str, Any]] = [], **request: Any
    # ) -> cads_api_client.jobs.JobsAPIClient:
    #     retrieve_process = self.retrieve_process()
    #     status_info = retrieve_process.execute(
    #         inputs=request, accepted_licences=accepted_licences, session=self.session
    #     )
    #     return status_info.make_remote()

    # def retrieve(
    #     self,
    #     target: Optional[str] = None,
    #     retry_options: Dict[str, Any] = {},
    #     accepted_licences: List[Dict[str, Any]] = [],
    #     **request: Any,
    # ) -> str:
    #     remote = self.submit(accepted_licences=accepted_licences, **request)
    #     return remote.download(target, retry_options=retry_options)

    # def multi_retrieve(
    #         self,
    #         target: Optional[str] = None,
    #         retry_options: Dict[str, Any] = {},
    #         accepted_licences: List[Dict[str, Any]] = [],
    #         requests: List[Dict] | Dict = [],
    #         max_updates: int = 10,
    #         max_downloads: int = 2,
    # ):  # TODO in retrieve (composite pattern)
    #
    #     if target and len(requests) > 1 and not os.path.isdir(target):
    #         raise ValueError(f"The target parameter path must be a directory ({target} given instead)")
    #
    #     for request in requests:
    #         request.update({'accepted_licences': accepted_licences})
    #
    #     return multi_retrieve(collection=self, requests=requests,
    #                                          target=target, retry_options=retry_options,
    #                                          max_updates=max_updates, max_downloads=max_downloads)
    #


