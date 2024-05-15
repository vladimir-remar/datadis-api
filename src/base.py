import requests
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Union, List, Iterable, Tuple, Callable
from urllib.parse import urljoin
from .exceptions import RequestBodyException, UserDefinedBackoffException, DefaultBackoffException
from .rate_limiting import default_backoff_handler, user_defined_backoff_handler
from .custom_logging import logger
from .utils import JsonType

BODY_REQUEST_METHODS = ("GET", "POST", "PUT", "PATCH")


class BaseStream(ABC):
    url_base = "https://datadis.es/api-private/api/"

    def __init__(self, authenticator: requests.auth.AuthBase, authorized_nif: str):
        self.authenticator = authenticator
        self.authorized_nif = authorized_nif
        self._session = requests.Session()
        self.logger = logger
    
    @abstractmethod
    def path(
        self,
        *,
        stream_state: Optional[Mapping[str, Any]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> str:
        ...
    
    @classmethod
    def _join_url(cls, url_base: str, path: str) -> str:
        return urljoin(url_base, path)
    
    @property
    def http_method(self) -> str:
        """
        Override if needed. See get_request_data/get_request_json if using POST/PUT/PATCH.
        """
        return "GET"

    @property
    def raise_on_http_errors(self) -> bool:
        """
        Override if needed. If set to False, allows opting-out of raising HTTP code exception.
        """
        return True
    
    def request_params(self, **kwargs):
        return {
            "authorizedNif": self.authorized_nif
        }
    
    def request_kwargs(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        Override to return a mapping of keyword arguments to be used when creating the HTTP request.
        Any option listed in https://docs.python-requests.org/en/latest/api/#requests.adapters.BaseAdapter.send for can be returned from
        this method. Note that these options do not conflict with request-level options such as headers, request params, etc..
        """
        return {}

    def request_headers(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        Override to return any non-auth headers. Authentication headers will overwrite any overlapping headers returned from this method.
        """
        return {}
    
    def request_body_data(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Union[Mapping[str, Any], str]]:
        """
        Override when creating POST/PUT/PATCH requests to populate the body of the request with a non-JSON payload.

        If returns a ready text that it will be sent as is.
        If returns a dict that it will be converted to a urlencoded form.
        E.g. {"key1": "value1", "key2": "value2"} => "key1=value1&key2=value2"

        At the same time only one of the 'request_body_data' and 'request_body_json' functions can be overridden.
        """
        return None

    def request_body_json(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Mapping[str, Any]]:
        """
        Override when creating POST/PUT/PATCH requests to populate the body of the request with a JSON payload.

        At the same time only one of the 'request_body_data' and 'request_body_json' functions can be overridden.
        """
        return None
    
    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None
    
    def should_retry(self, response: requests.Response) -> bool:

        return response.status_code == 429 or 500 <= response.status_code < 600
    
    def _create_prepared_request(
        self,
        path: str,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, str]] = None,
        json: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, Mapping[str, Any]]] = None,
    ) -> requests.PreparedRequest:
        url = self._join_url(self.url_base, path)
        query_params = params or {}
        args = {"method": self.http_method, "url": url, "headers": headers, "params": query_params}
        if self.http_method.upper() in BODY_REQUEST_METHODS:
            if json and data:
                raise RequestBodyException(
                    "At the same time only one of the 'request_body_data' and 'request_body_json' functions can return data"
                )
            elif json:
                args["json"] = json
            elif data:
                args["data"] = data
        prepared_request: requests.PreparedRequest = self._session.prepare_request(requests.Request(**args))

        return prepared_request
    
    def backoff_time(self, response: requests.Response) -> Optional[float]:

        return None
    
    def error_message(self, response: requests.Response) -> str:

        return ""

    def _send(self, request: requests.PreparedRequest, request_kwargs: Mapping[str, Any]) -> requests.Response:

        self.logger.debug(
            "Making outbound API request", extra={"headers": request.headers, "url": request.url, "request_body": request.body}
        )
        response: requests.Response = self._session.send(request, **request_kwargs)

        # Evaluation of response.text can be heavy, for example, if streaming a large response
        # Do it only in debug mode

        if self.should_retry(response):
            custom_backoff_time = self.backoff_time(response)
            error_message = self.error_message(response)
            if custom_backoff_time:
                raise UserDefinedBackoffException(
                    backoff=custom_backoff_time, request=request, response=response, error_message=error_message
                )
            else:
                raise DefaultBackoffException(request=request, response=response, error_message=error_message)
        elif self.raise_on_http_errors:
            # Raise any HTTP exceptions that happened in case there were unexpected ones
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                self.logger.error(response.text)
                raise exc
        return response
    
    @classmethod
    def parse_response_error_message(cls, response: requests.Response) -> Optional[str]:

        # default logic to grab error from common fields
        def _try_get_error(value: Optional[JsonType]) -> Optional[str]:
            if isinstance(value, str):
                return value
            elif isinstance(value, list):
                errors_in_value = [_try_get_error(v) for v in value]
                return ", ".join(v for v in errors_in_value if v is not None)
            elif isinstance(value, dict):
                new_value = (
                    value.get("message")
                    or value.get("messages")
                    or value.get("error")
                    or value.get("errors")
                    or value.get("failures")
                    or value.get("failure")
                    or value.get("detail")
                )
                return _try_get_error(new_value)
            return None

        try:
            body = response.json()
            return _try_get_error(body)
        except requests.exceptions.JSONDecodeError:
            return None
    
    def _send_request(self, request: requests.PreparedRequest, request_kwargs: Mapping[str, Any]) -> requests.Response:

        max_tries = 5

        max_time = 60 * 10

        retry_factor = 5

        if max_tries is not None:
            max_tries = max(0, max_tries) + 1

        user_backoff_handler = user_defined_backoff_handler(max_tries=max_tries, max_time=max_time)(self._send)
        backoff_handler = default_backoff_handler(max_tries=max_tries, max_time=max_time, factor=retry_factor)
        return backoff_handler(user_backoff_handler)(request, request_kwargs)

    @abstractmethod
    def parse_response(
        self,
        response: requests.Response,
        *,
        stream_state: Mapping[str, Any],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        ...
    
    def read_records(
        self,
        cursor_field: Optional[List[str]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable:
        yield from self._read_pages(
            lambda req, res, state, _slice: self.parse_response(res, stream_slice=_slice, stream_state=state), stream_slice, stream_state
        )

    def _read_pages(
        self,
        records_generator_fn: Callable[
            [requests.PreparedRequest, requests.Response, Mapping[str, Any], Optional[Mapping[str, Any]]], Iterable
        ],
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable:
        stream_state = stream_state or {}
        pagination_complete = False
        next_page_token = None
        while not pagination_complete:
            request, response = self._fetch_next_page(stream_slice, stream_state, next_page_token)
            yield from records_generator_fn(request, response, stream_state, stream_slice)

            next_page_token = self.next_page_token(response)
            if not next_page_token:
                pagination_complete = True

        # Always return an empty generator just in case no records were ever yielded
        yield from []

    def _fetch_next_page(
        self,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[requests.PreparedRequest, requests.Response]:
        request_headers = self.request_headers(stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token)
        request = self._create_prepared_request(
            path=self.path(stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token),
            headers=dict(request_headers, **self.authenticator.get_auth_header()),
            params=self.request_params(stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token),
            json=self.request_body_json(stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token),
            data=self.request_body_data(stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token),
        )
        request_kwargs = self.request_kwargs(stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token)

        response = self._send_request(request, request_kwargs)
        return request, response