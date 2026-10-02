# -*- coding: utf-8 -*-
"""
"""
import biosteam as bst
from biosteam.wastewater.high_rate.utils import append_wwt_chemicals

__all__ = (
    'create_chemicals',
)

def create_chemicals(yeast_includes_nitrogen=False):
    chemicals = bst.Chemicals([
        'Water', 'Ethanol', 'Glucose', 'Sucrose',
        'H3PO4', 'P4O10', 'Octane', 'Ash',    
        'Cellulose', 'Hemicellulose', 'Flocculant', 'Lignin', 
        'Solids', 'Yeast', 'Bacteria', 'CaO',     
        'N2', 'CO', 'H2', 'O2', 'CO2', 'Urea',
    ], db='BioSTEAM')
    return append_wwt_chemicals(chemicals, set_thermo=False)

