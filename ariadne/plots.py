from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.plot_specs import Axes, Figure

# plan_name
# underlying_plan linescan motor type
# underlying_plan xafs trans/fluorescence/ref


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
        if stream_name != 'primary':
            return

        # Find out the plan type.
        plan_name = run.metadata['start'].get('plan_name').split(' ')
        if len(plan_name) > 1:
            plan = plan_name[1]

        # Skip plan if it is not supported.
        if plan not in ['xafs', 'linescan']:
            return

        # Gather the rest of the parameters.
        subtype = plan_name[-1] # trans, ref, fluorescence, I0, It, Ir
        element = run.metadata['start'].get('XDI', {}).get('Element',{}).get('symbol', False)
        fluorescence = f'{element}1+{element}2+{element}3+{element}4' if element else None

        # Look up what goes on the x-axis.
        x_lookup = {'linescan': plan_name[2],
                    'xafs': 'dcm_energy'}
        x_axis = x_lookup[plan]

        # Look up what goes on the y-axis.
        y_lookup = {'I0': ['I0'],
                    'It': ['It/I0'],
                    'Ir': ['Ir/It'],
                    'If': [f'({fluorescence})/I0'],
                    'trans': ['log(I0/It)', 'log(It/Ir)', 'I0', 'It/I0', 'Ir/It'],
                    'fluorescence': [f'({fluorescence})/I0', 'log(I0/It)',
                                     'log(It/Ir)', 'I0', 'It/I0', 'Ir/It'],
                    'ref': ['log(It/Ir)', 'It/I0', 'Ir/It']}
        y_axes = y_lookup[subtype]

        for y_axis in y_axes:
            title = ' '.join(plan_name)
            subtitle = y_axis
            key = f'{title}: {subtitle}'
            if key in self._models:
                models = self._models[key]
            else:
                model, figure = self.single_plot(f'{title}: {subtitle}',x_axis, y_axis)
                models = [model]
                self._models[key] = model

            for model in models:
                model.add_run(run)
                self.plot_builders.append(model)
                self.figures.append(figure)

        return model, figure

    def single_plot(self, title, x, y):
        axes1 = Axes()
        figure = Figure((axes1,), title=title)
        model = Lines(x=x, ys=[y,], max_runs=10, axes=axes1)
        return model, figure
