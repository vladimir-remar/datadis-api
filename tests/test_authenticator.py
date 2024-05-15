import os
import requests
import pytest
import requests_mock
from src.authenticator import DatadisAuthenticator

# Test for successful authentication
def test_successful_authentication():
    username = os.environ.get("DATADIS_USERNAME")
    password = os.environ.get("DATADIS_PASSWORD")
    with requests_mock.Mocker() as m:
        expected_token = "valid_token"
        m.post(DatadisAuthenticator.base_url, text=expected_token)
        authenticator = DatadisAuthenticator(username, password)
        token = authenticator.get_auth_token()
        assert token == expected_token
        # Assert that the request made by the authenticator is correct
        assert m.called_once
        request = m.request_history[0]
        assert request.method == "POST"
        assert request.url.split('?')[0] == DatadisAuthenticator.base_url  # Ensure base URL without query params



# Test for unsuccessful authentication
def test_unsuccessful_authentication():
    username = os.environ.get("DATADIS_USERNAME")
    password = os.environ.get("DATADIS_PASSWORD")
    error_code = 401  # Unauthorized

    with requests_mock.Mocker() as m:
        m.post(DatadisAuthenticator.base_url, status_code=error_code)
        authenticator = DatadisAuthenticator(username, password)
        with pytest.raises(Exception) as exc_info:
            authenticator.get_auth_token()
        assert f"Error: {error_code}" in str(exc_info.value)
        # Assert that the request made by the authenticator is correct
        assert m.called_once
        request = m.request_history[0]
        assert request.method == "POST"
        assert request.url.split('?')[0] == DatadisAuthenticator.base_url  # Ensure base URL without query params

# Test for server error during authentication
def test_server_error():
    username = os.environ.get("DATADIS_USERNAME")
    password = os.environ.get("DATADIS_PASSWORD")
    error_code = 500  # Internal Server Error

    with requests_mock.Mocker() as m:
        m.post(DatadisAuthenticator.base_url, status_code=error_code)
        authenticator = DatadisAuthenticator(username, password)
        with pytest.raises(Exception) as exc_info:
            authenticator.get_auth_token()
        assert f"Error: {error_code}" in str(exc_info.value)
        # Assert that the request made by the authenticator is correct
        assert m.called_once
        request = m.request_history[0]
        assert request.method == "POST"
        assert request.url.split('?')[0] == DatadisAuthenticator.base_url  # Ensure base URL without query params




# You can add more tests for edge cases like timeouts
