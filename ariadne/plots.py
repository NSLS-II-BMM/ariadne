from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.plot_specs import Axes, Figure


class AutoBMMPlot(AutoPlotter):

    def handle_new_stream(self, run, stream_name):
        if stream_name == 'primary':
            #getattr(self, run.metadata['plan_name'])(run, stream_name)
            models, figures = getattr(self, run.metadata.get('plot_request', 'It')(run, stream_name)

            for model in models:
                model.add_run(run)
                self.plot_builders.append(model)
            self.figures.extend(figures)

    def It(self, run, stream_name):
        x_values = run.metadata['start']['motors'][0]
        models = []
        figures = []

        axes1 = Axes()
        figure1 = Figure((axes1,), title="It/I0")
        figures.append(figure1)
        models.append(
            Lines(x=x_values, ys=['It/I0',], max_runs=1, axes=axes1)
        )

        axes2 = Axes()
        figure2 = Figure((axes2,), title="I0")
        figures.append(figure2)
        models.append(
            Lines(x=x_values, ys=['I0',],    max_runs=1, axes=axes2)
        )

        return models, figures

    def I0(self, run, stream_name):
        x_values = run.metadata['start']['motors'][0]
        models = []
        figures = []

        axes = Axes()
        figure = Figure((axes,), title="I0")
        figures.append(figure)
        models.append(
            Lines(x=x_values, ys=['I0',],    max_runs=1, axes=axes)
        )

        return models, figures

    def Ir(self, run, stream_name):
        x_values = run.metadata['start']['motors'][0]
        models = []
        figures = []

        axes1 = Axes()
        axes2 = Axes()
        figure = Figure((axes1, axes2), title='It and I0')
        figures.append(figure)
        models.append(
            Lines(x=x_values, ys=['It/I0',], max_runs=1, axes=axes1)
        )
        models.append(
            Lines(x=x_values, ys=['I0',],    max_runs=1, axes=axes2)

        return models, figures
