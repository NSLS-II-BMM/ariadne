import os
import pytest
import tempfile
from pathlib import Path

from databroker._drivers.jsonl import BlueskyJSONLCatalog
from databroker.core import BlueskyRunFromGenerator
from bluesky_widgets.utils.streaming import stream_documents_into_runs
from bluesky_live.run_builder import RunBuilder
from ..kafka_previews import export_thumbnails_when_complete


@pytest.fixture(scope='module')
def catalog():
    catalog = BlueskyJSONLCatalog(
        f"{Path(__file__).parent.resolve()}/*.jsonl",
        name='bmm')
    return catalog


def test_from_config(catalog):
    assert len(catalog)


@pytest.mark.parametrize(
    "uid,titles",
    [
        ("1dccff46-2576-4da2-8971-4de1ee4e98b7", ["It_divided_by_I0", "I0"]),
        ("d748dbdc-cec4-4211-b626-801f1799cb56", ["I0"]),
        ("ac694ff6-2444-49af-8898-bfa23d99c28c", ["It and I0"]),
    ]
)
def test_export_(catalog, uid, titles):
    plotter = stream_documents_into_runs(export_thumbnails_when_complete)

    for name, doc in catalog[uid].canonical(fill='no'):
        plotter(name, doc)

    for title in titles:
        plot_file = os.path.join(tempfile.gettempdir(),"ariadne",
                                 uid, f"{title}.png")
        assert Path(plot_file).exists()
        os.remove(plot_file)
