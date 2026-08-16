# -*- coding: utf-8 -*-
"""
"""
from biorefineries.gas_fermentation import Biorefinery, TRYBiorefinery
import numpy as np
from matplotlib import pyplot as plt
import biosteam as bst
import os
import thermosteam as tmo
from colorpalette import Color

__all__ = (
)

line_color = Color(fg='#8E9BB3').RGBn
results_folder = os.path.join(os.path.dirname(__file__), 'results')
images_folder = os.path.join(os.path.dirname(__file__), 'images')

# def plot_bars(scenario_names, raw_materials):
#     import pandas as pd
#     import biosteam as bst
#     import seaborn as sns
#     import matplotlib.pyplot as plt
#     from warnings import filterwarnings
#     filterwarnings('ignore')
#     sns.set(style='ticks')
#     bst.set_figure_size(aspect_ratio=0.6, width='full')
#     bst.set_font(size=10)
#     fig, (CAPEX_ax, OPEX_ax) = plt.subplots(1, 2)
#     process_models = [
#         Biorefinery(scenario=name, simulate=True) 
#         for name in scenario_names
#     ]
#     for pm in process_models:
#         for group in pm.unit_groups: 
#             try:
#                 group.autofill_metrics(
#                     shorthand=False, 
#                     installed_cost=True,
#                     cooling_duty=False,
#                     heating_duty=False,
#                     electricity_consumption=False,
#                     electricity_production=False,
#                     material_cost=False
#                 )
#             except:
#                 pass
#     CAPEX = pd.concat([
#         bst.UnitGroup.df_from_groups(pm.unit_groups)
#         for pm in process_models
#     ], axis=1)
#     CAPEX.loc['Indirect costs'] = [(i.tea.TCI - i.tea.DPI) /1e6 for i in process_models]
#     CAPEX.loc['Other'] = [i.tea.TCI / 1e6 for i in process_models] - CAPEX.sum()
#     CAPEX = CAPEX.sort_index(key=lambda x:[-abs(sum(CAPEX.loc[i])) for i in x])
#     CAPEX.columns = scenario_names
#     plt.sca(CAPEX_ax)
#     CAPEX.T.plot.bar(stacked=True, rot=0, ax=CAPEX_ax, fontsize=10)
#     plt.ylabel(r'CAPEX [$10^6\cdot$USD]', fontsize=10)
#     ax = plt.gca()
#     ax.tick_params(axis='x', which='major', length=6,
#                    direction="inout")
#     ax.tick_params(axis='y', which='major', length=6,
#                    direction="inout")
#     ax.get_legend().remove()
#     ax.spines[['right', 'top']].set_visible(False)
#     # ax.legend(bbox_to_anchor=(1.05, 1.05))
#     # ax.legend(
#     #     loc='upper center', bbox_to_anchor=(0.5, 1.05),
#     #     ncol=3, fancybox=True
#     # )
#     VOC_table = bst.report.voc_table(
#         [i.system for i in process_models], 
#         system_names=scenario_names,
#         product_IDs=[]
#     )
#     VOC_table = VOC_table.drop('Price [$/MT]', axis=1)
#     materials = VOC_table.loc['Raw materials']
#     ash_disposal_cost = -VOC_table.loc['Co-products & credits', 'Ash disposal']
#     materials.loc['Glucose'] = materials.loc['Feedstock'] + materials.loc['Seedtrain feed']
#     materials = materials.drop('Seedtrain feed')
#     materials = materials.drop('Feedstock')
#     OPEX = materials.loc[raw_materials]
#     OPEX.loc['Other'] = ash_disposal_cost + materials.sum() - OPEX.sum() + [i.tea.FOC/1e6 for i in process_models]
#     products = VOC_table.loc['Co-products & credits'].drop('Ash disposal', axis=0)
#     OPEX_and_revenue = pd.concat([-OPEX, products])
#     OPEX_and_revenue = OPEX_and_revenue.sort_index(key=lambda x:[-abs(sum(OPEX_and_revenue.loc[i])) for i in x])
#     OPEX_and_revenue.columns = scenario_names
#     plt.sca(OPEX_ax)
#     OPEX_and_revenue.T.plot.bar(stacked=True, rot=0, ax=OPEX_ax, fontsize=10)
#     plt.axhline(y=0, color='darkgray', linestyle='--')
#     plt.ylabel(r'OPEX & Revenue [$10^6\cdot$USD$\cdot$yr$^{-1}$]', fontsize=10)
#     ax = plt.gca()
#     ax.tick_params(axis='x', which='major', length=6,
#                    direction="inout")
#     ax.tick_params(axis='y', which='major', length=6,
#                    direction="inout")
#     ax.get_legend().remove()
#     ax.spines[['right', 'top']].set_visible(False)
#     # ax.legend(bbox_to_anchor=(1.05, 1.05))
#     # ax.legend(
#     #     loc='upper center', bbox_to_anchor=(0.5, 1.05),
#     #     ncol=3, fancybox=True
#     # )
#     plt.subplots_adjust(wspace=0.5, hspace=0.9, right=0.95, bottom=0.2, top=0.95)
#     for i in ('svg', 'png'):
#         file = os.path.join(images_folder, f'bars.{i}')
#         plt.savefig(file, dpi=900, transparent=True)


# def MSP_at_capacity_price(price, capacity, biorefinery):
#     biorefinery.set_H2_price.setter(price)
#     biorefinery.set_capacity.setter(capacity)
#     if biorefinery.last_capacity != capacity:
#         biorefinery.system.simulate()
#         biorefinery.last_capacity = capacity
#     MSP = biorefinery.tea.solve_price(biorefinery.dodecylacetate)
#     return np.array([MSP])

# def plot_MSP_across_capacity_price(process_model, load=True):
#     bst.plots.set_font(size=12, family='sans-serif', font='Arial')
#     process_model.last_capacity = None
#     xlim = np.array(process_model.set_H2_price.bounds)
#     ylim = np.array(process_model.set_capacity.bounds)
#     X, Y, Z = bst.plots.generate_contour_data(
#         MSP_at_capacity_price,
#         file=os.path.join(results_folder, 'MSP_capacity_price.npy'),
#         load=load, save=True,
#         xlim=xlim, ylim=ylim,
#         args=(process_model,),
#         n=10,
#     )
    
#     # Plot contours
#     ylabel = "Production [$\mathrm{10}^{3} \cdot \mathrm{MT} \cdot \mathrm{yr}^{\mathrm{-1}}$]"
#     xlabel = '$\mathrm{H}_\mathrm{2}$ Price [$\mathrm{USD} \cdot \mathrm{kg}^{\mathrm{-1}}$]'
#     yticks = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
#     xticks = [1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
#     metric_bar = bst.plots.MetricBar(
#         'MSP', '$\mathrm{USD} \cdot \mathrm{kg}^{\mathrm{-1}}$', plt.cm.get_cmap('viridis_r'), 
#         bst.plots.rounded_tickmarks_from_data(Z, 5, 1, expand=0, p=0.5), 
#         10, 1
#     )
#     fig, axes, CSs, CB, other_axes = bst.plots.plot_contour_single_metric(
#         X, Y / 1000, Z[:, :, None], xlabel, ylabel, xticks, yticks, metric_bar,  
#         fillcolor=None, styleaxiskw=dict(xtick0=False), label=True,
#     )

# def metric_at_parameters(
#         value_A, value_B, system, metric,
#         param_A, param_B,
#     ):
#     param_A.setter(value_A)
#     param_B.setter(value_B)
#     system.simulate()
#     return metric()

# def metric_at_parameters_across_biorefineries(
#         value_A, value_B, biorefineries, metric,
#         param_A, param_B,
#     ):
#     values = np.zeros(len(biorefineries))
#     for i, br in enumerate(biorefineries):
#         values[i] = metric_at_parameters(
#             value_A, value_B, br.system,
#             getattr(br, metric),
#             getattr(br, param_A),
#             getattr(br, param_B),
#         )
#     return values

# def metric_at_parameters_across_biorefineries_and_other(
#         value_A, value_B, biorefineries, metric,
#         param_A, param_B, other_param, other_values, 
#     ):
#     values = np.zeros([len(biorefineries), len(other_values)])
#     for i, br in enumerate(biorefineries):
#         for j, value in enumerate(other_values):
#             getattr(br, other_param)(value)
#             values[i, j] = metric_at_parameters(
#                 value_A, value_B, br.system,
#                 getattr(br, metric),
#                 getattr(br, param_A),
#                 getattr(br, param_B),
#             )
#     return values

# def plot_MSP_across_yield_and_titer(load=True, scenario=None):
#     from warnings import filterwarnings
#     filterwarnings('ignore')
#     bst.plots.set_font(size=10, family='sans-serif', font='Arial')
#     bst.plots.set_figure_size(aspect_ratio=0.55, width='full')
#     br_acetate, br_acetate_glucose_seed, br_glucose = biorefineries = [
#         Biorefinery(simulate=False, scenario=i)
#         for i in ['acetate', 'acetate/glucose-seed', 'glucose']
#     ]
#     xlim = np.array(br_acetate.set_oleochemical_bioreactor_yield.bounds)
#     ylim = np.array(br_acetate.set_oleochemical_titer.bounds)
#     X, Y, Z = bst.plots.generate_contour_data(
#         metric_at_parameters_across_biorefineries_and_other,
#         file=os.path.join(results_folder, 'MSP_yield_titer.npy'),
#         load=load, save=True,
#         xlim=xlim, ylim=ylim,
#         args=(biorefineries,
#               'MSP', 
#               'set_oleochemical_bioreactor_yield', 
#               'set_oleochemical_titer',
#               'set_oleochemical_productivity',
#               [0.1, 1]),
#         n=10,
#     )
#     Z = Z.swapaxes(2, 3)
#     # Plot contours
#     yticks = [1, 2, 4, 6, 8, 10]
#     xticks = [35, 45, 55, 65, 75, 85]
#     metric_bar = bst.plots.MetricBar(
#         'Minimum selling price', r'$[\mathrm{USD} \cdot \mathrm{kg}^{\mathrm{-1}}]$', 
#         plt.cm.get_cmap('viridis_r'), 
#         bst.plots.rounded_tickmarks_from_data(Z, 5, 1, expand=0, p=1), 
#         25, 1, ylabelkwargs=dict(size=10), shrink=1.0,
#         units_dlim=' ',
#         title_position='horizontal',
#         forced_size=1.2,
#     )
#     fig, axes, CSs, CB, other_axes = bst.plots.plot_contour_single_metric(
#         X, Y, Z, None, None, xticks, yticks, metric_bar,  
#         fillcolor=None, 
#         styleaxiskw=dict(xtick0=False, ytick0=False), label=True,
#         contour_label_interval=3, label_fs=9,
#         highlight_levels=[5], highlight_color='r',
#     )
#     plt.subplots_adjust(left=0.12, right=0.85, wspace=0.15, hspace=0.15, top=0.9, bottom=0.13)
#     for i in ('svg', 'png'):
#         file = os.path.join(images_folder, f'oleochemical_yield_titer_contours.{i}')
#         plt.savefig(file, dpi=900, transparent=True)

# def plot_CI_across_yield_and_titer(load=True, scenario=None):
#     from warnings import filterwarnings
#     filterwarnings('ignore')
#     bst.plots.set_font(size=10, family='sans-serif', font='Arial')
#     bst.plots.set_figure_size(aspect_ratio=0.55, width='full')
#     br_acetate, br_acetate_glucose_seed, br_glucose = biorefineries = [
#         Biorefinery(simulate=False, scenario=i)
#         for i in ['acetate', 'acetate/glucose-seed', 'glucose']
#     ]
#     xlim = np.array(br_acetate.set_oleochemical_bioreactor_yield.bounds)
#     ylim = np.array(br_acetate.set_oleochemical_titer.bounds)
#     X, Y, Z = bst.plots.generate_contour_data(
#         metric_at_parameters_across_biorefineries_and_other,
#         file=os.path.join(results_folder, 'CI_H2_price_and_yield.npy'),
#         load=load, save=True,
#         xlim=xlim, ylim=ylim,
#         args=(biorefineries,
#               'carbon_intensity', 
#               'set_oleochemical_bioreactor_yield', 
#               'set_oleochemical_titer',
#               'set_oleochemical_productivity',
#               [0.1, 1]),
#         n=10,
#     )
#     Z = Z.swapaxes(2, 3)
#     # Plot contours
#     yticks = [1, 2, 4, 6, 8, 10]
#     xticks = [35, 45, 55, 65, 75, 85]
#     dodecanol_carbon_intensity = 2.97 # Emissions (cradle-to-gate) DOI 10.1007/s11743-016-1867-y
#     metric_bar = bst.plots.MetricBar(
#         'Carbon intensity', '$[\mathrm{kg} \cdot \mathrm{CO}_{\mathrm{2}}\mathrm{e} \cdot \mathrm{kg}^{\mathrm{-1}}]$',
#         plt.cm.get_cmap('viridis_r'), 
#         bst.plots.rounded_tickmarks_from_data(Z, 5, 1, expand=0, p=1), 
#         25, 1, ylabelkwargs=dict(size=10), shrink=1.0,
#         units_dlim=' ',
#         title_position='horizontal',
#         forced_size=1.2,
#     )
#     fig, axes, CSs, CB, other_axes = bst.plots.plot_contour_single_metric(
#         X, Y, Z, None, None, xticks, yticks, metric_bar,  
#         fillcolor=None, 
#         styleaxiskw=dict(xtick0=False, ytick0=False), label=True,
#         contour_label_interval=3, label_fs=9,
#         highlight_levels=[dodecanol_carbon_intensity], highlight_color='r',
#     )
#     plt.subplots_adjust(left=0.12, right=0.85, wspace=0.15, hspace=0.15, top=0.9, bottom=0.13)
#     for i in ('svg', 'png'):
#         file = os.path.join(images_folder, f'CI_oleochemical_yield_titer_contours.{i}')
#         plt.savefig(file, dpi=900, transparent=True)
