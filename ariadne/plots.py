from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines
from bluesky_widgets.models.plot_specs import Axes, Figure

plan linescan motor type
plan xafs tran/fluor/ref

# Just a note, can delete this.
y_lookup = {'I0': 'I0',
            'It': 'It/I0',
            'Ir': 'Ir/It',
            'If': f'({fluorescence_signal})/I0',
            'trans': 'log(I0/It)',
            'fluorescence': f'({fluorescence_signal})/I0',
            'ref': 'log(It/Ir)'}

plot_lookup = {'I0': ['I0'],
               'It': ['It/I0'],
               'Ir': ['Ir/It'],
               'If': [f'({fluorescence_signal})/I0'],
               'trans' : ['log(I0/It)', 'log(It/Ir)', 'I0', 'It/I0', 'Ir/It']
               'fluorescence' : [f'({fluorescence_signal})/I0', 'log(I0/It)',
                                 'log(It/Ir)', 'I0', 'It/I0', 'Ir/It']
               'ref' : ['log(It/Ir)', 'It/I0', 'Ir/It']

class AutoBMMPlot(AutoPlotter):

    def handle_new_stream(self, run, stream_name):
        if stream_name == 'primary':

            plan_name = run.metadata['start'].get('plan_name').split(' ')
            plan = plan_name[1]a # xafs or linescan
            subtype = plan_name[-1] # trans, ref, fluorescence, I0, It, Ir

            if plan == 'linescan':
                x = plan_name[2]
            elif plan == 'xafs':
                x = 'dcm_energy'
            else:
                return

            if plan == 'xafs':
                element = run.metadata['start']['XDI']['Element']['Symbol']

            models = []
            figures = []

            for plot

            for model in models:
                model.add_run(run)
                self.plot_builders.append(model)
            self.figures.extend(figures)

    def single_plot(self, title, x, y):
        axes1 = Axes()
        figures = [Figure((axes1,), title=title)]
        models = [Lines(x=x, ys=[y,], max_runs=1, axes=axes1)]
        return models, figures

    def rel_scan_linescan_xafs_pitch_it(self, run, stream_name):
        x_values = 'xafs_pitch'
        models = []
        figures = []

        axes1 = Axes()
        figure1 = Figure((axes1,), title="rel_scan linescan xafs_pitch It: It_div_I0")
        figures.append(figure1)
        models.append(
            Lines(x=x_values, ys=['It/I0',], max_runs=1, axes=axes1)
        )

        axes2 = Axes()
        figure2 = Figure((axes2,), title="rel_scan linescan xafs_pitch It: I0")
        figures.append(figure2)
        models.append(
            Lines(x=x_values, ys=['I0',],    max_runs=1, axes=axes2)
        )

        return models, figures

    def rel_scan_linescane_xafs_y_if(self, run, stream_name):
        x_values = 'xafs_y'
        models = []
        figures = []

        axes = Axes()
        figure = Figure((axes,), title="rel_scan linescan xafs_y if: Fluor_div_I0")
        figures.append(figure)
        models.append(
            Lines(x=x_values, ys=['(Pt1+Pt2+Pt3+Pt4)/I0',],    max_runs=1, axes=axes)
        )

        return models, figures

    def scan_nd_xafs_trans(self, run, stream_name):
        x_values = run.metadata['start']['motors'][0]
        models = []
        figures = []

        axes1 = Axes()
        axes2 = Axes()
        figure = Figure((axes1, axes2), title='scan_nd xafs transmission')
        figures.append(figure)
        models.append(
            Lines(x=x_values, ys=['It/I0',], max_runs=1, axes=axes1)
        )
        models.append(
            Lines(x=x_values, ys=['I0',],    max_runs=1, axes=axes2)
        )

        return models, figures

    def scan_nd_xafs_fluorescence(self, run, stream_name):
        x_values = run.metadata['start']['motors'][0]
        models = []
        figures = []

        axes1 = Axes()
        axes2 = Axes()
        figure = Figure((axes1, axes2), title='scan_nd xafs fluorescense')
        figures.append(figure)
        models.append(
            Lines(x=x_values, ys=['It/I0',], max_runs=1, axes=axes1)
        )
        models.append(
            Lines(x=x_values, ys=['I0',],    max_runs=1, axes=axes2)
        )

        return models, figures
