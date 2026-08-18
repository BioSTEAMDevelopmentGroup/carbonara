# -*- coding: utf-8 -*-
"""
"""
import os
import chaospy as cp
import biosteam as bst
from warnings import catch_warnings
from carbonara.fermentation.property_package import create_chemicals
from carbonara.fermentation.process_settings import (
    load_process_settings, 
    GWP as GWPkey,
    characterization_factors as CFs
)
from carbonara.fermentation.systems import create_hydrogen_fermentation_system
from biorefineries.tea import (
    create_cellulosic_ethanol_tea as create_tea
)

__all__ = (
    'PlatformBioproductProcess',
)

# DO NOT DELETE:
# natural_gas = bst.Chemical('CH4')
# natural_gas.phase = 'g'
# natural_gas.set_property('T', 60, 'degF')
# natural_gas.set_property('P', 14.73, 'psi')
# original_value = natural_gas.imol['CH4']
# natural_gas.imass['CH4'] = 1 
# V_ng = natural_gas.get_total_flow('m3/hr')
# natural_gas.imol['CH4'] = original_value
V_ng = 1.473318463076884 # Natural gas volume at 60 F and 14.73 psi [m3 / kg]
results_folder = os.path.join(os.path.dirname(__file__), 'results')

price_data = {
    'Ethanol': {},
    'AceticAcid': {},
    'BFG': {}, # Blast Furnace Gas (flue gas from steelmaking)
    'RFG': {}, # Refinery Flue Gas
    'sugarcane': {},
    'sugarcane 2G': {},
}
titer_data = {
}
productivity_data = {
}
yield_data = {
}

# Key scenarios (5 total)
# BFG, AcOH vs EtOH (2)
# BFG vs RFG vs sugarcane, EtOH (3 - 1)
# sugarcane CO2/EtOH  vs. sugarcane sugars/EtOH (2 - 1)

# Key assumptions
# Electricity - assume renewable
# Steam - assume solar

# LCA methodology used: end-of-life
# Questions:
# 1. What bioproduct is best?
# Ethanol, at comparable performance and low H2 price (requires more reducing power).
# 2. Which feedstocks in best? Why?
# * Concentrated CO2 is critical for mass transfer, RFG is not feasible
# * While BFG is less carbon instensive, 
#   due to avoiding emissions associated to biomass,
#   the cost is infeasible.
# * Traditional sugarcane offers integrated separations/heat/power, which
#   supports economies-of-scale and makes carbon utilization feasible.
# * Cellulosic ethanol integration is a disadvantage because biomass is used to 
#   satisfy the high power/heating demand, and there is not enough biomass left
#   to justify the cost of pretreatment equipment.
# 3. Carbon utilization is the more economical route with integration of 
#    separation, heat, and power equipment at a biorefinery.

class PlatformBioproductProcess(bst.ProcessModel):
    """
    Examples
    --------
    >>> from biorefineries.gas_fermentation import Biorefinery
    >>> pm = PlatformBioproductProcess(simulate=False, scenario='BFG/EtOH')
    >>> pm.system.simulate()
    >>> assumptions, results = br.baseline()
    >>> pm.system.diagram() # View diagram
    >>> print(assumptions)
    
    """
    class Scenario:
        name: str = 'BFG/ethanol'
        product: str = 'ethanol'
        glucose_growth: bool = True
        feedstock: str = 'BFG' # Alternatively 'biomass' or 'glucose'
        fuel: str = 'cornstover' # Either 'miscanthus' or 'cornstover'
    
    @property
    def name(self):
        return self.scenario.name
    
    @classmethod
    def as_scenario(cls, scenario):
        try:
            feedstock, product = scenario.split('/')
        except:
            raise ValueError("invalid scenario")
        return cls.Scenario(
            product=product,
            glucose_growth=True,
            feedstock=feedstock,
            fuel='cornstover',
            name=scenario,
        )
    
    def optimize(self):
        with catch_warnings(action="ignore"):
            results, convergence_model = self.model.optimize(
                self.MSP,  
                convergence_model='linear regressor', 
                # method='differential evolution',
            )
        for p, x in zip(self.model.optimized_parameters, results.x): p.setter(x)
        return results
    
    def create_thermo(self):
        return create_chemicals(
            [self.scenario.feedstock, 
             self.scenario.product, 
             self.scenario.biomass]
        )
    
    def create_system(self):
        scenario = self.scenario
        load_process_settings()
        system = create_hydrogen_fermentation_system(
            glucose_growth=scenario.glucose_growth,
            product=scenario.product,
            feedstock=scenario.feedstock,
            fuel=scenario.biomass,
        )
        self.tea = create_tea(system)
        system.set_tolerance(
            rmol=1e-4, mol=1e-3, maxiter=50, 
            method='wegstein', subsystems=True
        )
        return system
    
    def create_model(self):
        system = self.system
        scenario = self.scenario
        model = bst.Model(system)
        parameter = model.parameter
        metric = model.metric
        
        def uniform(baseline, *args, **kwargs):
            bounds = [0.8 * baseline, 1.2 * baseline]
            return parameter(*args, **kwargs, baseline=baseline, bounds=bounds)
        
        @parameter(units='USD/kg', element=scenario.feedstock,
                   **price_data[scenario.feedstock]) 
        def set_feedstock_price(price): 
            self.feedstock.price = price
        
        @parameter(units='USD/kg', element=scenario.product, 
                   **price_data[scenario.product])
        def set_product_price(price):
            self.product.price = price
        
        # https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/20004-cost-electrolytic-hydrogen-production.pdf?Status=Master
        # Actual cost of hydrogen between 4-6 USD/kg according to DOE
        @parameter(units='USD/kg', element='H2', bounds=[2, 6],
                   baseline=3, distribution='uniform') # Natural gas 1.5 - 5; Electrolysis 3 - 7
        def set_H2_price(price):
            if scenario.carbon_source == 'glucose': return
            self.hydrogen.price = price
        
        @parameter(units='g/L', element='Gas-fed bioreactor',
                   **titer_data[scenario.product])
        def set_gas_fed_bioreactor_titer(titer):
            self.gas_fed_bioreactor.titer[scenario.product] = titer
        
        @parameter(units='g/L/h', element='Gas-fed bioreactor',
                   bounds=[1, 2], baseline=1.5, distribution='uniform')
        def set_gas_fed_bioreactor_productivity(productivity):
            self.gas_fed_bioreactor.productivity = productivity
        
        @parameter(units='% theoretical', element='Gas-fed bioreactor', 
                   bounds=[85, 95], baseline=90, distribution='uniform')
        def set_gas_fed_bioreactor_yield(product_yield):
            self.gas_fed_bioreactor.product_yield = product_yield
        
        # @parameter(distribution=dist.electricity_price_distribution, units='USD/kWh',
        #            element='electricity', baseline=dist.mean_electricity_price)
        # def set_electricity_price(price): 
        #     bst.settings.electricity_price = price
        
        # https://pmc.ncbi.nlm.nih.gov/articles/PMC3947793/
        # https://www.capturemap.no/the-biogenic-co2-breakdown/
        self.BT.CO2_emissions_concentration = 15.0 / 100 # 
        
        @parameter(units='MT/yr', element=scenario.product, 
                   bounds=[20000, 50000], baseline=35000)
        def set_production_capacity(production_capacity):
            self.production_capacity = production_capacity
                
        @system.add_specification(simulate=True)
        def adjust_production_capacity():
            capacity = self.production_capacity / system.operating_hours * 1000 # kg / hr
            self.system.simulate()
            self.system.rescale(self.AcOH_media, capacity / self.product.F_mass) 
        
        baseline_length_to_diameter = 12
        optimized_parameter = model.optimized_parameter
        
        @optimized_parameter(
            bounds=[2, 12], baseline=baseline_length_to_diameter, 
            element='Gas-fed bioreactor', name='length to diameter'
        )
        def set_gas_fed_bioreactor_length_to_diameter(length_to_diameter):
            self.gas_fed_bioreactor.length_to_diameter = length_to_diameter
        
        @optimized_parameter(bounds=[0.2, 0.6], baseline=0.5,
                             element='Gas-fed bioreactor', 
                             name='agitation power')
        def set_gas_fed_bioreactor_agitation_power(kW_per_m3):
            self.gas_fed_bioreactor.kW_per_m3 = kW_per_m3
        
        chemicals = bst.settings.chemicals
        self.credited_carbon_intake = lambda: (
            self.product.get_atomic_flow('C') * chemicals.CO2.MW * system.operating_hours
        )
        self.system.define_process_impact(
            key=GWPkey,
            name='Credited carbon intake',
            basis='kg',
            inventory=self.credited_carbon_intake,
            CF=-1.,
        )
        
        @parameter(units='USD/MT', element='biomass', 
                   **price_data[scenario.biomass])
        def set_biomass_price(price):
            self.BT.fuel.price = price / 1000
        
        # bst.settings.electricity_price = 0.060 # Maryland solar REC (renewable energy certificates) # https://escholarship.org/uc/item/80n4q8xc
        self.hydrogen.set_CF(GWPkey, CFs['H2'])
        
        @metric(units='USD/kg')
        def MSP():
            return self.tea.solve_price(self.product)
        
        @metric(units='kg*CO2e/kg')
        def carbon_intensity():
            return (
                self.system.get_net_impact(GWPkey)
                / self.system.get_mass_flow(self.product)
            )
        
        @metric(units='10^6 USD')
        def TCI():
            return self.tea.TCI / 1e6
        
        @metric(units='% theoretical')
        def product_yield_to_hydrogen():
            if scenario.carbon_source == 'glucose': return 0
            return self.product.get_atomic_flow('H') / self.hydrogen.get_atomic_flow('H')
        
        @metric(units='10^3 MT/yr')
        def biomass_burned(): # 825 MT / y for NREL's cornstover model
            return self.BT.fuel.F_mass * self.system.operating_hours / 1e6
        
        @metric(units='10^3 MT/yr')
        def hydrogen_consumption(): 
            return self.hydrogen.F_mass * self.system.operating_hours / 1e6
        
        @metric(units='kWh/kg-H2')
        def electricity_demand(): 
            return self.system.get_electricity_consumption() / (self.product.F_mass * self.system.operating_hours)
        
        return model
    
    def MSP_contributions(self):
        total_cost = self.MSP() * self.product.F_mass * self.tea.operating_hours
        cost = self.tea.total_production_cost(self.product)
        f = cost / total_cost
        return {
            'OPEX': f,
            'CAPEX': 1 - f,
        }
    