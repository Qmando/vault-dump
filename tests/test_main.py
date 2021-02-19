import os
import requests

import vault_dump.main

import mock
import pytest

@pytest.fixture(autouse=True)
def mock_shutil():
    with mock.patch("vault_dump.main.shutil") as _fixture:
        yield _fixture

@pytest.fixture(autouse=True)
def mock_request():
    with mock.patch("vault_dump.main.requests.request") as _fixture:
        yield _fixture

@pytest.fixture(autouse=True)
def mock_path():
    with mock.patch('vault_dump.main.Path') as _fixture:
        yield _fixture

@pytest.fixture(autouse=True)
def mock_os():
    with mock.patch('vault_dump.main.os') as _fixture:
        yield _fixture


def test_no_authentication_token_provided(mock_os):
    mock_os.getenv = mock.Mock(return_value = None)
    with pytest.raises(Exception) as e:
        vault_dump.main.main()

    assert "You need to provide a vault token" in str(e)


def test_invalid_authentication_token_provided(mock_os, mock_request):
    mock_request.return_value = mock.Mock(json=mock.Mock(return_value = {"errors": ["permission denied"]}))
    with pytest.raises(Exception) as e:
        vault_dump.main.main()

    assert "Permission denied. Did you provide a valid Vault Token" in str(e)


def test_get_policies(mock_request, mock_shutil, mock_path):
    def mock_responses(*args, **kwargs):
        if args[-1].endswith("policy"):
            return mock.Mock(json=mock.Mock(return_value={"policies": ["a", "b", "c", "root"]}))
        elif "policy" in args[-1]:
            return mock.Mock(json=mock.Mock(return_value={"rules": f"{args[-1][-1]}_policy_text"}))
        else:
            return mock.Mock(json=mock.Mock(return_value={}))
    mock_request.side_effect = mock_responses
    vault_dump.main.get_policies(".", "token", "addr")


def test_get_auth_backends(mock_request, mock_shutil, mock_path):
    def mock_responses(*args, **kwargs):
        if args[-1].endswith("auth"):
            return mock.Mock(json=mock.Mock(return_value=
                {"data": {"key1_no_config": {"k1": "v1", "type": "ldap"}, "key2_with_config": {"k2": "v2", "type": "token"}}}))
        elif args[-1].endswith("config"):
            if "key1" in args[-1]:
                return mock.Mock(status_code=404, json=mock.Mock(return_value={}))
            elif "key2" in args[-1]:
                return mock.Mock(json=mock.Mock(return_value={"data":{}}))
        else:
            return mock.Mock(json=mock.Mock(return_value={}))
    mock_request.side_effect = mock_responses
    with mock.patch("vault_dump.main.get_auth_roles"): # tested separately
        vault_dump.main.get_auth_backends(".", "token", "addr")


@pytest.mark.parametrize("auth_type, status_code", [pytest.param("token", 404), pytest.param("ldap", 200)])
def test_get_auth_roles(mock_request, mock_shutil, mock_path, auth_type, status_code):
    def mock_responses(*args, **kwargs):
        if args[-1].endswith("roles"):
            return mock.Mock(status_code=status_code, json=mock.Mock(return_value=
                {"data": {"keys": {"key1_no_config": {"k1": "v1"}, "key2_with_config": {"k2": "v2"}}}}))
        elif "role" in args[-1]:
            return mock.Mock(json=mock.Mock(return_value={"data":{}}))
        else:
            return mock.Mock(json=mock.Mock(return_value={}))
    mock_request.side_effect = mock_responses
    vault_dump.main.get_auth_roles(".", "token", "addr", "auth_path", auth_type)


def test_get_mounts(mock_request, mock_shutil, mock_path):
    def mock_responses(*args, **kwargs):
        if args[-1].endswith("mounts"):
            return mock.Mock(json=mock.Mock(return_value=
                {
                    "data": {
                        "key1_no_config": {"k1": "v1", "type": "pki"},
                        "key2_with_config": {"k2": "v2", "type": "other"},
                        "key3_with_config": {"k3": "v3", "type": "pki"}
                    }
                }))
        elif args[-1].endswith("config") or args[-1].endswith("urls") or args[-1].endswith("crl"):
            if "key1" in args[-1]:
                return mock.Mock(status_code=404, json=mock.Mock(return_value={}))
            elif "key2" in args[-1]:
                return mock.Mock(json=mock.Mock(return_value={"data":{"key": "value\nwith\nnewlines\n"}}))
            elif "key3" in args[-1]:
                return mock.Mock(json=mock.Mock(return_value={"data":{}}))
        else:
            return mock.Mock(json=mock.Mock(return_value={"data":{}}))
    mock_request.side_effect = mock_responses
    vault_dump.main.get_mounts(".", "token", "addr")


def test_get_audit_backends(mock_request, mock_shutil, mock_path):
    def mock_responses(*args, **kwargs):
        if args[-1].endswith("audit"):
            return mock.Mock(json=mock.Mock(return_value=
                {"data": {"key1_no_config": {"k1": "v1"}, "key2_with_config": {"k2": "v2"}}}))
        else:
            return mock.Mock(json=mock.Mock(return_value={}))
    mock_request.side_effect = mock_responses
    vault_dump.main.get_audit_backends(".", "token", "addr")


def test_main(mock_request, mock_os, mock_shutil, mock_path):
    mock_shutil.rmtree = mock.Mock(side_effect=FileNotFoundError)
    vault_dump.main.main()