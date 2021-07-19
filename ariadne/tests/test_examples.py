from databroker._drivers.jsonl import BlueskyJSONLCatalog

def test_from_config():
    catalog = BlueskyJSONLCatalog(
        "./ariadne/tests/*.jsonl",
        name='bmm')
    assert len(catalog)

