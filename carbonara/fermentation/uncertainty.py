# -*- coding: utf-8 -*-
"""
"""
import carbonara.fermentation as gasferm
from warnings import filterwarnings
import biosteam as bst
import numpy as np
import pandas as pd
import os
from thermosteam.units_of_measure import format_units
from thermosteam.utils import roundsigfigs
from matplotlib import pyplot as plt
from biosteam.utils import GG_colors, CABBI_colors
from SALib.analyze import sobol
import seaborn as sns
import yaml
from scipy import interpolate
from chaospy import distributions as shape

__all__ = (
    'run_monte_carlo', 
    'run_all_monte_carlo',
    # 'plot_monte_carlo',
    'plot_kde',
    'plot_kde_comparison',
    'plot_spearman_scenarios',
    # 'sobol_analysis',
    'montecarlo_results',
    # 'opportunity_space',
    'get_distribution_table',
    'plot_all_dark',
    'plot_graphical_abstract_dark',
)

results_folder = os.path.join(os.path.dirname(__file__), 'results')
images_folder = os.path.join(os.path.dirname(__file__), 'images')
comparison_scenarios = ('sugarcane2/H2 - sugarcane2', 'sugarcane1/H2 - sugarcane1')

def sobol_file(name, extention='xlsx'):
    filename = name.replace('/', '_') + '_sobol'
    filename += '.' + extention
    return os.path.join(results_folder, filename)

def monte_carlo_file_name(name):
    filename = name.replace('/', '_') + '_monte_carlo'
    filename += '.' + 'xlsx'
    return os.path.join(results_folder, filename)

def spearman_file_name(name):
    filename = name.replace('/', '_') + '_spearman'
    filename += '.xlsx'
    return os.path.join(results_folder, filename)

def autoload_file_name(name, N):
    filename = name.replace('/', '_') + '_' + str(N)
    return os.path.join(results_folder, filename)

def plot_all_dark():
    gasferm.dark_mode()
    for i in ('environment', 'economic', 'circularity'):
        plot_kde(i)
        for j in (1, 2):
            plot_kde_comparison(i, f'sugarcane{j}/H2 - sugarcane{j}')

def plot_graphical_abstract_dark():
    gasferm.dark_mode()
    for i in ('environment', 'economic', 'circularity'):
        plot_kde(
            i, 
            scenarios=['BFG/H2', 'sugarcane1/H2', 'sugarcane2/H2'], 
            colors=[GG_colors.blue, GG_colors.red, GG_colors.yellow],
            ticklabels=False,
            short=True,
        )

# def plot_monte_carlo(scenarios=None):
#     bst.plots.set_font(size=10, family='sans-serif', font='Arial')
#     bst.plots.set_figure_size(aspect_ratio=1.05)
#     fig, axes = _plot_monte_carlo(scenarios)
#     plt.subplots_adjust(left=0.12, right=0.95, wspace=0.50, top=0.98, bottom=0.2)
#     for i in ('svg', 'png'):
#         file = os.path.join(images_folder, f'montecarlo_absolute.{i}')
#         plt.savefig(file, transparent=True)

# def _plot_monte_carlo(scenarios=None):
#     ProcessModel = gasferm.EthanolProductionProcess
#     scenarios = ('sugarcane', 'sugarcane/H2', 'BFG/H2', 'RFG/H2')
#     models = [
#         EthanolProductionProcess(scenario=name, simulate=False)
#         for name in scenarios
#     ]
#     indicators = [
#         ['MSP', 'carbon_intensity'], 
#         ['TCI', 'production_capacity'],
#         ['electricity_demand', 'biomass_burned'],
#         ['hydrogen_consumption', 'glucose_consumption'],
#     ]
#     # Subplots
#     nrows = len(indicators)
#     ncols = len(indicators[0])
#     fig, axes_box = plt.subplots(ncols=ncols, nrows=nrows)
#     plt.subplots_adjust(wspace=0.45)
#     axes = axes_box.transpose()
#     axes = axes.flatten()
#     pm = models[0]
#     df = get_monte_carlo(pm.scenario, pm.MSP.index)
#     N_scenarios = len(scenarios)
#     nsamples = df.shape[0]
#     M = nsamples * len(scenarios)
#     for i in range(nrows):
#         for j in range(ncols):
#             original_name = indicators[i][j]
#             indicator = getattr(pm, original_name)
#             indicator_name = indicator.label(element=False).replace(' [', '\n[')
#             indicator_index = indicator.index
#             indicator_name = indicator_name.replace('hydrogen', 'H$_2$')
#             indicator_name = indicator_name.replace('Hydrogen', 'H$_2$')
#             indicator_name = indicator_name.replace(r'-H2}', r'} \cdot \mathrm{H}_2')
#             indicator_name = indicator_name.replace('yield', '')
#             columns = ['substrate', indicator_name]
#             substrate_index = 0
#             values_index = 1
#             data = np.zeros([M, 2], dtype=object)
#             df = pd.DataFrame(
#                 data=data, columns=columns
#             )
#             mask = None
#             lower_index = 0
#             for pm in models:
#                 values = get_monte_carlo(pm.scenario, indicator_index)
#                 if pm.scenario.name == 'acetate/glucose-seed':
#                     # Remove top 0.5 % of all scenarios due to overly conservative 
#                     # assumptions that lead to an extremely high capital cost.
#                     # These scenarios are near the minimum technological performance,
#                     # which are overly conservative for an industrial process.
#                     if mask is None:
#                         glucose_consumption = get_monte_carlo(pm.scenario, pm.glucose_consumption.index)
#                         new_max = np.percentile(glucose_consumption, 99.5) 
#                         mask = glucose_consumption < new_max
#                     values = values[mask]
#                 upper_index = lower_index + values.size
#                 rowslice = slice(lower_index, upper_index)
#                 data[rowslice, values_index] = values
#                 data[rowslice, substrate_index] = pm.scenario.name.replace('/', ' &\n')
#                 lower_index = upper_index
#             df = df.iloc[:upper_index]
#             axis = axes_box[i, j]
#             plt.sca(axis)
#             kwargs = {}
#             if box:
#                 f = sns.boxplot
#             else:
#                 # kwargs['split'] = False
#                 # kwargs['inner'] = 'quart'
#                 f = sns.violinplot
#             f(legend=False, ax=axis,
#               data=df, y=indicator_name,
#               x='substrate', 
#               # gap=.1, 
#               palette={
#                   'glucose': GG_colors.yellow.RGBn,
#                   'acetate': GG_colors.blue.RGBn,
#                   'acetate &\nglucose-seed': GG_colors.red.RGBn,
#               },
#               **kwargs)
#             if i == 0:
#                 if j == 0:
#                     bst.plots.plot_horizontal_line(dodecanol_market_price, lw=1, ls='--', color=line_color * 1.1)
#                 elif j == 1:
#                     bst.plots.plot_horizontal_line(dodecanol_carbon_intensity, lw=1, ls='--', color=line_color * 1.1)
#             values = data[:, values_index]
#             assert not np.isnan(np.array(values, dtype=float)).any()
#             tickmarks = bst.plots.rounded_tickmarks_from_data(
#                 values, N_ticks=5, lb_max=values.min() * 2 if (values < 0).any() else 0,
#                 f=lambda x: roundsigfigs(x, sigfigs=2, index=1),
#                 f_min=lambda x: np.min(x),
#                 f_max=lambda x: np.max(x),
#                 expand=0.2,
#             ) 
#             yticks = roundsigfigs(tickmarks, sigfigs=3, index=1)
#             plt.ylim([yticks[0], yticks[1]])
#             # if yticks[0] < 0.:
#             #     bst.plots.plot_horizontal_line(0, color=CABBI_colors.black.RGBn, lw=0.8, linestyle='--')
#             xticks, xticklabels = plt.xticks()
#             if i != nrows - 1: 
#                 xticklabels =  N_scenarios * ['']
#                 xticks = [*range(N_scenarios)]
#             if N_scenarios == 1:
#                 xticklabels = []
#                 xticks = []
#             plt.xlabel('')
#             bst.plots.style_axis(axis,  
#                 xticks = xticks,
#                 yticks = yticks,
#                 xticklabels= xticklabels, 
#                 ytick0=True,
#                 ytickf=False,
#                 xrot=0,
#                 offset_xticks=False,
#             )
#     if fig is None:
#         fig = plt.gcf()
#     else:
#         plt.subplots_adjust(hspace=0, wspace=0.3)
#     fig.align_ylabels(axes)
#     return fig, axes

def spearman_name(f):
    d = f.distribution
    units = f.units
    if f.element and f.element_name.lower() not in f.name.lower():
        name = ' '.join([f.element_name.capitalize(), f.name.lower()])
        name = name.replace('Cofermenation', 'Cofermentation').replace('Cofermentation', 'Coferm')
    else:
        name = f.name
    dname = type(d).__name__
    if units is None: units = f.units
    if dname == 'Triangle':
        distribution = ', '.join([format(j, '.2g')
                                  for j in d._repr.values()])
    elif dname == 'Uniform':
        distribution = ' $-$ '.join([format(j, '.2g')
                                     for j in d._repr.values()])
    if units is None:
        return f"{name}\n[{distribution}]"
    else:
        return f"{name}\n[{distribution} {format_units(units)}]"


def get_distribution_table():
    pm = gasferm.EthanolProductionProcess(simulate=False)
    parameters = pm.model.parameters
    def with_units(f, name, units=None):
        if units is None: units = f.units
        if units is None: units = '-'
        return name, units
        
    def get_distribution_dict(f):
        d = f.distribution
        dname = type(d).__name__
        values = [roundsigfigs(j, 3) for j in d._repr.values()]
        if dname == 'Triangle':
            return {
                'Shape': 'Triangular',
                'Lower': values[0],
                'Upper': values[2],
                'Mode': values[1],
            }
            
        elif dname == 'Uniform':
            return {
                'Shape': 'Uniform',
                'Lower': values[0],
                'Upper': values[1],
                'Mode': '-',
            }
    
    rows = []
    for f in parameters:
        if f.element and f.element_name.lower() not in f.name.lower():
            name = ' '.join([f.element_name.capitalize(), f.name.lower()])
            name = name.replace('Cofermenation', 'Cofermentation').replace('Cofermentation', 'Coferm')
        else:
            name = f.name
        rows.append({
            'Parameter': name,
            'Units': f.units or '-',
            'Baseline': roundsigfigs(f.baseline, 3),
            **get_distribution_dict(f),
        })
    table = pd.DataFrame(
        rows, 
        index=list(
            range(1, len(parameters) + 1)
        )
    )
    table.drop(columns=['Mode'], inplace=True)
    file = os.path.join(results_folder, 'distributions.xlsx')
    table.to_excel(file)
    table.index.name = '#'
    return table

def plot_spearman_scenarios(
        kind='TEA',
        full=None,
        scenarios=None,
        **kwargs
    ):
    if scenarios is None: scenarios = gasferm.all_scenarios
    bst.plots.set_font(size=8)
    if full:
        if kind == 'TEA':
            bst.plots.set_figure_size(aspect_ratio=1.5, width='half')
        else:
            bst.plots.set_figure_size(aspect_ratio=3, width='half')
    else:
        if kind == 'TEA':
            bst.plots.set_figure_size(aspect_ratio=1.1, width='half')
        else:
            bst.plots.set_figure_size(aspect_ratio=0.9, width='half')
    rhos = []
    first = scenarios[0]
    pm = gasferm.EthanolProductionProcess(simulate=False, scenario=first)
    file = spearman_file_name(pm.scenario.name)
    df = pd.read_excel(file, header=[0, 1], index_col=[0, 1])
    names = [spearman_name(i) for i in pm.model.parameters]
    index = [i for i in range(len(df.index))]
    for scenario in scenarios:
        pm = gasferm.EthanolProductionProcess(simulate=False, scenario=scenario)
        file = spearman_file_name(pm.scenario.name)
        df = pd.read_excel(file, header=[0, 1], index_col=[0, 1])
        if kind == 'TEA':
            indicator = pm.carbon_mitigation_cost
            indicator_name = indicator.name
            values = df[indicator.index]
            full = True
        elif kind == 'LCA':
            indicator = pm.carbon_intensity
            indicator_name = r'carbon intensity'
            values = df[indicator.index]
            for i, p in enumerate(pm.model.parameters):
                name = p.name.lower()
                if 'price' in name or 'consumption' in name or 'capacity' in name: 
                    values.iloc[i] = 0
            full = False
        else:
            raise ValueError(f"invalid kind '{kind}'")
        values = values.iloc[index]
        rhos.append(values)
    label = indicator.label()
    label = label.replace('Carbon intensity', 'CI')
    if full: 
        top = 8
    else:
        top = 6
    fig, ax = bst.plots.plot_spearman_2d(rhos, index=names,
                                         color_wheel=[gasferm.colors[i] for i in scenarios],
                                         name=indicator_name,
                                         xlabel=r"Spearman's rank correlation" "\nwith " + label,
                                         top=top,
                                         w=1.0,
                                         **kwargs)
    if kind == 'LCA':
        bottom = 0.2
    else:
        bottom = 0.16
    plt.subplots_adjust(
        hspace=0.05, wspace=0.05,
        top=0.98, bottom=bottom,
        left=0.5, right=0.86,
    )
    for i in ('svg', 'png'):
        file = os.path.join(images_folder, f'spearman_all_scenarios_{kind}.{i}')
        plt.savefig(file, dpi=900, transparent=True)
    return fig, ax

def run_all_monte_carlo(scenarios=None):
    if scenarios is None: scenarios = ['BFG/H2', 'BFG/H2e', 'sugarcane/H2', 'sugarcane']
    for scenario in scenarios:
        run_monte_carlo(scenario=scenario)

def run_monte_carlo(
        scenario,
        N=1000, rule='L',
        sample_cache={},
        autosave=True,
        autoload=True,
        sort=True,
        convergence_model=None,
        dewatering=False,
        carbon_capture=False
    ):
    filterwarnings('ignore')
    pm = gasferm.EthanolProductionProcess(
        simulate=False, 
        scenario=scenario,
    )
    pm.model.exception_hook = 'raise'
    
    N_notify = min(int(N/10), 20)
    autosave = N_notify if autosave else False
    name = pm.scenario.name
    autoload_file = autoload_file_name(name, N)
    spearman_file = spearman_file_name(name)
    monte_carlo_file = monte_carlo_file_name(name)
    np.random.seed(1)
    samples = pm.model.sample(N, rule)
    pm.model.load_samples(samples, sort=sort)
    pm.model.evaluate(
        notify=N_notify,
        autosave=autosave,
        autoload=autoload,
        file=autoload_file,
        convergence_model=convergence_model,
    )
    pm.model.table.to_excel(monte_carlo_file)
    pm.model.table = pm.model.table.dropna(how='all', axis=1)
    for i in pm.model.indicators:
        if i.index not in pm.model.table: pm.model._indicators.remove(i)
    pm.model.table = pm.model.table.dropna(how='any', axis=0)
    rho, p = pm.model.spearman_r(filter='omit nan')
    rho.to_excel(spearman_file)

# def sobol_analysis():
#     filterwarnings('ignore', category=bst.exceptions.DesignWarning)
#     filterwarnings('ignore', category=bst.exceptions.CostWarning)
#     pm = gasferm.EthanolProductionProcess(simulate=False)
#     pm.model.exception_hook = 'raise'
#     for kind, params, indicator in [('tea', pm.tea_parameters, pm.MSP), ('lca', pm.lca_parameters, pm.GWP)]:
#         file = sobol_file('_'.join([pm.name, kind]))
#         pm.model.parameters = params
#         convergence_model = bst.ConvergenceModel(predictors=params)
#         samples = pm.model.sample(N=2**(len(pm.tea_parameters) - 4), rule='sobol', seed=0)
#         pm.model.load_samples(samples)
#         pm.model.evaluate(
#             notify=int(len(samples)/10),
#             convergence_model=convergence_model
#         )
#         problem = pm.model.problem()
#         Y = pm.model.table[indicator.index].values
#         results = sobol.analyze(problem, Y)
#         for i, j in results.items(): results[i] = j.tolist()
#         with open(file, 'w') as file:
#             yaml.dump(results, file)

# def plot_sobol(names, categories, df, colors=None, hatches=None,
#                bold_label=True, format_total=None, legend=False,
#                legend_kwargs=None, **kwargs):
#     colors, hatches = bst.plots.default_colors_and_hatches(len(names), colors, hatches)
#     N_categories = len(categories)
#     if format_total is None: format_total = lambda x: format(x, '.3g')
#     if bold_label:
#         bar_labels = [r"$\mathbf{" f"{format_total(i.total)}" "}$" "\n"
#                       r"$\mathbf{[" f"{format_units(i.units, '', False)}" "]}$"
#                       for i in categories]
#     else:
#         bar_labels = [f"{format_total(i.total)}\n[{format_units(i.units)}]"
#                       for i in categories]
#     df.T.plot(kind='bar', stacked=True, edgecolor='k', **kwargs)
#     locs, labels = plt.xticks()
#     plt.xticks(locs, ['\n['.join(i.get_text().split(' [')) for i in labels])
#     if legend: plt.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left')
#     plt.xticks(rotation=0)
#     fig = plt.gcf()
#     ax = plt.gca()
#     ax.set_ylabel('Cost and Utility Breakdown [%]')
#     values = df.values
#     negative_values = np.where(values < 0., values, 0.).sum(axis=0)
#     lb = min(0., 20 * np.floor(negative_values.min() / 20))
#     plt.ylim(lb, 100)
#     bst.plots.style_axis(top=False, yticks=np.arange(lb, 101, 20))
#     xticks, _ = plt.xticks()
#     xlim = plt.xlim()
#     y_twin = ax.twiny()
#     plt.sca(y_twin)
#     y_twin.tick_params(axis='x', top=True, direction="in", length=0)
#     y_twin.zorder = 2
#     plt.xlim(xlim)
#     if len(xticks) != len(bar_labels): xticks = xticks[1:]
#     plt.xticks(xticks, bar_labels, va='baseline')
#     N_marks = N_categories
#     axes = np.array([ax])
#     if legend_kwargs is None: legend_kwargs = {}
#     bst.plots.modify_stacked_bars(axes, N_marks, names, colors, hatches, 
#                                   legend, **legend_kwargs)
#     return fig, axes
    
def get_monte_carlo(scenario, features, cache={}, dropna=True):
    if isinstance(scenario, gasferm.EthanolProductionProcess.Scenario):
        if scenario in cache:
            df = cache[scenario]
        else:
            file = monte_carlo_file_name(scenario.name)
            cache[scenario] = df = pd.read_excel(file, header=[0, 1], index_col=[0])
        df = df[features]    
    elif isinstance(scenario, str):
        if scenario in cache:
            df = cache[scenario]
        elif '-' in scenario:
            left, right = scenario.split('-')
            left = left.strip(' ')
            right = right.strip(' ')
            left = gasferm.EthanolProductionProcess.as_scenario(left)
            right = gasferm.EthanolProductionProcess.as_scenario(right)
            left = get_monte_carlo(left, features, dropna=False)
            right = get_monte_carlo(right, features, dropna=False)
            return left - right
        else:
            file = monte_carlo_file_name(scenario)
            cache[scenario] = df = pd.read_excel(file, header=[0, 1], index_col=[0])
        df = df[features]    
    elif isinstance(scenario, bst.ScenarioComparison):
        left = get_monte_carlo(scenario.left, features, dropna=False)
        right = get_monte_carlo(scenario.right, features, dropna=False)
        df = left - right
    else:
        raise ValueError('invalid scenario')
    if dropna: df = df.dropna(how='all', axis=0)
    return df

def plot_kde(indicator_set=None, scenarios=None, short=False, ticklabels=True, colors=None):
    if scenarios is None: scenarios = gasferm.all_scenarios
    if indicator_set is None: indicator_set = 'economic'
    if colors is None: colors = [gasferm.colors[i] for i in scenarios]
    from warnings import filterwarnings
    filterwarnings('ignore')
    bst.plots.set_font(size=12)
    if short:
        aspect_ratio = 1.0
    else:
        aspect_ratio = 1.25
    bst.plots.set_figure_size(width='half', aspect_ratio=aspect_ratio)
    Xi, Yi, xlabel, ylabel, xticks, yticks = indicator_index_and_labels(indicator_set)
    indicators = [Xi, Yi]
    ys = []
    xs = []
    # shift = {
    #     'count': 0,
    #     'sep': 0.003,
    #     'start': 0.002,
    # }
    for scenario in scenarios:
        scenario = gasferm.EthanolProductionProcess.as_scenario(scenario)
        df = get_monte_carlo(scenario, indicators)
        y = df[Yi].values
        x = df[Xi].values
        ys.append(y)
        xs.append(x)
        # if scenario.feedstock == 'sugarcane' or Xi != get_index('carbon_intensity'): 
        #     xs.append(x)
        # else:
        #     count, sep, start = shift.values()
        #     shift['count'] = count + 1
        #     x = x + (start + count * sep)
        #     xs.append(x)
    fig, axes = bst.plots.plot_kde_1d(
        ys=[ys], xs=[xs], xticks=xticks, yticks=yticks,
        xticklabels=ticklabels, yticklabels=ticklabels,
        color_wheel=colors,
        autobox=False,
        # xbox_kwargs=dict(light=CABBI_colors.orange.RGBn, dark=CABBI_colors.orange.shade(60).RGBn),
        # ybox_kwargs=dict(light=CABBI_colors.blue.RGBn, dark=CABBI_colors.blue.shade(60).RGBn),
        xlabel=xlabel,
        ylabel=ylabel,
        s=0.5,
        aspect_ratio=1 if short else 1.1,
        xtick0=xticks[1] - xticks[0] > (xticks[2] - xticks[1]) * 0.95,
        ytick0=yticks[1] - yticks[0] > (yticks[2] - yticks[1]) * 0.95,
        xtickf=xticks[-1] - xticks[-2] > (xticks[-2] - xticks[-3]) * 0.95,
        ytickf=yticks[-1] - yticks[-2] > (yticks[-2] - yticks[-3]) * 0.95,
        kde=True,
    )
    if short:
        plt.subplots_adjust(
            hspace=0, wspace=0,
            top=0.95, bottom=0.14,
            left=0.18, right=0.96,
        )
    else:
        plt.subplots_adjust(
            hspace=0, wspace=0,
            top=0.95, bottom=0.12,
            left=0.22, right=0.96,
        )
    for i in ('svg', 'png'):
        file = os.path.join(images_folder, f"{indicator_set}_kde.{i}")
        plt.savefig(file, dpi=900, transparent=True)

# def opportunity_space(scenarios=None):
#     from warnings import filterwarnings
#     filterwarnings('ignore')
#     bst.plots.set_font(size=9)
#     bst.plots.set_figure_size(width='half', aspect_ratio=1)
#     if scenarios is None:
#         scenarios = ['acetate', 'acetate/glucose-seed', 'glucose']
#     pm = gasferm.EthanolProductionProcess(simulate=False, scenario=scenarios[0])
#     market_price = 5 # USD / kg
#     carbon_intensity = dodecanol_carbon_intensity
#     indicators = [pm.carbon_intensity.index, pm.MSP.index]
#     Xi, Yi = indicators
#     ys = []
#     xs = []
#     opportunity_space_market = {}
#     opportunity_space_environment = {}
#     for scenario in scenarios:
#         df = get_monte_carlo(
#             gasferm.EthanolProductionProcess.as_scenario(scenario),
#             indicators
#         )
#         y = df[Yi].values
#         x = df[Xi].values
#         ys.append(y)
#         xs.append(x)
#         opportunity_space_market[scenario] = (
#             (y <= market_price).sum() / y.size
#         )
#         opportunity_space_environment[scenario] = (
#             (x <= carbon_intensity).sum() / x.size
#         )
#     return {
#         'market': opportunity_space_market, 
#         'environment': opportunity_space_environment, 
#     }

def get_index(name):
    pm = gasferm.EthanolProductionProcess(scenario='sugarcane1', simulate=False)
    return getattr(pm, name).index

def indicator_index_and_labels(indicator_set, comparison=None):
    pm = gasferm.EthanolProductionProcess(scenario='sugarcane1', simulate=False)
    good = 'good'
    bad = 'bad'
    bgcolor = {
        good: (*GG_colors.blue.RGBn, 0.12),
        bad: (*GG_colors.red.RGBn, 0.12)
    }
    txcolor = {
        good: GG_colors.blue.shade(50).RGBn,
        bad: GG_colors.red.shade(50).RGBn,
    }
    text = {
        good: '()',
        bad: '()',
        None: '()'
    }
    if indicator_set == 'circularity':
        xindex = pm.carbon_circularity_index.index
        yindex = pm.energy_circularity_index.index
        xlabel = r'Carbon circularity rate [%]'
        ylabel = r'Energy circularity rate [%]'
        if comparison is None:
            xticks = [30, 40, 50, 60, 65]
            yticks = [45, 50, 55, 60, 65]
            # xticks = [25, 30, 40, 50, 60, 65]
            # yticks = [45, 50, 55, 60, 65, 70, 75]
        else:
            if comparison == 'sugarcane2/H2 - sugarcane2':
                xticks = [12, 15, 18, 21, 24]
                yticks = [-12, -8, -4, 0, 4, 6]
            elif comparison == 'sugarcane1/H2 - sugarcane1':
                xticks = [11.5, 12, 12.5, 13, 13.5]
                yticks = [-3.4, -3.25, -3.1, -2.95, -2.8]
            else:
                xticks = None
                yticks = None
            quadrants = [
                None, good,
                bad, None
            ]
    elif indicator_set == 'economic':
        xindex = pm.TCI.index
        yindex = pm.carbon_mitigation_cost.index
        xlabel = r'TCI $[$million USD$]$'
        ylabel = r'Carbon mitigation cost $[\mathrm{USD} \cdot \mathrm{MT}^{\mathrm{-1}}]$'
        if comparison is None:
            xticks = [0, 250, 500, 750, 1000, 1100]
            yticks = [0, 150, 300, 450, 600, 680]
        else:
            if comparison == 'sugarcane2/H2 - sugarcane2':
                xticks = [60, 120, 180, 240, 300, 360]
                yticks = [0, 50, 100, 150, 200, 250]
            elif comparison == 'sugarcane1/H2 - sugarcane1':
                xticks = [60, 90, 120, 150, 180]
                yticks = [0, 50, 100, 150, 200, 250]
            else:
                xticks = None
                yticks = None
            quadrants = [
                None, bad,
                good, None
            ]
    elif indicator_set == 'environment':
        xindex = pm.carbon_intensity.index
        xlabel = r'Carbon intensity $[\mathrm{kgCO2e} \cdot \mathrm{L}^{\mathrm{-1}}]$'
        yindex = pm.water_usage.index
        ylabel = r'Water usage $[\mathrm{L}_\mathrm{H2O} \cdot \mathrm{L}^{\mathrm{-1}}_{\mathrm{EtOH}}]$'
        if comparison is None:
            xticks = [0.15, 0.16, 0.17, 0.18, 0.19, 0.20]
            yticks = [700, 790, 880, 970, 1060]
            # xticks = [0.15, 0.16, 0.20, 0.24, 0.28]
            # yticks = [700, 850, 1000, 1150, 1300, 1400]
        else:
            if comparison == 'sugarcane2/H2 - sugarcane2':
                xticks = [-0.12, -0.10, -0.08, -0.06, -0.04]
                yticks = [-500, -425, -350, -275, -200]
            elif comparison == 'sugarcane1/H2 - sugarcane1':
                xticks = [-0.051, -0.05, -0.049, -0.048, -0.047]
                yticks = [-270, -260, -250, -240, -230, -220]
            else:
                xticks = None
                yticks = None
            quadrants = [
                None, bad,
                good, None
            ]
    elif indicator_set == 'combined':
        xindex = pm.carbon_energy_circularity_index.index
        yindex = pm.carbon_mitigation_cost.index
        xlabel = r'Carbon-energy circularity $[$%$]$'
        ylabel = r'Carbon mitigation cost $[\mathrm{USD} \cdot \mathrm{MT}^{\mathrm{-1}}]$'
        if comparison is None:
            xticks = [40, 45, 50, 55, 60, 65]
            yticks = [0, 150, 300, 450, 600, 680]
        else:
            xticks = None
            yticks = None
            quadrants = [
                None, bad,
                good, None
            ]
    else:
        raise ValueError(f'invalid indicator_set {indicator_set!r}')
    if comparison is None:
        return xindex, yindex, xlabel, ylabel, xticks, yticks
    else:
        quadrant_colors = [bgcolor.get(i) for i in quadrants]
        text_colors = [txcolor.get(i) for i in quadrants]
        labels = [text.get(i) for i in quadrants]
        return xindex, yindex, xlabel, ylabel, xticks, yticks, quadrant_colors, text_colors, labels

def plot_kde_comparison(
        indicator_set=None, comparison=None, xticks=None, yticks=None,
        xbox_kwargs=None, ybox_kwargs=None, fs=None, ticklabels=True, aspect_ratio=1.1,
        figure=True, 
    ):
    if comparison is None: comparison = 'sugarcane/H2 - sugarcane'
    if indicator_set is None: indicator_set = 'economic'
    if figure:
        bst.plots.set_font(size=fs or 12)
        bst.plots.set_figure_size(width='half', aspect_ratio=aspect_ratio)
    Xi, Yi, xlabel, ylabel, xticks, yticks, qc, tc, txt = indicator_index_and_labels(indicator_set, comparison)
    df = get_monte_carlo(comparison, [Xi, Yi])
    y = df[Yi].values
    x = df[Xi].values
    if xticks is None:
        xtick0 = xtickf = None
    else:
        xtick0 = xticks[1] - xticks[0] > (xticks[2] - xticks[1]) * 0.95
        xtickf = xticks[-1] - xticks[-2] > (xticks[-2] - xticks[-3]) * 0.95,
    if yticks is None:
        ytick0 = ytickf = None
    else:
        ytick0 = yticks[1] - yticks[0] > (yticks[2] - yticks[1]) * 0.95
        ytickf = yticks[-1] - yticks[-2] > (yticks[-2] - yticks[-3]) * 0.95,
    fig, ax, axes = bst.plots.plot_kde(
        y=y, x=x, xticks=xticks, yticks=yticks,
        xticklabels=ticklabels, yticklabels=ticklabels,
        xbox=False, ybox=False,
        # xbox_kwargs=xbox_kwargs or dict(light=CABBI_colors.orange.RGBn, dark=CABBI_colors.orange.shade(60).RGBn),
        # ybox_kwargs=ybox_kwargs or dict(light=CABBI_colors.blue.RGBn, dark=CABBI_colors.blue.shade(60).RGBn),
        aspect_ratio=1.2,
        xtick0=xtick0,
        ytick0=ytick0,
        xtickf=xtickf,
        ytickf=ytickf,
    )
    plt.sca(ax)
    plt.ylabel(r'$\Delta$' + ylabel)
    plt.xlabel(r'$\Delta$' + xlabel)    
    # bst.plots.plot_quadrants(
    #     data=[x, y], 
    #     text=txt, 
    #     quadrant_color=qc,
    #     text_color=tc,
    #     hline=False,
    #     vline=False,
    # )
    if figure:
        plt.subplots_adjust(
            hspace=0.05, wspace=0.05,
            top=0.98, bottom=0.15,
            left=0.23, right=0.94,
        )
        comparison = comparison.replace('/', '_')
        for i in ('svg', 'png'):
            file = os.path.join(images_folder, f"{comparison}_{indicator_set}_kde.{i}")
            plt.savefig(file, transparent=True, dpi=900)
    return fig, ax
    
def get_monte_carlo_key(index, dct, with_units=False):
    key = index[1] if with_units else index[1].split(' [')[0]
    if key in dct: key = f'{key}, {index[0]}'
    return key
    
def montecarlo_results(scenario, indicators=None):
    f = gasferm.EthanolProductionProcess(scenario=scenario, simulate=False)
    if isinstance(indicators, str): 
        indicators = [getattr(f, indicators)] 
    elif indicators is None:
        indicators = [
            f.carbon_intensity, f.MSP,
        ]
    else:
        indicators = [
            (getattr(f, i) if isinstance(i, str) else i) 
            for i in indicators
        ]
    indicators = [i.index for i in indicators]
    results = {}
    df = get_monte_carlo(f.scenario, indicators)
    results[f.name] = dct = {}
    for index in indicators:
        data = df[index].values
        q05, q50, q95 = roundsigfigs(np.percentile(data, [5, 50, 95], axis=0), 3)
        key = get_monte_carlo_key(index, dct, False)
        dct[key] = f"{q50} [{q05}, {q95}]"
    return results

# def plot_kde_carbon_capture_comparison():
#     left = (
#         gasferm.Scenario(carbon_capture=True, dewatering=True)
#         - gasferm.Scenario(carbon_capture=False, dewatering=True)
#     )
#     right = (
#         gasferm.Scenario(carbon_capture=True, dewatering=False)
#         - gasferm.Scenario(carbon_capture=False, dewatering=False)
#     )
#     plot_kde_2d_comparison(
#         (left, right),
#         # yticks=[[-60, -40, -20, 0, 20, 40, 60]],
#         # xticks=[[-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9],
#         #         [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9]],
#         top_right='No CC\nFavored()',
#         bottom_left='CC\nFavored()',
#         top_left='MSP\nTradeoff()',
#         bottom_right='GWP\nTradeoff()',
#         rotate_quadrants=2,
#         titles=['(a) With dewatering', '(b) No dewatering'],
#         fs=10,
#     )
#     plt.subplots_adjust(
#         wspace=0,
        
#     )
#     for i in ('svg', 'png'):
#         file = os.path.join(images_folder, f'carbon_capture_comparison_kde.{i}')
#         plt.savefig(file, dpi=900, transparent=True)
   
# def plot_kde_dewatering_comparison():
#     left = (
#         gasferm.Scenario(carbon_capture=True, dewatering=True)
#         - gasferm.Scenario(carbon_capture=True, dewatering=True)
#     )
#     right = (
#         gasferm.Scenario(carbon_capture=False, dewatering=True)
#         - gasferm.Scenario(carbon_capture=False, dewatering=False)
#     )
#     plot_kde_2d_comparison(
#         (left, right),
#         # yticks=[[-60, -40, -20, 0, 20, 40, 60]],
#         # xticks=[[-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9],
#         #         [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9]],
#         top_right='No CC\nFavored()',
#         bottom_left='CC\nFavored()',
#         top_left='MSP\nTradeoff()',
#         bottom_right='GWP\nTradeoff()',
#         rotate_quadrants=2,
#         titles=['(a) With CC', '(b) No CC'],
#         fs=10,
#     )
#     plt.subplots_adjust(
#         wspace=0,
#     )
#     for i in ('svg', 'png'):
#         file = os.path.join(images_folder, f'dewatering_comparison_kde.{i}')
#         plt.savefig(file, dpi=900, transparent=True)
    
# def plot_kde_comparison(
#         scenario, indicators, xticks=None, yticks=None,
#         xbox_kwargs=None, ybox_kwargs=None, top_left='',
#         top_right='Tradeoff', bottom_left='Tradeoff',
#         bottom_right='', fs=None, ticklabels=True, aspect_ratio=1.1,
#         xlabel=None, ylabel=None
#     ):
#     set_font(size=fs or 8)
#     set_figure_size(width='half', aspect_ratio=aspect_ratio)
#     Xi, Yi = [i.index for i in indicators]
#     df = get_monte_carlo(scenario, indicators)
#     y = df[Yi].values
#     x = df[Xi].values
#     ax = bst.plots.plot_kde(
#         y=y, x=x, xticks=xticks, yticks=yticks,
#         xticklabels=ticklabels, yticklabels=ticklabels,
#         xbox_kwargs=xbox_kwargs or dict(light=CABBI_colors.orange.RGBn, dark=CABBI_colors.orange.shade(60).RGBn),
#         ybox_kwargs=ybox_kwargs or dict(light=CABBI_colors.blue.RGBn, dark=CABBI_colors.blue.shade(60).RGBn),
#         aspect_ratio=1.2,
#     )
#     plt.sca(ax)
#     plt.xlabel(xlabel.replace('\n', ' '))
#     plt.ylabel(ylabel.replace('\n', ' '))
#     bst.plots.plot_quadrants(data=[x, y], text=[top_left, top_right, bottom_left, bottom_right])
#     plt.subplots_adjust(
#         hspace=0.05, wspace=0.05,
#         top=0.98, bottom=0.15,
#         left=0.2, right=0.98,
#     )
        