from .base import BaseStream
from typing import Any, Iterable, List, Mapping, Optional

class Supplies(BaseStream):

    def __init__(self, authenticator, authorized_nif):
        super().__init__(authenticator, authorized_nif)

    def path(self, **kwargs):
        return "get-supplies"
    
    def parse_response(self, response, **kwargs):
        data = response.json()

        yield from data

class Comsumption(BaseStream):

    def __init__(self, authenticator, authorized_nif, parent, start_date):
        super().__init__(authenticator, authorized_nif)
        self.parent = parent
        self.start_date = start_date

    def stream_slices(
        self, **kwargs
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        
        for record in self.parent.read_records():
            yield {"parent": record}
    
    def read_records(
        self,
        cursor_field: Optional[List[str]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable:
        
        for stream_slice in self.stream_slices():
            yield from self._read_pages(
                lambda req, res, state, _slice: self.parse_response(res, stream_slice=_slice, stream_state=state), stream_slice, stream_state
            )
    
    def request_params(self, **kwargs):
        params = super().request_params(**kwargs)
        new_params = {
            "cups": kwargs["stream_slice"]["parent"]["cups"],
            "distributorCode": kwargs["stream_slice"]["parent"]["distributorCode"],
            "startDate": self.start_date,
            "endDate": self.start_date,
            "measurementType": 0,
            "pointType": kwargs["stream_slice"]["parent"]["pointType"]
        }
        params.update(new_params)
        return params
    
    def parse_response(self, response, **kwargs):
        data = response.json()
        for e in data:
            # e["cups"] = kwargs["stream_slice"]["parent"]["cups"
            e["distributorCode"] = kwargs["stream_slice"]["parent"]["distributorCode"]
            e["pointType"] = kwargs["stream_slice"]["parent"]["pointType"]
            yield e
    
    def path(self, **kwargs):
        return "get-consumption-data"