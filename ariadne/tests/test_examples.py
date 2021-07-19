import os
from pathlib import Path
import pytest
import tempfile

from databroker._drivers.jsonl import BlueskyJSONLCatalog
from databroker.core import BlueskyRunFromGenerator

from bluesky_widgets.utils.streaming import stream_documents_into_runs

from bluesky_live.run_builder import RunBuilder

from ..kafka_previews import export_thumbnails_when_complete

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

@pytest.mark.parametrize(
    "uid,titles",
    [
        ("12a63104-f8e1-4491-9f3e-e03a30575e33", ["It_divided_by_I0", "I0"]),
    ]
)
def test_export_(catalog, uid, titles):
    # delete files first
    documents = catalog[uid].canonical(fill='no')
    # print(len(list(documents)))
    plotting = stream_documents_into_runs(export_thumbnails_when_complete)
    counter = 0
    for name, doc in documents:
        print(counter)
        plotting(name, doc)
        counter += 1
    for title in titles:
        plot = os.path.join(tempfile.gettempdir(), "bluesky_widgets_example", uid, f"{title}.png")
        assert Path(plot).exists()

# test Qt plots
