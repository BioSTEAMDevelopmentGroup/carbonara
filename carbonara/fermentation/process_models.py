# -*- coding: utf-8 -*-
"""
"""
import os
import numpy as np
import biosteam as bst
from carbonara.fermentation.property_package import create_chemicals
from carbonara.fermentation.process_settings import (
    load_process_settings, 
    GWP as GWPkey,
    characterization_factors as CFs
)
from carbonara.fermentation import systems
from biorefineries.cane.data import price_distributions_2023 as dist
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
L_per_gal = 3.7854
ethanol_kg_per_gal = 2.98668849
ethanol_gal_per_kg = 1. / ethanol_kg_per_gal
ethanol_L_per_kg = ethanol_gal_per_kg * L_per_gal

# Key scenarios (4 total)
# [BFG vs RFG vs sugarcane CO2 vs. sugarcane sugars] -> EtOH (4)

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
# using optimized optimized design decisions around gas-fed bioreactor design.

# Uncertain parameters:
# Gas-fed fermentation performance
# Market prices
# Mass transfer coefficients (CO2, CO, H2)

# Optimized design decisions: 
# Length to diameter
# H2 flow rate (based on mass transfer)

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
    >>> from carbonara.fermentation import EthanolProductionProcess
    >>> pm = EthanolProductionProcess(simulate=False, feedstock='sugarcane')
    >>> pm.system.simulate()
    >>> assumptions, results = br.baseline()
    >>> pm.system.diagram() # View diagram
    >>> print(assumptions)
    
    """
    # The available land and biomass yield controls the cane crushing capacity and the transportation cost.
    # The cost of sugarcane without transportation is varied independently.
    baseline_dry_sugarcane_yield = 25.62 # dry MT / ha / y
    baseline_available_land = 1600000 * 0.3 / baseline_dry_sugarcane_yield # ha
    baseline_sugarcane_CF = 0.02931 * 0.30 / 0.25 # [kg CO2e / kg sugarcane] with transportation; from GREET, modified from moisture content of 0.75 to 0.70
    baseline_sugarcane_price = 0.035 # [USD / kg sugarcane] with transportation
    baseline_sugarcane_transportation_cost = 0.11 * baseline_sugarcane_price # Energy cane usage for cellulosic ethanol: estimation of feedstock costs; https://ageconsearch.umn.edu/record/46837/files/Energy%20Cane%20Feedstock%20Estimation_SAEA1.pdf
    baseline_sugarcane_transportation_CF = 0.029 * baseline_sugarcane_CF # Estimated from GREET 2020
    
    def update_sugarcane_feedstock(self):
        sugarcane = self.sugarcane
        sugarcane.price = self.sugarcane_price
        sugarcane.set_CF(GWPkey, self.sugarcane_CF)
        annual_crushing_capacity = self.annual_cane_crushing_capacity
        moisture_content = sugarcane.get_mass_fraction('Water')
        dry_content = 1 - moisture_content
        F_mass = 1000 * annual_crushing_capacity / self.tea.operating_hours / dry_content
        if sugarcane.isempty():
            sugarcane.imass['sugarcane'] = F_mass
        else:
            self.system.rescale(sugarcane, F_mass / sugarcane.F_mass)
    
    @property
    def annual_cane_crushing_capacity(self): # dry MT / y
        return self.available_land * self.dry_sugarcane_yield
    
    @property
    def sugarcane_price(self): # [USD / kg] with transportation
        return (
            (self.baseline_sugarcane_price - self.baseline_sugarcane_transportation_cost)
            + self.sugarcane_transportation_cost
        )
    
    @property
    def sugarcane_CF(self): # [kg CO2e / kg] with transportation
        return (
            (self.baseline_sugarcane_CF - self.baseline_sugarcane_transportation_CF)
            + self.sugarcane_transportation_CF
        )
    
    @property
    def sugarcane_transportation_cost(self): # [USD / kg] 
        return (
            self.baseline_sugarcane_transportation_cost
            * np.sqrt(self.available_land / self.baseline_available_land)
        )
    
    @property
    def sugarcane_transportation_CF(self): # [kg CO2e / kg] 
        return (
            self.baseline_sugarcane_transportation_CF
            * np.sqrt(self.available_land / self.baseline_available_land)
        )
    
    class Scenario:
        feedstock: str = 'BFG' # Alternatively 'sugarcane', 'BFG', or 'RFG'
        hydrogen: str = True
        
        @property
        def name(self):
            return self.feedstock + '/H2' if self.hydrogen else self.feedstock 
    
    @classmethod
    def as_scenario(cls, name):
        if name.endswith('/H2'):
            return cls(feedstock=name[:-3], hydrogen=True)
        else:
            return cls(feedstock=name, hydrogen=False)
    
    def create_thermo(self):
        chemicals = create_chemicals()
        thermo = bst.Thermo(chemicals)
        match self.scenario.feedstock:
            case 'BFG':
                # Composition
                # https://www.researchgate.net/publication/342635556_Advanced_Packed-Bed_Ca-Cu_Looping_Process_for_the_CO2_Capture_From_Steel_Mill_Off-Gases
                bfg = bst.Stream(CO=23, CO2=23, H2=4.5, N2=49.5, units='m3/hr', phase='g', thermo=thermo)
                gases = ('CO', 'CO2', 'H2', 'N2')
                gas_flows = bfg.imass[gases] 
                chemicals.define_group(
                    'BFG', gases, gas_flows, wt=True
                )
            case 'RFG':
                raise NotImplementedError('feedstock RFG not available')
            case 'sugarcane':
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
        return thermo        
    
    def create_system(self):
        scenario = self.scenario
        load_process_settings()
        match scenario.name:
            case 'BFG/H2':
                feedstock = bst.Stream(BFG=100, phase='g')
                system = systems.create_fluegas_hydrogen_ethanol_system(ins=feedstock)
            case 'RFG/H2':
                feedstock = bst.Stream(RFG=100, phase='g')
                system = systems.create_fluegas_hydrogen_ethanol_system(ins=feedstock)
            case 'sugarcane':
                system = systems.create_sugarcane_ethanol_system()
            case 'sugarcane/H2':
                system = systems.create_sugarcane_hydrogen_ethanol_system()
            case _:
                raise ValueError(f'invalid scenario {scenario}')
                
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
        product = 'Ethanol'
        
        # Maryland solar REC (renewable energy certificates) # https://escholarship.org/uc/item/80n4q8xc
        bst.settings.electricity_price = 0.060 
        
        def default(baseline, *args, **kwargs):
            lb = 0.80*baseline
            ub = 1.20*baseline
            return parameter(*args, bounds=(lb, ub), baseline=baseline, distribution='uniform')
        
        @parameter(units='USD/kg', element=scenario.feedstock,
                   **price_data[scenario.feedstock]) 
        def set_feedstock_price(price): 
            self.feedstock.price = price
        
        # USDA ERS historical price data without EPA RIN prices
        @parameter(distribution=dist.ethanol_no_RIN_price_distribution, element='Ethanol', 
                   baseline=dist.mean_ethanol_no_RIN_price, units='USD/L')
        def set_ethanol_price(price): # Triangular distribution fitted over the past 10 years Sep 2009 to Nov 2020
            self.ethanol.price = price * ethanol_L_per_kg

        # USDA ERS historical price data without EPA RIN prices
        @parameter(distribution=dist.RIN_D3_price_distribution, element='RIN D3', 
                   baseline=dist.mean_RIN_D3_price, units='USD/RIN')
        def set_RIN_D3_price(price): # Triangular distribution fitted over the past 10 years Sep 2009 to Nov 2020
            bst.settings.register_credit('Ethanol RIN D3', price * ethanol_L_per_kg)
        set_RIN_D3_price(dist.mean_RIN_D3_price)
        
        # USDA ERS historical price data
        @parameter(distribution=dist.RIN_D5_price_distribution, 
                   element='RIN D5', units='USD/RIN',
                   baseline=dist.mean_RIN_D5_price)
        def set_RIN_D5_price(price): # Triangular distribution fitted over the past 10 years Sep 2009 to March 2021
            bst.settings.register_credit('Ethanol RIN D5', price * ethanol_L_per_kg)
        set_RIN_D5_price(dist.mean_RIN_D5_price)
        
        if scenario.feedstock == 'sugarcane':
            if scenario.hydrogen:
                def RIN_D3_fraction():
                    D5 = self.gas_fed_bioreactor.outs[1].imass['Ethanol']
                    D3 = self.bioreactor.outs[1].imass['Ethanol']
                    return D3 / (D3 + D5)
                
                self.ethanol_storage.define_credit(
                    'Ethanol RIN D3', self.ethanol_storage.outs[0], 
                    RIN_D3_fraction,
                )
                self.ethanol_storage.define_credit(
                   'Ethanol RIN D5', self.ethanol_storage.outs[0], 
                   lambda: 1 - RIN_D3_fraction(),
                )
            else:
                self.ethanol_storage.define_credit(
                    'Ethanol RIN D3', self.ethanol_storage.outs[0], 
                )
        elif scenario.hydrogen:
            self.ethanol_storage.define_credit(
               'Ethanol RIN D5', self.ethanol_storage.outs[0], 
            )
        
        # [kg*CO2*eq / kg] From GREET 2023; Miscanthus for ethanol production
        self.BT.fuel.set_CF('GWP', CFs['Miscanthus']) 
        
        price_ub = 59 / 907.185 * 0.8 # https://www.sciencedirect.com/science/article/pii/S096195340700205X
        price_lb = 61.98 / 907.185 * 0.8 # https://farmdoc.illinois.edu/fast-tools/biomass-crop-budget-tool-miscanthus-and-switchgrass
        self.BT.fuel.price = price_baseline = 0.5 * (price_lb + price_ub)
        
        @parameter(units='USD/MT', element='biomass', 
                   bounds=[price_lb * 1000, price_ub * 1000], 
                   baseline=price_baseline * 1000)
        def set_biomass_price(price):
            self.BT.fuel.price = price / 1000
        
        @parameter(distribution=dist.electricity_price_distribution, units='USD/kWh',
                   element='electricity', baseline=dist.mean_electricity_price)
        def set_electricity_price(price): 
            bst.settings.electricity_price = price
        
        if scenario.hydrogen:
            # https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2020.00204/pdf
            @parameter(units='g/L', element='Gas-fed bioreactor',
                       bounds=(10, 30))
            def set_gas_fed_bioreactor_titer(titer):            
                self.gas_fed_bioreactor.titer[product] = titer
            
            @parameter(units='g/L/h', element='Gas-fed bioreactor',
                       bounds=[1, 2], baseline=1.5, distribution='uniform')
            def set_gas_fed_bioreactor_productivity(productivity):
                self.gas_fed_bioreactor.productivity = productivity
            
            # TODO: Add references for this parameter
            @parameter(units='g-product/g-DCW', element='Gas-fed bioreactor', 
                       bounds=[12, 33], baseline=20, distribution='uniform')
            def set_gas_fed_bioreactor_specific_yield(specific_yield):
                self.gas_fed_bioreactor.specific_yield = specific_yield
    
            # TODO: Add references for this parameter
            @parameter(units='%', element='Gas-fed bioreactor', 
                       bounds=[60, 95], baseline=60, distribution='uniform')
            def set_cellmass_recirculation(cellmass_recirculation):
                self.cellmass_centrifuge.isplit['Bacteria'] = cellmass_recirculation / 100
                
            baseline_length_to_diameter = 12
            optimized_parameter = model.optimized_parameter
            
            @optimized_parameter(
                bounds=[2, 12], baseline=baseline_length_to_diameter, 
                element='Gas-fed bioreactor', name='length to diameter'
            )
            def set_gas_fed_bioreactor_length_to_diameter(length_to_diameter):
                self.gas_fed_bioreactor.length_to_diameter = length_to_diameter
            
            # https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/20004-cost-electrolytic-hydrogen-production.pdf?Status=Master
            # Actual cost of hydrogen between 4-6 USD/kg according to DOE
            @parameter(units='USD/kg', element='H2', bounds=[2, 6],
                       baseline=3, distribution='uniform') # Natural gas 1.5 - 5; Electrolysis 3 - 7
            def set_H2_price(price):
                self.hydrogen.price = price
                
            self.hydrogen.set_CF(GWPkey, CFs['H2'])
            
        # https://pmc.ncbi.nlm.nih.gov/articles/PMC3947793/
        # https://www.capturemap.no/the-biogenic-co2-breakdown/
        self.BT.CO2_emissions_concentration = 15.0 / 100
        
        if scenario.feedstock == 'sugarcane':
            # TODO: Use agricultural data
            baseline = self.baseline_dry_sugarcane_yield                
            @parameter(
                element='feedstock', 
                baseline=baseline,
                bounds=[0.95 * baseline, 1.05 * baseline],
                distribution='triangular',
                units='DMT/ha/y', 
            )
            def set_dry_sugarcane_yield(dry_sugarcane_yield):
                self.dry_sugarcane_yield = dry_sugarcane_yield 
                
            # Distribution in line with Florida sugarcane harvesting (3-5 months).
            # https://ifactoryapp.com/predictive-maintenance/predictive-maintenance-sugar-ethanol-plants
            # Baseline from Huang's 2016 paper.
            @parameter(bounds=(120, 200), units='day/y', baseline=180, kind='coupled')
            def set_operating_days(operating_days):
                self.tea.operating_days = operating_days
            
            @default(self.baseline_available_land, element='sugarcane', units='ha', kind='coupled')
            def set_available_land(available_land):
                self.available_land = available_land
                self.update_sugarcane_feedstock()    
            
            @default(self.baseline_sugarcane_price, element='feedstock', units='USD/kg')
            def set_baseline_feedstock_price(price):
                self.baseline_sugarcane_price = price
                
        else: # Must be flue gas
            sugarcane_ethanol_yield = 88.6547560538855 # L/MT
            annual_crushing_capacity = 480000.0 # MT / yr
            baseline = sugarcane_ethanol_yield * annual_crushing_capacity / 1e6
            @default(baseline, units='10^6 L/yr', element=product)
            def set_ethanol_production_capacity(production_capacity):
                self.gas_fed_bioreactor.update_theoretical_yield()
                carbon_source = self.feedstock.copy()
                self.gas_fed_bioreactor.funneling_reactions.force_reaction(carbon_source)
                self.gas_fed_bioreactor.reactions.force_reaction(carbon_source)
                ethanol = carbon_source.imass[product] * self.tea.operating_hours * ethanol_L_per_kg / 1e6
                self.system.rescale(self.feedstock, production_capacity / ethanol)
                
            # https://ifactoryapp.com/industries/steel-plant/steel-plant-annual-shutdown-planning-turnaround-management
            @parameter(bounds=(340, 360), units='day/y', baseline=150, kind='coupled')
            def set_operating_days(operating_days):
                self.tea.operating_days = operating_days
        
        # chemicals = bst.settings.chemicals
        # self.credited_carbon_intake = lambda: (
        #     self.product.get_atomic_flow('C') * chemicals.CO2.MW * system.operating_hours
        # )
        # self.system.define_process_impact(
        #     key=GWPkey,
        #     name='Credited carbon intake',
        #     basis='kg',
        #     inventory=self.credited_carbon_intake,
        #     CF=-1.,
        # )
        
        @metric(units='USD/kg')
        def MSP():
            return self.tea.solve_price(self.ethanol)
        
        @metric(units='%')
        def IRR():
            return self.tea.solve_IRR()
        
        @metric(units='kg*CO2e/kg')
        def carbon_intensity():
            return (
                self.system.get_net_impact(GWPkey)
                / self.system.get_mass_flow(self.ethanol)
            )
        
        @metric(units='10^6 USD')
        def TCI():
            return self.tea.TCI / 1e6
        
        @metric(units='10^3 MT/yr')
        def biomass_burned(): # 825 MT / yr in NREL's cornstover model
            return self.boiler.fuel.F_mass * self.system.operating_hours / 1e6
        
        @metric(units='10^3 MT/yr')
        def hydrogen_consumption(): 
            return self.hydrogen.F_mass * self.system.operating_hours / 1e6
        
        @metric(units='kWh/kg-H2')
        def electricity_demand(): 
            return self.system.get_electricity_consumption() / (self.ethanol.F_mass * self.system.operating_hours)
        
        return model
    
    def get_sugarcane_ethanol_price(self):
        return self.set_ethanol_price.last_value + self.set_RIN_D3_price.last_value
    
    def MSP_contributions(self):
        total_cost = self.MSP() * self.ethanol.F_mass * self.tea.operating_hours
        cost = self.tea.total_production_cost(self.ethanol)
        f = cost / total_cost
        return {
            'OPEX': f,
            'CAPEX': 1 - f,
        }
    
