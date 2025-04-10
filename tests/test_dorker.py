import pytest
from gdorker import Dorker, Logger
from unittest.mock import patch, MagicMock
import requests

def dummy_logger():
    return Logger({'title': True, 'body': False, 'code': False, 'dest': None, 'debug': False})

@patch("gdorker.build")
def test_dorker_search_api_mocked(mock_build):
    # mock the Google API client
    mock_client = MagicMock()
    mock_cse = mock_client.cse.return_value
    mock_list = mock_cse.list.return_value
    mock_list.execute.return_value = {
        'items': [
            {'link': 'https://test.com', 'title': 'Test Page'},
            {'link': 'https://another.com', 'title': 'Another Page'},
        ]
    }
    mock_build.return_value = mock_client

    logger = dummy_logger()
    dorker = Dorker(logger, api_key="test", cse_id="test")

    results = dorker._search("inurl:login", start=1)

    assert len(results) == 2
    assert results[0]['link'] == 'https://test.com'
    assert results[1]['title'] == 'Another Page'
