"""
Extending and supplementing the models from bluesky-widgets
"""
from bluesky_widgets.models.search import Search
from bluesky_widgets.utils.event import Event


class SearchWithButton(Search):
    """
    A Search model with a method to handle a click event.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events.add(view=Event)


class RunAndView:
    def __init__(self, run_engine, live_auto_plot_builder):
        self.run_engine = run_engine
        self.live_auto_plot_builder = live_auto_plot_builder


class SearchAndView:
    def __init__(self, search, databroker_auto_plot_builder):
        self.search = search
        self.databroker_auto_plot_builder = databroker_auto_plot_builder
        self.search.events.view.connect(self._on_view)

        self._figures_to_lines = {}
        self.databroker_auto_plot_builder.figures.events.added.connect(self._on_figure_added)

    def _on_view(self, event):
        catalog = self.search.selection_as_catalog
        if catalog is None:
            return
        for uid, run in catalog.items():
            self.databroker_auto_plot_builder.add_run(run)

    def _on_figure_added(self, event):
        figure = event.item
        self._figures_to_lines[figure.uuid] = []
        for builder in self.databroker_auto_plot_builder.plot_builders:
            if builder.axes.figure.uuid == figure.uuid:
                self._figures_to_lines[figure.uuid].append(builder)
