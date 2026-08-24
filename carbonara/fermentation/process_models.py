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
from biorefineries.cane.systems import create_sugarcane_to_ethanol_system
from biorefineries.tea import (
    create_cellulosic_ethanol_tea as create_tea
)

__all__ = (
    'EthanolProductionProcess',
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
    'BFG': {}, # Blast Furnace Gas (flue gas from steelmaking)
    'RFG': {}, # Refinery Flue Gas
    'sugarcane': {},
}
titer_data = {
}
productivity_data = {
}
yield_data = {
}

# Key scenarios (4 total)
# BFG vs RFG vs sugarcane CO2  vs. sugarcane sugars, EtOH (4)

# Key assumptions
# Electricity - assume renewable
# Steam - assume biomass

# LCA methodology used: end-of-life

# Presentation:
# Explain the importance of uncertainty, harmonized assumptions, and design of bioreactor
# Show big plot of uncertainty across each configuration, with overlap.

# Let's see where most of the uncertainties come from... 
# Design decisions are extremely important! We should optimize these for each configuration
# This reduces uncertainty, but we still do not have any conclusive insights.

# We have to take a closer look by comparing each scenario under harmonized assumptions.
# In the first graph we are comparing BFG vs RFG, (BFG wins because XYZ).
# In the second graph we compare BFG vs sugarcane, (sugarcane is more economical but more carbon intensive)
# In the last graph we can see how integrating CU with sugarcane is better than just sugarcane.

# General Approach:
# Compare configurations under uncertainty, 
# under harmonized market assumtions
# using optimized optimized design decision.

# Scalable analysis problem:
# Minutes to solve
# Thousands of simulations needed for optimization, 
# Thousands of scenarios for uncertainty analysis:
# 1000 * 1000 * 1 min -> 2 years of simulation.

# Methology for scalability:
# f(d, c, m) -> h(g(d, c), c, m)
# g(p) -> g*(p) | replace g with a surrogate ML model g*
# h -> Cash flow analysis
# g -> Process simulation
# d -> Design decisions
# * Length to diameter
# * H2 to CO2 feed ratio
# * Agitation
# * Bubble column or agitated
# m -> market prices
# c -> Other contextual parameters (cannot be controlled)
# * Mass transfer coefficients (CO2, CO, H2)
# * Processing capacity
# Create ML model as a GP using a mesh grid of data points
# (5^6 * (5 + 1) -> 93,750 points x 3 configurations).

# Questions:
# 1. What bioproduct is best?
# Answer -> Ethanol, at comparable performance and low H2 price (requires more reducing power).
# Analysis -> Break-even hydrogen price vs titer under uncertainty, assuming constant low and high productivities.
# 2. Which feedstocks are best? Why?
# Answer -> 
# * Concentrated CO2 is critical for mass transfer, RFG is not feasible
# * While BFG is less carbon instensive, due to avoiding emissions 
#   associated to biomass, the cost is infeasible.
# * Traditional sugarcane offers integrated separations/heat/power, 
#   which supports economies-of-scale and makes carbon utilization feasible.
# * Cellulosic ethanol integration is a disadvantage because biomass is 
#   used to satisfy the high power/heating demand, and there is not enough 
#   biomass left to justify the cost of pretreatment equipment.
# Analysis ->
# * Harmonized uncertainty analysis for each questions.
# 3. What can we do to make carbon utilization more feasible? 
# Answer -> 
#    Carbon utilization is the more economical route with integration of 
#    separation, heat, and power equipment at a biorefinery.
    

class EthanolProductionProcess(bst.ProcessModel):
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
        feedstock: str = 'BFG' # Alternatively 'sugarcane', 'BFG', or 'RFG'
        integrated: bool = True # Whether or not CO2 from anaerobic fermentation is valorized
    
    def create_thermo(self):
        chemicals = create_chemicals()
        chemicals.compile()
        feedstock = self.scenario.feedstock
        if feedstock == 'BFG':
            # Composition
            # https://www.researchgate.net/publication/342635556_Advanced_Packed-Bed_Ca-Cu_Looping_Process_for_the_CO2_Capture_From_Steel_Mill_Off-Gases
            bfg = bst.Stream(CO=23, CO2=23, H2=4.5, N2=49.5, units='m3/hr', phase='g')
            gases = ('CO', 'CO2', 'H2', 'N2')
            gas_flows = bfg.imass[gases] 
            chemicals.define_group(
                'BFG', gases, gas_flows, wt=True
            )
        elif feedstock == 'sugarcane':
            sugarcane = dict(
                Water=0.7,
                Glucose=0.01208,
                Sucrose=0.1369,
                Ash=0.006,
                Cellulose=0.06115,
                Hemicellulose=0.03608,
                Lignin=0.03276,
                Solids=0.015,
            )
            components, flows = zip(*sugarcane.items())
            chemicals.define_group(
                'sugarcane', components, flows, wt=True
            )    
        chemicals.define_group( # Assume Miscanthus is a good representative biomass
            'Biomass', 
            ['Water', 'Solids', 
             'Ash', 'Lignin', 
             'Cellulose', 'Hemicellulose'],
            [0.2, 0.04023529411764703, 
             0.015647058823529406, 0.1616, 
             0.3592, 0.22331764705882354],
            wt=True,
        )
        return chemicals        
    
    def create_system(self):
        scenario = self.scenario
        load_process_settings()
        feedstock = scenario.feedstock
        if feedstock == 'sugarcane':
            with bst.System() as system:
                etoh_sys = create_sugarcane_to_ethanol_system(
                    
                    WWT_kwargs=dict(kind='high-rate')
                )
                if scenario.integrated:
                    system = create_hydrogen_fermentation_system(
                        glucose_growth=scenario.glucose_growth,
                        product=scenario.product,
                        feedstock=scenario.feedstock,
                        fuel=scenario.biomass,
                    )
        else:
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
        
        @parameter(units='by mol theoretical', element='Gas-fed bioreactor',
                   bounds=[0.8, 1.2], baseline=1, distribution='uniform')
        def set_gas_fed_bioreactor_H2_CO2_ratio(H2_CO2_ratio):
            self.gas_fed_bioreactor.H2_CO2_ratio = H2_CO2_ratio
        
        @parameter(units='g/L', element='Gas-fed bioreactor',
                   **titer_data[scenario.product])
        def set_gas_fed_bioreactor_titer(titer):
            self.gas_fed_bioreactor.titer[scenario.product] = titer
        
        @parameter(units='g/L/h', element='Gas-fed bioreactor',
                   bounds=[1, 2], baseline=1.5, distribution='uniform')
        def set_gas_fed_bioreactor_productivity(productivity):
            self.gas_fed_bioreactor.productivity = productivity
        
        @parameter(units='g-product/g-DCW', element='Gas-fed bioreactor', 
                   bounds=[12, 33], baseline=20, distribution='uniform')
        def set_gas_fed_bioreactor_specific_yield(specific_yield):
            self.gas_fed_bioreactor.specific_yield = specific_yield
        
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
    