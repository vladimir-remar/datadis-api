
import requests
from requests.auth import AuthBase
from typing import Any, Mapping


class DatadisAuthenticator(AuthBase):
    base_url = "https://datadis.es/nikola-auth/tokens/login"
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def request_params(self):
        params = {
            "username": self.username,
            "password": self.password
        }
        print(params)
        return params
    
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_auth_token(self):

        response = requests.post(self.base_url, params=self.request_params(), timeout=60)
        response.raise_for_status()
        if response.status_code == 200:
            parsed_response = response.text
            return str(parsed_response).strip()
        else:
            raise Exception(f"Error: {response.status_code}")

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Attach the HTTP headers required to authenticate on the HTTP request"""
        request.headers.update(self.get_auth_header())
        return request

    def get_auth_header(self) -> Mapping[str, Any]:
        """HTTP header to set on the requests"""
        return {"Authorization": f"Bearer {self.get_auth_token()}"}
