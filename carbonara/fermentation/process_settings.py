# -*- coding: utf-8 -*-
"""
"""
import biosteam as bst

__all__ = (
    'load_process_settings',
)
GWP = 'GWP'
characterization_factors = {
    # 'Electricity': 0.38, # [kg*CO2*eq / kWhr] From GREET 2020; NG-Fired Simple-Cycle Gas Turbine CHP Plant
    # https://www2.gov.bc.ca/assets/gov/business/natural-resource-industries/reports/carbon_intensity_of_hydrogen_production_methods.pdf
    'H2': 0, # [kg*CO2*eq / kg] From GREET 2023; Compressed G.H2 produced from PEM electrolysis (solar or wind)
    #'H2': 1.8023, # [kg*CO2*eq / kg] From GREET 2022; Compressed G.H2 produced from PEM electrolysis (solar or wind)
    'Cornstover': 0.03819, # [kg*CO2*eq / kg] From GREET 2023; Miscanthus for ethanol production
    'Miscanthus': 0.07606, # [kg*CO2*eq / kg] From GREET 2023; Miscanthus for ethanol production
    'Flue gas': -0.07134147183700712, # [kg*CO2*eq / kg] Assume C is displaced from flue gas
    'Natural gas': 0.33, # Natural gas from shell conventional recovery, GREET; includes non-biogenic emissions
    'Electricity': 0.36, # [kg*CO2*eq / kWhr] From GREET; NG-Fired Simple-Cycle Gas Turbine CHP Plant
}

def load_process_settings():
    settings = bst.settings
    settings.define_impact_indicator(GWP, 'kg*CO2e')
    settings.CEPCI = 816.0 # 2022
    cw = settings.get_cooling_agent("cooling_water")
    cw.set_property('T', 70, 'degF') # https://www.sciencedirect.com/topics/earth-and-planetary-sciences/cooling-tower
    hps = settings.get_heating_agent("high_pressure_steam")
    hps.heat_transfer_efficiency = 1.0
    hps.regeneration_price = 0.3171 + 0.097281 # Added increase in fuel cost 2016 to 2026
    hps.T = 508.991
    hps.P = 3.11e+6
    mps = settings.get_heating_agent("medium_pressure_steam")
    mps.heat_transfer_efficiency = 1.0
    mps.regeneration_price = 0.2756 + 0.097281 # Added increase in fuel cost 2016 to 2026
    mps.T = 454.770
    mps.P = 1.041e+6
    lps = settings.get_heating_agent("low_pressure_steam")
    lps.heat_transfer_efficiency = 1.0
    lps.regeneration_price = 0.2378 + 0.097281 # Added increase in fuel cost 2016 to 2026
    lps.T = 412.189
    lps.P = 344738.0
        