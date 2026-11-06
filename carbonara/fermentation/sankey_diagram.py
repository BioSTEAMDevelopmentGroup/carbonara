# -*- coding: utf-8 -*-
"""
"""
import biosteam as bst
from biosteam.plots import sankey
from biosteam.utils import CABBI_colors
import carbonara.fermentation as ferm

__all__ = (
    'create_sankey_plot',
)

class SankeyHandle(sankey.MassStreamHandle):
    __slots__ = ('node_color',)
    
    def _init(self, node_color):
        self.node_color = node_color
    
    def process_color(self, units, index):
        return "rgba(%d, %d, %d, 1.0)" %tuple(self.node_color.RGB)
    
    def stream_color(self, stream): 
        return "rgba(%d, %d, %d, 1.0)" %tuple(ferm.colors['stream'].RGB)


@bst.utils.piping.ignore_docking_warnings
def create_sankey_plot(scenario, width=1000, height=560, add_label=True, show=True):
    pm = ferm.EthanolProductionProcess(scenario=scenario)
    node_color = ferm.colors[scenario]
    mocksys = pm.create_mock_system()
    handle = SankeyHandle(node_color=node_color)
    nodes = handle.nodes(mocksys.units)
    links = sum([i.links() for i in nodes], [])
    data = sankey.sankey_data(nodes, links=links, orientation="h", add_label=add_label)
    fig = sankey.sankey_figure(data)
    fig.update_layout(width=width, height=height, **ferm.sankey_layout)
    if show: fig.show()
    return data, fig