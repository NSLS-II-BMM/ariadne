import pytest

from databroker._drivers.jsonl import BlueskyJSONLCatalog

@pytest.fixture(scope='module')
def catalog():
    catalog = BlueskyJSONLCatalog(
        "./ariadne/tests/*.jsonl",
        name='bmm')
    return catalog

def test_from_config(catalog):
    #catalog = BlueskyJSONLCatalog(
    #    "./ariadne/tests/*.jsonl",
    #    name='bmm')
    assert len(catalog)

