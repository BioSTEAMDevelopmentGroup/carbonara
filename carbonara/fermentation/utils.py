# -*- coding: utf-8 -*-
"""
"""
from colorpalette import Color, Palette
from biosteam.utils import GG_colors, CABBI_colors, colors as other_colors
import matplotlib.pyplot as plt

__all__ = (
    'all_scenarios',
    'colors',
    'sankey_layout',
    'dark_mode',
)

all_scenarios = ('BFG/H2',
                 'sugarcane1', 'sugarcane1/H2', 
                 'sugarcane2', 'sugarcane2/H2')
colors = Palette(**{
    'BFG/H2': GG_colors.blue, 
    'sugarcane1': GG_colors.red, 
    'sugarcane1/H2': GG_colors.purple, 
    'sugarcane2': GG_colors.yellow, 
    'sugarcane2/H2': GG_colors.green, 
    'letter': other_colors.neutral.shade(25),
    'line': Color(fg='#8E9BB3'),
    'stream': CABBI_colors.grey.shade(20),    
})
sankey_layout = {
    'font_size': 12, 
}

def dark_mode():
    plt.style.use('dark_background')
    plt.rcParams.update({
        "figure.facecolor":  (0.0, 0.0, 0.0, 0), 
        "axes.facecolor":    (0.0, 0.0, 0.0, 1), 
        "savefig.facecolor": (0.0, 0.0, 0.0, 0), 
    })
    for i in ('line', 'letter', 'stream'):
        colors[i] = colors[i].invert()
    # colors['stream'] = other_colors.neutral
    sankey_layout['template'] = 'plotly_dark'
    sankey_layout['paper_bgcolor'] = '#000000'