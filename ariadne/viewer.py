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
    def __init__(self):
        super().__init__()
        self._models = {}

        self.plot_builders.events.removed.connect(self._on_plot_builder_removed)

    def _on_plot_builder_removed(self, event):
        plot_builder = event.item
        for key in list(self._models):
            for line in self._models[key]:
                if line == plot_builder:
                    del self._models[key]

    def handle_new_stream(self, run, stream_name):
        # TODO: revisit this for xafs plan to_plot option
        if stream_name != "primary":
            return

        xx = run.metadata["start"]["motors"][0]
        to_plot = run.metadata["start"].get("plot_request", "It")
        models = []
        figures = []

        if to_plot == "It":
            y_keys = (("log(I0/It)",), ("I0",))
        elif to_plot == "I0":
            y_keys = (("I0",),)
        elif to_plot == "Ir":
            y_keys = (("log(I0/It)", "I0"),)

        for y_key in y_keys:
            key = (xx, y_key, to_plot)
            try:
                models = self._models[key]
            except KeyError:
                x, ys, to_plot = key
                models = []
                axes_list = []
                for y in ys:
                    axes = Axes()
                    axes_list.append(axes)
                    models.append(Lines(x=x, ys=[y], max_runs=3, axes=axes))
                figure = Figure(tuple(axes_list), title=y)
                self._models[key] = models
                self.figures.append(figure)
            finally:
                for model in models:
                    model.add_run(run)
                    self.plot_builders.append(model)


class ViewerModel:
    """
    This encapsulates on the models in the application.
    """

    def __init__(self):
        self.search = SearchWithButton(SETTINGS.catalog, columns=SETTINGS.columns)
        # auto_plot_builder for live plotting
        self.live_auto_plot_builder = AutoBMMPlot()
        # auto_plot_builder for databroker plotting
        self.databroker_auto_plot_builder = AutoBMMPlot()

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
                dispatcher.subscribe(stream_documents_into_runs(self.live_auto_plot_builder.add_run))
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

                self.dispatcher.subscribe(stream_documents_into_runs(self.live_auto_plot_builder.add_run))

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

        # Customize Run Engine model for BMM:
        #   - name of the module that contains custom code modules
        #     (conversion of spreadsheets to sequences of plans)
        self.run_engine.qserver_custom_module_name = "bluesky-httpserver-bmm"
        #   - list of names of spreadsheet types
        self.run_engine.plan_spreadsheet_data_types = ["wheel_xafs"]

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
