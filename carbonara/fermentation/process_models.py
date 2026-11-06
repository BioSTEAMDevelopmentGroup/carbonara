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
from typing import Optional
from carbonara.fermentation import systems
from biorefineries.cane.data import price_distributions_2023 as dist
from biorefineries.tea import (
    create_cellulosic_ethanol_tea as create_tea
)

__all__ = (
    'EthanolProductionProcess',
)

# Inconsisted energy balance allows for consistent VLE at reboiler/condenser 
# stages and enables HXN on reboilers
bst.Distillation.use_overall_energy_balance = False 

# # https://www.researchgate.net/publication/351102338_THERMOECONOMIC_ANALYSIS_OF_ALKHOMS_STEAM_POWER_PLANT_AT_DIFFERENT_OPERATING_LOADS
# bst.BoilerTurbogenerator.cost_items['Turbogenerator'].n = 0.7

# # Carbon credit for sugarcane ethanol equivalent to RIN
GWP_sugarcane = 0.27 # kg / L
ethanol_energy = 0.67 # % gasoline
GWP_gasoline = 2.31 # kg / L 
GWP_reduction = GWP_gasoline * ethanol_energy - GWP_sugarcane # kg-CO2e / L-ethanol
sugarcane_ethanol_carbon_credit = dist.mean_RIN_D5_price / GWP_reduction * 1000 # ~160 USD / kg-CO2

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

L_per_gal = 3.7854
ethanol_kg_per_gal = 2.98668849
ethanol_gal_per_kg = 1. / ethanol_kg_per_gal
ethanol_L_per_kg = ethanol_gal_per_kg * L_per_gal

# Blast furnace production
BFG_to_pig_iron = np.array([2, 3]) # by wt
pig_iron_produciton = np.array([3, 10]) # MTPA -> Million ton per annual
BFG_flared = np.array([2, 5]) # %
BFG_available = tuple(BFG_to_pig_iron * pig_iron_produciton * BFG_flared / 100) # [0.18, 1.5] 10^6 MT / yr

# FCC partial combustion flue gas availability
# Source: quick gemini search assuming Singapore Jurong island and heuristing estimates for FCC.
# TODO: improve this estimate and add detailed calculation.
RFG_available = np.array([6.3, 10.5]) # 10^6 MT / yr

# Key scenarios (3 total)
# [BFG vs sugarcane CO2 vs. sugarcane sugars] -> EtOH (4)

# LCA methodology used: cradle-to-refinery-gate, without crediting carbon from waste and biogenic sources for a fair comparison, which will ultimately be burned anyway (otherwise numbers would be negative)

# Presentation:
# Explain the importance of uncertainty, harmonized assumptions, and design of bioreactor.
# Note that critical bioreactor design decisions were optimized at each scenario.
# Show landscape of potential outcomes for each configuration.
# Show sensitivities across configurations.

# We have to take a closer look by comparing each scenario under harmonized assumptions.
# In the first graph we compare BFG vs sugarcane, (sugarcane is more economical but more carbon intensive)
# In the second graph we can see how integrating CU with sugarcane is better than just sugarcane.

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

# Questions (answers hypothetical for now):
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
    
# Uncertainty analysis plots:
# Carbon mitigation cost vs. carbon intensity (economic vs environmental impact)
# Carbon efficiency vs energy efficiency (scalability -> how efficient are we in using our carbon and energy resources)

def _MSP_at_L2D(L2D, system, gas_fed_bioreactor, MSP):
    gas_fed_bioreactor.length_to_diameter = L2D
    system.simulate()
    return MSP()

def _optimize_length_to_diameter(pm): 
    # Optimize up to the nearest integer; MSP is not sensitive to L2D except
    # when it is too low (and too much H2 is not consumed)
    args = (pm.system, pm.gas_fed_bioreactor, pm.MSP)
    f = _MSP_at_L2D
    y7 = f(7, *args)
    y8 = f(8, *args)
    if y8 < y7: return
    x0 = 8
    y0 = y7
    for x1 in range(6, 1, -1):
        y1 = f(x1, *args)
        if y1 > y0: 
            f(x0, *args)
            break
        y0 = y1
        x0 = x1

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
    processing_areas = {
        'sugarcane1': ['Facilities', 'Juicing', 'CoFerm', 'EtOH sep', 'WWT'],
        'sugarcane1/H2': ['Facilities', 'Juicing', 'CoFerm', 'Gas-Ferm', 'EtOH sep', 'WWT'],
        'sugarcane2': ['Facilities', 'Juicing', 'Pretreatment', 'CoFerm', 'EtOH sep', 'WWT'],
        'sugarcane2/H2': ['Facilities', 'Juicing', 'Pretreatment', 'CoFerm', 'Gas-Ferm', 'EtOH sep', 'WWT'],
        'BFG/H2': ['Facilities', 'Gas-Ferm', 'EtOH sep', 'WWT'],
    }
    
    # The available land and biomass yield controls the cane crushing capacity and the transportation cost.
    # The cost of sugarcane without transportation is varied independently.
    baseline_dry_sugarcane_yield = 25.62 # dry MT / ha / y
    baseline_available_land = 1600000 * 0.3 / baseline_dry_sugarcane_yield # ha
    baseline_sugarcane_CF = 0.02931 * 0.30 / 0.25 # [kg CO2e / kg sugarcane] with transportation; from GREET, modified from moisture content of 0.75 to 0.70
    baseline_sugarcane_price = 0.035 # [USD / kg sugarcane] with transportation
    baseline_sugarcane_transportation_cost = 0.11 * baseline_sugarcane_price # Energy cane usage for cellulosic ethanol: estimation of feedstock costs; https://ageconsearch.umn.edu/record/46837/files/Energy%20Cane%20Feedstock%20Estimation_SAEA1.pdf
    baseline_sugarcane_transportation_CF = 0.029 * baseline_sugarcane_CF # Estimated from GREET 2020
    
    hydrogen_energy_density = 39.385 # kWh / kg
    PEM_energy_efficiency = 0.72
    
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
        # m3/ha/y * ha -> L/y
        # L/y * (y / hr) -> L / hr
        water_usage = 1000 * self.irrigation_requirement * self.available_land / self.tea.operating_hours # L / hr
        self.sugarcane.set_CF('WU', water_usage / F_mass, units='L', basis='kg')
    
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
        generation: Optional[int] = None
        hydrogen: str = True
        
        @property
        def name(self):
            name = self.feedstock
            if self.generation: name += str(self.generation)
            if self.hydrogen: name += '/H2'
            return name
    
    @classmethod
    def as_scenario(cls, name):
        if name.startswith('sugarcane'):
            hydrogen = False
            feedstock = 'sugarcane'
            name = name[len(feedstock):]
            if name[0].isnumeric():
                generation = int(name[0])
                name = name[1:]
            else:
                generation = 1
        else:
            generation = None
            feedstock = name[:3]
            name = name[3:]
        if name.endswith('/H2'):
            hydrogen = True
        else:
            hydrogen = False
        return cls.Scenario(feedstock, generation, hydrogen)
    
    def create_thermo(self):
        chemicals = create_chemicals()
        thermo = bst.Thermo(chemicals)
        chemicals.define_group('Cellmass', ['Yeast', 'Bacteria'])
        chemicals.set_alias('Cellulose', 'Glucan')
        chemicals.set_alias('Hemicellulose', 'Xylan')
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
            case 'sugarcane':
                sugarcane = dict(
                    Water=0.7,
                    Glucose=0.01208,
                    Sucrose=0.1369,
                    Ash=0.006,
                    Cellulose=0.06115,
                    Hemicellulose=0.03608,
                    Lignin=0.03276 + 0.015, # Treat waxes solids as lignin
                    # Solids=,
                )
                components, flows = zip(*sugarcane.items())
                chemicals.define_group(
                    'sugarcane', components, flows, wt=True
                )
            case 'RFG':
                # Partial combustion at FCC for petroleum refining (like in Jurong Island)
                rfg = bst.Stream(CO=8, CO2=10, N2=75, H2O=7, units='m3/hr', phase='g', thermo=thermo)
                gases = ('CO', 'CO2', 'N2', 'H2O')
                gas_flows = rfg.imass[gases] 
                chemicals.define_group(
                    'RFG', gases, gas_flows, wt=True
                )
            case _:
                raise ValueError(f'invalid feedstock {self.scenario.feedstock!r}')
        chemicals.define_group( # Assume Miscanthus is a good representative biomass
            'Biomass', 
            ['Water', # 'Solids', # treat solids as lignin
             'Ash', 'Lignin', 
             'Cellulose', 'Hemicellulose'],
            [0.2, 
             0.015647058823529406, 0.1616 + 0.04023529411764703, 
             0.3592, 0.22331764705882354],
            wt=True,
        )
        return thermo        
    
    def create_system(self):
        scenario = self.scenario
        load_process_settings()
        match scenario.name:
            case 'BFG/H2':
                feedstock = bst.Stream(BFG=100, phase='g', P=101325 * 2)
                system = systems.create_fluegas_hydrogen_ethanol_system(ins=feedstock, fuel_source='BFG')
            case 'RFG/H2':
                feedstock = bst.Stream(RFG=100, phase='g', P=101325 * 2)
                system = systems.create_fluegas_hydrogen_ethanol_system(ins=feedstock, fuel_source='RFG')
            case 'sugarcane1':
                system = systems.create_sugarcane_1G_ethanol_system()
                feedstock = system.ins[0]
            case 'sugarcane2':
                system = systems.create_sugarcane_2G_ethanol_system()
                feedstock = system.ins[0]
            case 'sugarcane1/H2':
                system = systems.create_sugarcane_1G_hydrogen_ethanol_system()
                feedstock = system.ins[0]
            case 'sugarcane2/H2':
                system = systems.create_sugarcane_2G_hydrogen_ethanol_system()
                feedstock = system.ins[0]
            case _:
                raise ValueError(f'invalid scenario {scenario!r}')
    
        self.feedstock = feedstock                
        self.tea = create_tea(system)
        self.tea.income_tax = 0.21
        system.set_tolerance(
            rmol=1e-4, mol=1e-3, maxiter=100, 
            method='fixed-point', subsystems=True
        )
        self.unit_groups = unit_groups = bst.UnitGroup.group_by_area(system.units)
        for i, j in zip(unit_groups, self.processing_areas[scenario.name]): i.name = j
        return system
    
    def create_model(self):
        system = self.system
        scenario = self.scenario
        model = bst.Model(system)
        parameter = model.parameter
        metric = model.metric
        product = 'Ethanol'
        
        if scenario.feedstock == 'sugarcane':
            # USDA
            bst.settings.register_credit('Ethanol RIN D5', dist.mean_RIN_D5_price * ethanol_L_per_kg)
            
            self.ethanol_storage.define_credit(
                'Ethanol RIN D5', self.ethanol_storage.outs[0], 
            )
            
            # https://pmc.ncbi.nlm.nih.gov/articles/PMC3947793/
            # https://www.capturemap.no/the-biogenic-co2-breakdown/
            self.BT.CO2_emissions_concentration = 15.0 / 100
            
            if scenario.hydrogen:
                @system.add_specification(simulate=False)
                def optimize_length_to_diameter():
                    _optimize_length_to_diameter(self)
            
            # biomass_price_ub = 59 / 907.185 * 0.8 # https://www.sciencedirect.com/science/article/pii/S096195340700205X
            # biomass_price_lb = 61.98 / 907.185 * 0.8 # https://farmdoc.illinois.edu/fast-tools/biomass-crop-budget-tool-miscanthus-and-switchgrass
            biomass_price_baseline = 0.052
            
            # [kg*CO2*eq / kg] From GREET 2023; Miscanthus for ethanol production
            self.BT.fuel.set_CF('GWP', CFs['Miscanthus']) 
            self.BT.fuel.price = biomass_price_baseline 
            
            # https://www-sciencedirect-com.libproxy1.nus.edu.sg/science/article/pii/S0360544223004930
            self.BT.boiler_efficiency = 86.75 / 100 # TODO: add uncertainty to this value
            
        elif scenario.feedstock in ('BFG', 'RFG'):
            # https://files.gao.gov/reports/GAO-26-107711/index.html
            self.carbon_credit_45Q = 85 # USD / MT-CO2
            bst.settings.register_credit('Carbon credit 45Q', self.carbon_credit_45Q / 1000)
            self.BT.boiler_efficiency = 90 / 100 # TODO: add uncertainty to this value
            
            def GWP_reduction():
                GWP_ethanol = carbon_intensity()
                GWP_corn_ethanol = 1.22 # https://www.osti.gov
                return GWP_corn_ethanol - GWP_ethanol # kg-CO2e / L-ethanol
            
            self.ethanol_storage.define_credit(
                'Carbon credit 45Q', self.ethanol_storage.outs[0], 
                lambda: GWP_reduction() * ethanol_L_per_kg, # kg-CO2e / kg-ethanol
            )
            self.hydrogen.set_CF(GWPkey, CFs['H2'])
            
            @system.add_specification(simulate=False)
            def boiler_outside_system_boundary():
                _optimize_length_to_diameter(self)
                self.BT._setup() # Capital cost already incurred by steelmill
        
            self.BT.fuel.set_CF('GWP', 0) 
            self.BT.fuel_price = 0
            
        def default(baseline, *args, **kwargs):
            lb = 0.90*baseline
            ub = 1.10*baseline
            return parameter(*args, bounds=(lb, ub), baseline=baseline, distribution='uniform')
        
        # @parameter(units='USD/MT', element='biomass', 
        #            bounds=[biomass_price_lb * 1000, biomass_price_ub * 1000], 
        #            baseline=biomass_price_baseline * 1000)
        # def set_biomass_price(price):
        #     self.BT.fuel.price = price / 1000
        
        # USDA ERS historical price data without EPA RIN prices
        @parameter(distribution=dist.ethanol_no_RIN_price_distribution, element='Ethanol', 
                   baseline=dist.mean_ethanol_no_RIN_price, units='USD/L')
        def set_ethanol_price(price): # Triangular distribution fitted over the past 10 years Sep 2009 to Nov 2020
            self.ethanol.price = price * ethanol_L_per_kg
        
        # USDA ERS historical price data
        @parameter(distribution=dist.RIN_D5_price_distribution, 
                   element='RIN D5', units='USD/RIN',
                   baseline=dist.mean_RIN_D5_price)
        def set_RIN_D5_price(price): # Triangular distribution fitted over the past 10 years Sep 2009 to March 2021
            bst.settings.register_credit('Ethanol RIN D5', price * ethanol_L_per_kg)
        
        # Levelized Cost of Energy (LCOE); wholesale generation cost.
        # https://pv-magazine-usa.com/2025/06/17/despite-low-gas-prices-solar-wind-remain-cheapest-sources-of-power-in-u-s/
        # Lower bounds represents the lowest LCOE; higher bound with the cost of batteries.
        # These are super optimistic assumptions.
        # https://about.bnef.com/insights/clean-energy/battery-storage-costs-hit-record-lows-as-costs-of-other-clean-power-technologies-increased-bloombergnef/
        @parameter(distribution='uniform', bounds=(0.04, 0.08), units='USD/kWh',
                   element='electricity', baseline=0.06)
        def set_electricity_price(price): 
            bst.settings.electricity_price = price
            if scenario.feedstock != 'sugarcane':
                # No cooling tower, cost will scale with electricity price.
                cooling_electricity = 0.004542801314522282 * 18.015 # kWh / kmol
                cw = bst.settings.get_cooling_agent('cooling_water')
                cw.regeneration_price = cooling_electricity * price
                bst.HeatUtility.set_CF(cw.ID, 'WU', 0.011) # Evaporation + blowdown
                # self.BT.fuel.price = price * feedstock_energy_density * conversion_efficiency
        
        # [10 g/L] https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2020.00204/pdf
        # https://www.sciencedirect.com/science/article/abs/pii/S095816691100019X?via%3Dihub
        # [41 g/L] https://www.sciencedirect.com/science/article/abs/pii/S096085242500118X
        # [50 g/L target in Lanza Tech patent] https://patents.google.com/patent/US20160115505A1/en
        @parameter(units='g/L', element='Gas-fed bioreactor',
                   bounds=(40, 50), baseline=41)
        def set_gas_fed_bioreactor_titer(titer):  
            if not scenario.hydrogen: return
            self.gas_fed_bioreactor.titer[product] = titer
        
        @parameter(units='g/L/h', element='Gas-fed bioreactor',
                   bounds=[1, 2], baseline=1.5, distribution='uniform')
        def set_gas_fed_bioreactor_productivity(productivity):
            if not scenario.hydrogen: return
            self.gas_fed_bioreactor.productivity = productivity
        
        # TODO: Add references for this parameter
        @parameter(units='g-product/g-DCW', element='Gas-fed bioreactor', 
                   bounds=[12, 33], baseline=20, distribution='uniform')
        def set_gas_fed_bioreactor_specific_yield(specific_yield):
            if not scenario.hydrogen: return
            self.gas_fed_bioreactor.specific_yield = specific_yield

        # 2 - 4 times as much https://www.sciencedirect.com/science/article/pii/S1369703X22001747
        @parameter(element='Gas-fed bioreactor', 
                   bounds=[2, 4], baseline=3, 
                   distribution='uniform')
        def set_kLa_correction_factor(kLa_correction_factor):
            if not scenario.hydrogen: return
            self.gas_fed_bioreactor.kLa_correction_factor = kLa_correction_factor
            
        # TODO: Add references for this parameter
        @parameter(units='%', element='Gas-fed bioreactor', 
                   bounds=[60, 95], baseline=60, distribution='uniform')
        def set_cellmass_recirculation(cellmass_recirculation):
            if not scenario.hydrogen: return
            self.cellmass_centrifuge.isplit['Bacteria'] = cellmass_recirculation / 100
        
        # https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/20004-cost-electrolytic-hydrogen-production.pdf?Status=Master
        # Actual cost of hydrogen between 4-6 USD/kg according to DOE
        @parameter(units='USD/kg', element='H2', bounds=[1, 3],
                   baseline=2.87, distribution='uniform')
        def set_H2_price_floor(H2_price_floor):
            if not scenario.hydrogen: return
            electricity_price = bst.settings.electricity_price
            self.hydrogen.price = H2_price_floor + electricity_price * self.hydrogen_energy_density / self.PEM_energy_efficiency
        
        # TODO: check source and confirm
        # https://wires.onlinelibrary.wiley.com/doi/10.1002/wene.70035
        @parameter(units='L/kg', element='H2', bounds=[15, 30],
                   baseline=20, distribution='uniform')
        def set_H2_water_usage(water_usage):
            if not scenario.hydrogen: return
            self.hydrogen.set_CF('WU', water_usage)
        
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
            if scenario.feedstock != 'sugarcane': return
            self.dry_sugarcane_yield = dry_sugarcane_yield 
            
        # Distribution in line with Florida sugarcane harvesting (3-5 months).
        # https://ifactoryapp.com/predictive-maintenance/predictive-maintenance-sugar-ethanol-plants
        # Baseline from Huang's 2016 paper.
        @parameter(bounds=(120, 200), units='day/y', baseline=180)
        def set_sugarcane_operating_days(sugarcane_operating_days):
            if scenario.feedstock != 'sugarcane': return
            self.tea.operating_days = sugarcane_operating_days
        
        # TODO: Get values from GREET and other sources
        @parameter(distribution='uniform', bounds=(14660, 15580), element='sugarcane', 
                   baseline=15000, units='m3/hectare')
        def set_irrigation_requirement(irrigation_requirement):
            if scenario.feedstock != 'sugarcane': return
            self.irrigation_requirement = irrigation_requirement
        
        @default(self.baseline_available_land, element='sugarcane', units='ha')
        def set_available_land(available_land):
            if scenario.feedstock != 'sugarcane': return
            self.available_land = available_land
            self.update_sugarcane_feedstock()
        
        @default(self.baseline_sugarcane_price, element='sugarcane', units='USD/kg')
        def set_baseline_sugarcane_price(price):
            if scenario.feedstock != 'sugarcane': return
            self.baseline_sugarcane_price = price

        # https://pmc.ncbi.nlm.nih.gov/articles/PMC3970039/
        # https://www.researchgate.net/publication/397090476_Analyzing_the_Potential_of_Sugarcane_Juice_for_Bio-ethanol_Production
        @parameter(units='% theoretical', element='juice bioreactor', 
                   bounds=[90, 95], baseline=92, distribution='uniform')
        def set_juice_bioreactor_yield(ethanol_yield):
            if not scenario.generation == 1: return
            self.juice_bioreactor.fermentation_reaction.X = ethanol_yield / 100
        
        def set_glucose_yield(glucose_yield):
            glucose_yield *= 0.01
            X1 = self.pretreatment.glucan_to_glucose.X
            X1_side = self.pretreatment.glucose_to_byproducts.X.sum()
            X2_side = self.saccharification.saccharification.X[:2].sum()
            self.saccharification.saccharification.X[2] = X2 = (glucose_yield - X1) / (1 - X1_side)
            X_excess = (X2_side + X2) - 1
            if X_excess > 0: breakpoint()
                
        def set_xylose_yield(xylose_yield):
            xylose_yield *= 0.01
            X1_side = self.pretreatment.xylose_to_byproducts.X.sum()
            self.pretreatment.xylan_to_xylose.X = X1 = xylose_yield
            X_excess = (X1_side + X1) - 1
            if X_excess > 0.: breakpoint()
        
        @parameter(bounds=(85, 94), units='%', element='Pretreatment and saccharification')
        def set_cane_glucose_yield(cane_glucose_yield):
            if scenario.generation != 2: return
            set_glucose_yield(cane_glucose_yield)
                
        @parameter(bounds=(65, 92), units='%', element='Pretreatment and saccharification')
        def set_cane_xylose_yield(cane_xylose_yield):
            if scenario.generation != 2: return
            set_xylose_yield(cane_xylose_yield)
                
        @parameter(bounds=(90, 95), units='%', element='Cofermenation')
        def set_glucose_to_ethanol_yield(glucose_to_ethanol_yield):
            if scenario.generation != 2: return
            glucose_to_ethanol_yield *= 0.01
            split = self.seed_train_splitter.split.mean()
            X1 = split * self.seed_train.reactions.X[0]
            X2 = split * self.seed_train.reactions.X[2]
            X3 = (glucose_to_ethanol_yield - X1) / (1 - X1 - X2)
            X_excess = X3 * 1.0526 - 1
            if X_excess > 0.: breakpoint()
            self.cofermentation.cofermentation.X[0] = X3
            self.cofermentation.cofermentation.X[2] = X3 * 0.0526 # 95% towards ethanol, the other 5% goes towards cell mass

        @parameter(bounds=(66, 95), units='%', element='Cofermenation')
        def set_xylose_to_ethanol_yield(xylose_to_ethanol_yield):
            if scenario.generation != 2: return
            xylose_to_ethanol_yield *= 0.01
            split = self.seed_train_splitter.split.mean()
            X1 = split * self.seed_train.reactions.X[1]
            X2 = split * self.seed_train.reactions.X[3]
            X3 = (xylose_to_ethanol_yield - X1) / (1 - X1 - X2)
            X_excess = X3 * 1.0526 - 1
            if X_excess > 0.: breakpoint()
            self.cofermentation.cofermentation.X[1] = X3
            self.cofermentation.cofermentation.X[3] = X3 * 0.0526 # 95% towards ethanol, the other 5% goes towards cell mass
                
        @parameter(bounds=(68.5, 137), units='g/L', element='Cofermentation')
        def set_cofermentation_ethanol_titer(ethanol_titer):
            if scenario.generation != 2: return
            self.cofermentation.titer = ethanol_titer

        @parameter(bounds=(0.951, 1.902), units='g/L/h', element='Cofermentation')
        def set_cofermentation_ethanol_productivity(ethanol_productivity):
            if scenario.generation != 2: return
            self.cofermentation.productivity = ethanol_productivity
            
        # https://ifactoryapp.com/industries/steel-plant/steel-plant-annual-shutdown-planning-turnaround-management
        @parameter(bounds=(340, 360), units='day/y', baseline=350)
        def set_BFG_operating_days(BFG_operating_days):
            if scenario.feedstock != 'BFG': return
            self.tea.operating_days = BFG_operating_days
        
        @parameter(bounds=(340, 360), units='day/y', baseline=350)
        def set_RFG_operating_days(RFG_operating_days):
            if scenario.feedstock != 'RFG': return
            self.tea.operating_days = RFG_operating_days
        
        # https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/3_Volume3/19R_V3_Ch04_Metal_Industry.pdf
        # 5% of BFG is left unused at a steelmill. We can use this as both 
        # feedstock and fuel. We will need solve for the split and then resimulate.
        # https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2021.642162/full
        @parameter(bounds=BFG_available, units='10^6 MT/yr', element='BFG')
        def set_BFG_processing_capacity(BFG_processing_capacity):
            if scenario.feedstock != 'BFG': return
            current = self.feedstock.F_mass * self.tea.operating_hours / 1e9
            self.system.rescale(self.feedstock, BFG_processing_capacity / current)
            self._max_processing_capacity = self.feedstock.F_mass
        
        @parameter(bounds=RFG_available, units='10^6 MT/yr', baseline=RFG_available[0], element='RFG')
        def set_RFG_processing_capacity(RFG_processing_capacity):
            if scenario.feedstock != 'RFG': return
            current = self.feedstock.F_mass * self.tea.operating_hours / 1e9
            self.system.rescale(self.feedstock, RFG_processing_capacity / current)
            self._max_processing_capacity = self.feedstock.F_mass
        
        @metric(units='USD/MT')
        def carbon_mitigation_cost():
            # GWP_gasoline = 21.2 MJ (Energy in 1L Ethanol) × 93 g CO2e/MJ (Gasoline GWP) = 1.9716 kg CO2e / g CO2e
            ethanol_storage = self.ethanol_storage
            revenue = ethanol_storage._outlet_revenue
            ethanol_storage._outlet_revenue = 0
            target_price = MSP()
            actual_price = self.ethanol.price / ethanol_L_per_kg
            GWP_reduction = 1.9716 - self.carbon_intensity()
            ethanol_storage._outlet_revenue = revenue
            return (target_price - actual_price) / GWP_reduction * 1000
        
        @metric(units='kg*CO2e/L')
        def carbon_intensity(): # Energy allocation
            return self.system.get_product_impact(
                self.ethanol, GWPkey, allocation_method='energy'
            ) / ethanol_L_per_kg
        
        @metric(units='L-Water/L-EtOH')
        def water_usage(): # Energy allocation
            return self.system.get_product_impact(
                self.ethanol, 'WU', allocation_method='energy'
            ) / ethanol_L_per_kg
        
        @metric(units='%')
        def carbon_circularity_index():
            C_in = self.feedstock.get_atomic_flow('C')
            C_in += self.BT.fuel.get_atomic_flow('C')
            if self.scenario.feedstock == 'sugarcane':
                F_sugarcane = self.feedstock.F_mass / 1e3 # MT / hr
                GWP_sugarcane = self.sugarcane.characterization_factors['GWP'] # kg-CO2e / kg
                C_in += GWP_sugarcane * F_sugarcane / self.chemicals.CO2.MW
            ethanol = self.ethanol.copy()
            ethanol.imol['Octane'] = 0 # Remove denaturant
            C_out = ethanol.get_atomic_flow('C')
            return 100 * C_out / C_in
        
        @metric(units='%')
        def energy_circularity_index():
            ethanol = self.ethanol.copy()
            ethanol.imol['Octane'] = 0 # Do not count octane
            E_out = ethanol.HHV
            E_in = self.feedstock.HHV
            E_in += self.BT.fuel.HHV
            if isinstance(self.BT, bst.Boiler):
                water, steam, *_ = system.heat_utilities
                if 'steam' in water.ID: steam, water = water, steam
                cooling_electricity = 0.004542801314522282 * 18.015 # kWh / kmol
                E_in += water.flow * cooling_electricity * 3600 # Energy for cooling
            if scenario.hydrogen: 
                E_in += self.hydrogen.F_mass * self.hydrogen_energy_density / self.PEM_energy_efficiency * 3600
            net_electricity = self.system.power_utility.get_property('rate', 'kJ/hr')
            if net_electricity < 0: 
                E_out -= net_electricity # Net producing
            else:
                E_in += net_electricity
            if scenario.feedstock == 'sugarcane':
                # Add energy from farming/transportation inputs
                # Assume emissions all come from diesel
                # TODO: verify with GREET
                F_sugarcane = self.feedstock.F_mass / 1e3 # MT / hr
                HHV_diesel = 45500 # kJ / kg
                GWP_sugarcane = self.sugarcane.characterization_factors['GWP'] # kg-CO2e / kg
                GWP_diesel = 2.52
                diesel = F_sugarcane * GWP_sugarcane / GWP_diesel
                E_diesel = diesel * HHV_diesel
                E_in += E_diesel
            return 100 * E_out / E_in
        
        @metric(units='%')
        def carbon_energy_circularity_index():
            # Simple arithmetic mean; WBCSD (2020) aggregates circularity metrics using the same math.
            return (energy_circularity_index() + carbon_circularity_index()) / 2
        
        @metric(units='USD/L')
        def MSP():
            return self.tea.solve_price(self.ethanol) / ethanol_L_per_kg
        
        @metric(units='10^6 USD')
        def TCI():
            return self.tea.TCI / 1e6
        
        @metric(units='10^3 MT*CO2e/yr')
        def carbon_abated():
            GWP_reduction = 1.9716 - self.carbon_intensity()
            return self.ethanol.F_mass * self.tea.operating_hours * ethanol_L_per_kg * GWP_reduction / 1e6
        
        # @metric(units='USD/L')
        # def ethanol_credit():
        #     return self.carbon_credit / 1000 * GWP_reduction() # USD / L-ethanol
        
        # @metric(units='10^6 MT/yr')
        # def fuel_burned(): 
        #     return self.BT.fuel.F_mass * self.system.operating_hours / 1e9
        
        # @metric(units='10^6 MT/yr')
        # def hydrogen_consumption(): 
        #     return self.hydrogen.F_mass * self.system.operating_hours / 1e9 if scenario.hydrogen else 0
        
        # @metric(units='kWh/kg-H2')
        # def electricity_demand(): 
        #     return self.system.get_electricity_consumption() / (self.ethanol.F_mass * self.system.operating_hours)
        
        return model
    
    def create_mock_system(self):
        name = self.scenario.name
        all_units = bst.create_connected_grouped_units(self.unit_groups)
        units = all_units[1:-1] # Remove facilities and WWT
        
        def adjust_pretreatment_inlets():
            other = bst.Stream('water+')
            for i in pretreatment.ins:
                if i.isempty() or i.ID == 'dryer_air': 
                    continue
                elif i.ID == 'sugarcane':
                    sugarcane = i
                else:
                    other.mol += i.mol
            pretreatment.ins[:] = [sugarcane, other]
        
        def adjust_pretreatment_outlets():
            bagasse, humid_air, fiber_fines, filter_cake, juice = [i for i in pretreatment.outs if i.has_flow()]
            bagasse.mol += filter_cake.mol
            filter_cake.empty()
            water = humid_air.imol['Water']
            humid_air.empty()
            humid_air.imol['Water'] = water
            humid_air.ID = 'evaporated'
            pretreatment.outs[:] = [juice, bagasse, humid_air]
        
        def adjust_juiceferm_streams():
            other = bst.Stream('water+')
            for i in juiceferm.ins:
                if i.ID == 'juice': 
                    juice = i
                else:
                    other.mol += i.mol
            juiceferm.ins[:] = [juice, other]
            beer, *scrub_beer, wastewater, vent, yeast = juiceferm.outs
            wastewater.ID = '.wastewater'
            for i in scrub_beer:
                beer.mol += i.mol
                i.empty()
            juiceferm.outs[:] = [beer, vent, yeast, wastewater]
        
        def adjust_gasferm_streams():
            if self.scenario.feedstock == 'sugarcane':
                _, media, _, hydrogen, *other_hydrogen, vent = gasferm.ins
                for i in other_hydrogen:
                    hydrogen.mol += i.mol
                    i.empty()
                gasferm.ins[:] = [media, hydrogen, vent]
                
                # TODO: find out where this negligible stream `_whatsthis_` comes from 
                beer, _whatsthis_, wastewater, _, _, _, vent = gasferm.outs
                vent.mol[vent.mol < 0] = 0
                wastewater.ID = '.wastewater'
                gasferm.outs[:]= [vent, beer, wastewater]
            else:
                vent, hydrogen, media, _, stripping_water = gasferm.ins
                media.mol += stripping_water.mol
                stripping_water.empty()
                media.ID = '.water+'
                gasferm.ins[:] = [media, hydrogen, vent]
                beer, _, vent = gasferm.outs
                gasferm.outs[:] = [beer, vent]
                
            hydrogen.ID = '.H2'
            vent.ID = '.vent'
            return beer
            
        def adjust_EtOHsep_streams():
            EtOHsep.ins[:] = [i for i in EtOHsep.ins if i.imol['Ethanol']]
            ethanol, process_water, stillage = EtOHsep.outs
            stillage.ID = '.wastewater'
            
        match name:
            case 'BFG/H2':
                gasferm, EtOHsep = units
                adjust_gasferm_streams()
                adjust_EtOHsep_streams()
            case 'BFG/H2e':
                gasferm, EtOHsep = units
                adjust_gasferm_streams()
                adjust_EtOHsep_streams()
            case 'sugarcane':
                pretreatment, juiceferm, EtOHsep = units
                adjust_pretreatment_inlets()
                adjust_pretreatment_outlets()
                adjust_juiceferm_streams()
                adjust_EtOHsep_streams()
            case 'sugarcane/H2':
                pretreatment, juiceferm, gasferm, EtOHsep = units
                adjust_pretreatment_inlets()
                adjust_pretreatment_outlets()
                adjust_juiceferm_streams()
                adjust_gasferm_streams()
                adjust_EtOHsep_streams()
            case _:
                raise ValueError('')
        mocksys = bst.System.from_units('mocksys', units)
        return mocksys
    
    def ethanol_production(self):
        return self.ethanol.F_mass * self.tea.operating_hours * ethanol_L_per_kg / 1e6 # Million L/y Ethanol
    
    def ethanol_per_dollar_invested(self): # L / y-USD
        return self.ethanol_production() / self.TCI()
    
    @classmethod
    def simplified_integrated_sugarcane_diagram(cls):
        pm = cls(scenario='sugarcane/H2', simulate=True)
        bst.preferences.show_all_streams = False
        bst.preferences.stream_width = None
        for i in pm.system.streams:
            if i.isfeed() or i.isproduct(): continue
            i._ID = '      '
        for i in pm.system.units:
            i._ID = ''
        for i in pm.system.units: i.line = i.line.replace(' ', '\n')
        pm.system.diagram(layout='fdp', splines='ortho', overlap='true', ratio='0.5625', labelfontsize='18')
    
    def MSP_contributions(self):
        total_cost = self.MSP() * self.ethanol.F_mass * self.tea.operating_hours
        cost = self.tea.total_production_cost(self.ethanol)
        f = cost / total_cost
        return {
            'OPEX': f,
            'CAPEX': 1 - f,
        }
    
