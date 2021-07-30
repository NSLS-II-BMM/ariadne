from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.plot_specs import Axes, Figure

# plan_name
# underlying_plan linescan motor type
# underlying_plan xafs trans/fluorescence/ref


class AutoBMMPlot(AutoPlotter):

    def handle_new_stream(self, run, stream_name):
        if stream_name == 'primary':

            # Find out the plan type.
            plan_name = run.metadata['start'].get('plan_name').split(' ')
            if len(plan_name) > 1:
                plan = plan_name[1] # xafs or linescan

            # Skip plan if it is not supported.
            if plan not in ['xafs', 'linescan']:
                return

            # Gather the rest of the parameters.
            subtype = plan_name[-1] # trans, ref, fluorescence, I0, It, Ir
            element = run.metadata['start'].get('XDI', {}).get('Element',{}).get('Symbol')
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
                subtitle = y_axis.replace('/','_div_')
                model, figure = self.single_plot(f'{title}: {subtitle}', x_axis, y_axis)
                model.add_run(run)
                self.plot_builders.append(model)
                self.figures.append(figure)

    def single_plot(self, title, x, y):
        axes1 = Axes()
        figure = Figure((axes1,), title=title)
        model = Lines(x=x, ys=[y,], max_runs=1, axes=axes1)
        return model, figure
