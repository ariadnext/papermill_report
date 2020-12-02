import json
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from tornado.httpclient import HTTPClientError


async def test_get_templates(http_server_client):
    response = await http_server_client.fetch("/api/templates/")
    assert response.code == 200
    answer = json.loads(response.body.decode("utf-8"))
    assert answer["templates"] == [
        {
            "parameters": [
                {
                    "default": "2",
                    "help": "Beautiful",
                    "inferred_type_name": "int",
                    "name": "a",
                }
            ],
            "path": "notebook1.ipynb",
        },
        {
            "parameters": [
                {
                    "default": "'The famous B'",
                    "help": "Beautiful",
                    "inferred_type_name": "str",
                    "name": "b",
                }
            ],
            "path": "subfolder/notebook2.ipynb",
        },
    ]


async def test_get_templates_subfolder(http_server_client):
    with patch("papermill_report.handlers.ReportHandler.report_path", "subfolder"):
        response = await http_server_client.fetch("/api/templates/")
        assert response.code == 200
        answer = json.loads(response.body.decode("utf-8"))
        assert answer["templates"] == [
            {
                "parameters": [
                    {
                        "default": "'The famous B'",
                        "help": "Beautiful",
                        "inferred_type_name": "str",
                        "name": "b",
                    }
                ],
                "path": "notebook2.ipynb",
            },
        ]


@pytest.mark.parametrize("endpoint", ["/hello", "/my_script.py", "/hello/"])
async def test_bad_template_url(http_server_client, endpoint):
    with pytest.raises(HTTPClientError, match="HTTP 404:"):
        await http_server_client.fetch(endpoint)


async def test_generate_template(http_server_client):
    response = await http_server_client.fetch("/subfolder/notebook2.ipynb")
    assert response.code == 200
    assert "The famous Beaver" in response.body.decode("utf-8")


async def test_generate_template_with_parameters(http_server_client):
    param_b = "The agile w"
    response = await http_server_client.fetch(
        "/subfolder/notebook2.ipynb?" + urlencode(dict(b="The agile w"))
    )
    assert response.code == 200
    assert param_b + "eaver" in response.body.decode("utf-8")
