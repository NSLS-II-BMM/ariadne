import os

from bluesky_widgets.models.run_engine_client import RunEngineClient
from bluesky_widgets.qt import Window
from bluesky_widgets.models.plot_specs import Axes, Figure
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.auto_plot_builders import AutoPlotter

from .widgets import QtViewer
from .models import SearchWithButton
from .settings import SETTINGS


class AutoBMMPlot(AutoPlotter):
    def handle_new_stream(self, run, stream_name):
        if stream_name != "primary":
            return

        xx = run.metadata["start"]["motors"][0]
        to_plot = run.metadata["start"].get("plot_request", "It")
        models = []
        figures = []
        if to_plot == "It":
            axes1 = Axes()
            figure1 = Figure((axes1,), title="It/I0")
            figures.append(figure1)
            models.append(Lines(x=xx, ys=["It/I0"], max_runs=1, axes=axes1))
            axes2 = Axes()
            figure2 = Figure((axes2,), title="I0")
            figures.append(figure2)
            models.append(Lines(x=xx, ys=["I0"], max_runs=1, axes=axes2))
        elif to_plot == "I0":
            axes = Axes()
            figure = Figure((axes,), title="I0")
            figures.append(figure)
            models.append(Lines(x=xx, ys=["I0"], max_runs=1, axes=axes))
        elif to_plot == "Ir":
            axes1 = Axes()
            axes2 = Axes()
            figure = Figure((axes1, axes2), title="It and I0")
            figures.append(figure)
            models.append(Lines(x=xx, ys=["It/I0"], max_runs=1, axes=axes1))
            models.append(Lines(x=xx, ys=["I0"], max_runs=1, axes=axes2))
        else:
            # Plot nothing.
            pass
        for model in models:
            model.add_run(run)
            self.plot_builders.append(model)
        self.figures.extend(figures)


class ViewerModel:
    """
    This encapsulates on the models in the application.
    """

    def __init__(self):
        self.search = SearchWithButton(SETTINGS.catalog, columns=SETTINGS.columns)
        self.auto_plot_builder = AutoBMMPlot()

        self.run_engine = RunEngineClient(zmq_server_address=os.environ.get("QSERVER_ZMQ_ADDRESS", None))


class Viewer(ViewerModel):
    """
    This extends the model by attaching a Qt Window as its view.

    This object is meant to be exposed to the user in an interactive console.
    """

    def __init__(self, *, show=True, title="Demo App"):
        # TODO Where does title thread through?
        super().__init__()
        for source in SETTINGS.subscribe_to:
            if source["protocol"] == "zmq":
                from bluesky_widgets.qt.zmq_dispatcher import RemoteDispatcher
                from bluesky_widgets.utils.streaming import stream_documents_into_runs

                zmq_addr = source["zmq_addr"]

                dispatcher = RemoteDispatcher(zmq_addr)
                dispatcher.subscribe(stream_documents_into_runs(self.auto_plot_builder.add_run))
                dispatcher.start()

            elif source["protocol"] == "kafka":
                from bluesky_kafka import RemoteDispatcher
                from bluesky_widgets.utils.streaming import stream_documents_into_runs
                from qtpy.QtCore import QThread

                bootstrap_servers = source["servers"]
                topics = source["topics"]

                consumer_config = {"auto.commit.interval.ms": 100, "auto.offset.reset": "latest"}

                self.dispatcher = RemoteDispatcher(
                    topics=topics,
                    bootstrap_servers=bootstrap_servers,
                    group_id="widgets_test",
                    consumer_config=consumer_config,
                )

                self.dispatcher.subscribe(stream_documents_into_runs(self.auto_plot_builder.add_run))

                class DispatcherStart(QThread):
                    def __init__(self, dispatcher):
                        super().__init__()
                        self._dispatcher = dispatcher

                    def run(self):
                        self._dispatcher.start()

                self.dispatcher_thread = DispatcherStart(self.dispatcher)
                self.dispatcher_thread.start()

            else:
                print(f"Unknown protocol: {source['protocol']}")

        widget = QtViewer(self)
        self._window = Window(widget, show=show)

    @property
    def window(self):
        return self._window

    def show(self):
        """Resize, show, and raise the window."""
        self._window.show()

    def close(self):
        """Close the window."""
        self._window.close()
