from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.plot_specs import Axes, Figure

# plan_name
# underlying_plan linescan motor type
# underlying_plan xafs trans/fluorescence/ref


class AutoBMMPlot(AutoPlotter):

    def handle_new_stream(self, run, stream_name):
        if stream_name == 'primary':

            plan_name = run.metadata['start'].get('plan_name').split(' ')
            plan = plan_name[1] # xafs or linescan
            subtype = plan_name[-1] # trans, ref, fluorescence, I0, It, Ir

            if plan == 'linescan':
                x_axis = plan_name[2]
            elif plan == 'xafs':
                x_axis = 'dcm_energy'
            else:
                return

            try:
                element = run.metadata['start']['XDI']['Element']['Symbol']
                fluorescence_signal = f'{element}1+{element}2+{element}3+{element}4'
            except KeyError:
                element = None
                fluorescence_signal = None

            plot_lookup = {'I0': ['I0'],
               'It': ['It/I0'],
               'Ir': ['Ir/It'],
               'If': [f'({fluorescence_signal})/I0'],
               'trans': ['log(I0/It)', 'log(It/Ir)', 'I0', 'It/I0', 'Ir/It'],
               'fluorescence': [f'({fluorescence_signal})/I0', 'log(I0/It)',
                                 'log(It/Ir)', 'I0', 'It/I0', 'Ir/It'],
               'ref': ['log(It/Ir)', 'It/I0', 'Ir/It']}

            for y_axis in plot_lookup[subtype]:
                subtitle = y_axis.replace('/','div')
                model, figure = single_plot(f'{plan_name}: {subtitle}', x_axis, y_axis)
                model.add_run(run)
                self.plot_builders.append(model)
                self.figures.append(figure)

    def single_plot(self, title, x, y):
        axes1 = Axes()
        figures = [Figure((axes1,), title=title)]
        models = [Lines(x=x, ys=[y,], max_runs=1, axes=axes1)]
        return models, figures
