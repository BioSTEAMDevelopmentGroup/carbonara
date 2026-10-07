# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 23:34:44 2026

@author: yoelcp
"""

import numpy as np
fluegas_to_hotmetal = 2.5 # https://www.epa.gov/sites/production/files/2020-11/documents/c12s05.pdf
hot_metal = np.array([50000, 3e6]) * 0.05 # https://en.wikipedia.org/wiki/Steel_mill
fluegas_availability = fluegas_to_hotmetal * hot_metal # MT / yr
import biosteam as bst
gases = ('CO', 'CO2', 'H2', 'N2')
bst.settings.set_thermo([*gases, 'H2O', 'Ethanol'])
bfg = bst.Stream(CO=23, CO2=23, H2=4.5, N2=49.5, units='m3/hr', phase='g')
gas_flows = bfg.imass[gases] 
bst.settings.chemicals.define_group(
    'BFG', gases, gas_flows, wt=True
)
s = bst.Stream(BFG=1, T=150 + 273.15)
s.F_mass = 1000 # 1 MT / hr
watergas_shift = bst.Rxn(
    'CO + H2O -> CO2 + H2',
    reactant='CO', correct_atomic_balance=True, X=1
)
production = bst.Rxn(
    'H2 + CO2 -> Ethanol + H2O',
    reactant='CO2', correct_atomic_balance=True, X=1
)
watergas_shift.force_reaction(s)
production.force_reaction(s)
# Maximum theoretical yield -> 0.3474495180065154 g / g
print(s.get_flow('gal/hr', 'Ethanol') * fluegas_availability / 1e6)