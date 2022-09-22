from __future__ import annotations

import functools
import os
import time
import urllib
from typing import Any, Dict, List, Optional, Type, TypeVar

import attrs
import multiurl
import requests
from owslib import ogcapi

T_ApiResponse = TypeVar("T_ApiResponse", bound="ApiResponse")


class ProcessingFailedError(RuntimeError):
    pass


class DownloadError(RuntimeError):
    pass


@attrs.define(slots=False)
class ApiResponse:
    response: requests.Response

    @classmethod
    def from_request(
        cls: Type[T_ApiResponse], *args: Any, **kwargs: Any
    ) -> T_ApiResponse:
        # TODO:
        # - add retry on idempotent calls
        # - use HTTP session
        response = multiurl.robust(requests.request)(*args, **kwargs)
        response.raise_for_status()

        self = cls(response)
        return self

    @functools.cached_property
    def json(self) -> Dict[str, Any]:
        return self.response.json()  # type: ignore

    def get_links(self, rel: Optional[str] = None) -> List[Dict[str, str]]:
        links = []
        for link in self.json.get("links", []):
            if rel is not None and link.get("rel") == rel:
                links.append(link)
        return links

    def get_link_href(self, **kwargs: str) -> str:
        links = self.get_links(**kwargs)
        if len(links) != 1:
            raise RuntimeError(f"link not found or not unique {kwargs}")
        return links[0]["href"]


@attrs.define
class ProcessList(ApiResponse):
    def process_ids(self) -> List[str]:
        return [proc["id"] for proc in self.json["processes"]]


@attrs.define
class Process(ApiResponse):
    def execute(self, inputs: Dict[str, Any], **kwargs: Any) -> StatusInfo:
        assert "json" not in kwargs
        url = f"{self.response.request.url}/execute"
        return StatusInfo.from_request("post", url, json={"inputs": inputs}, **kwargs)


@attrs.define(slots=False)
class Remote:
    url: str
    sleep_max: int = 120

    @functools.cached_property
    def request_uid(self) -> str:
        return self.url.rpartition("/")[2]

    @property
    def status(self) -> str:
        # TODO: cache responses for a timeout (possibly reported nby the server)
        json = multiurl.robust(requests.get)(self.url).json()
        return json["status"]  # type: ignore

    def wait_on_result(self) -> None:
        sleep = 1.0
        last_status = self.status
        while True:
            status = self.status
            if last_status != status:
                print(status)
            if status == "successful":
                break
            elif status == "failed":
                raise ProcessingFailedError()
            elif status in ("accepted", "running"):
                sleep *= 1.5
                if sleep > self.sleep_max:
                    sleep = self.sleep_max
            else:
                raise ProcessingFailedError(f"Unknown API state {status!r}")
            time.sleep(sleep)

    def _download_result(self, target: Optional[str] = None) -> str:
        # TODO: get the results URL from link if it exist
        request_response = multiurl.robust(requests.get)(self.url)
        response = ApiResponse(request_response)
        try:
            results_url = response.get_link_href(rel="results")
        except RuntimeError:
            results_url = f"{self.url}/results"
        request_result = multiurl.robust(requests.get)(results_url)
        results = Results(request_result)
        return results.download(target)

    def download(self, target: Optional[str]) -> str:
        self.wait_on_result()
        return self._download_result(target)


@attrs.define
class StatusInfo(ApiResponse):
    def make_remote(self) -> Remote:
        if self.response.request.method == "POST":
            url = self.get_link_href(rel="monitor")
        else:
            url = self.get_link_href(rel="self")
        return Remote(url)


@attrs.define
class JobList(ApiResponse):
    def job_ids(self) -> List[str]:
        return [job["id"] for job in self.json["jobs"]]


@attrs.define
class Results(ApiResponse):
    def get_result_href(self) -> Optional[str]:
        asset = self.json.get("asset", {}).get("value", {})
        result_href = asset.get("href")
        assert isinstance(result_href, str) or result_href is None
        return result_href

    def get_result_checksum(self) -> Optional[str]:
        asset = self.json.get("asset", {}).get("value", {})
        result_checksum = asset.get("file:checksum")
        assert isinstance(result_checksum, str) or result_checksum is None
        return result_checksum

    def get_result_size(self) -> Optional[int]:
        asset = self.json.get("asset", {}).get("value", {})
        size = asset["file:size"]
        return int(size)

    def download(self, target: Optional[str] = None, timeout: int = 60) -> str:
        result_href = self.get_result_href()
        url = urllib.parse.urljoin(self.response.url, result_href)
        if target is None:
            parts = urllib.parse.urlparse(url)
            target = parts.path.strip("/").split("/")[-1]

        multiurl.download(url, stream=True, target=target, timeout=timeout)
        target_size = os.path.getsize(target)
        size = self.get_result_size()
        if size:
            if target_size != size:
                raise Exception(
                    "Download failed: downloaded %s byte(s) out of %s"
                    % (target_size, size)
                )
        return target


class Processing(ogcapi.API):  # type: ignore
    supported_api_version = "v1"

    def __init__(
        self, url: str, force_exact_url: bool = False, *args: Any, **kwargs: Any
    ) -> None:
        if not force_exact_url:
            url = f"{url}/{self.supported_api_version}"
        # FIXME: ogcapi.API crashes if the landing page is non compliant!
        try:
            super().__init__(url, *args, **kwargs)
        except Exception:
            pass

    def processes(self) -> ProcessList:
        url = self._build_url("processes")
        return ProcessList.from_request("get", url)

    def process(self, process_id: str) -> Process:
        url = self._build_url(f"processes/{process_id}")
        return Process.from_request("get", url)

    def process_execute(
        self, process_id: str, inputs: Dict[str, Any], **kwargs: Any
    ) -> StatusInfo:
        assert "json" not in kwargs
        url = self._build_url(f"processes/{process_id}/execute")
        return StatusInfo.from_request("post", url, json={"inputs": inputs}, **kwargs)

    def jobs(self) -> JobList:
        url = self._build_url("jobs")
        return JobList.from_request("get", url)

    def job(self, job_id: str) -> StatusInfo:
        url = self._build_url(f"jobs/{job_id}")
        return StatusInfo.from_request("get", url)

    def job_results(self, job_id: str) -> Results:
        url = self._build_url(f"jobs/{job_id}/results")
        return Results.from_request("get", url)

    # convenience methods

    def make_remote(self, job_id: str) -> Remote:
        url = self._build_url(f"jobs/{job_id}")
        return Remote(url)

    def download_result(self, job_id: str, target: Optional[str]) -> str:
        # NOTE: the remote waits for the result to be available
        return self.make_remote(job_id).download(target)