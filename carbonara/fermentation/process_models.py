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
    'ricestraw': {},
}

class PlatformBioproductProcess(bst.ProcessModel):
    """
    Examples
    --------
    >>> from biorefineries.gas_fermentation import Biorefinery
    >>> pm = PlatformBioproductProcess(simulate=False, scenario='glucose growth')
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
        
        # https://tradingeconomics.com/commodity/sugar
        @parameter(units='USD/kg', element=scenario.feedstock,
                   **price_data[scenario.feedstock]) 
        def set_feedstock_price(price): # https://scijournals.onlinelibrary.wiley.com/doi/epdf/10.1002/bbb.1976?saml_referrer
            if scenario.glucose_growth:
                self.seedtrain_feed.price = price * 0.12
            if scenario.carbon_source == 'glucose':
                self.feedstock.price = price * 0.10
        
        @parameter(units='USD/kg', element=scenario.product, 
                   **price_data[scenario.product]) # https://www.alibaba.com/product-detail/Factory-direct-sale-DODECYL-ACETATE-CAS_1601041319372.html
        def set_product_price(price):
            self.product.price = price
        
        # https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/20004-cost-electrolytic-hydrogen-production.pdf?Status=Master
        # Actual cost of hydrogen between 4-6 USD/kg according to DOE
        @parameter(units='USD/kg', element='H2', bounds=[2, 6],
                   baseline=3, distribution='uniform') # Natural gas 1.5 - 5; Electrolysis 3 - 7
        def set_H2_price(price):
            if scenario.carbon_source == 'glucose': return
            self.hydrogen.price = price
        
        @parameter(units='g/L', element='AcOH production',
                   bounds=[40, 90], baseline=60, distribution='uniform')
        def set_titer(titer):
            if scenario.carbon_source == 'glucose': return
            self.gas_fed_bioreactor.titer['AceticAcid'] = titer
        
        @parameter(units='g/L/h', element='AcOH production',
                   bounds=[1, 2], baseline=1.5, distribution='uniform')
        def set_productivity(productivity):
            if scenario.carbon_source == 'glucose': return
            self.gas_fed_bioreactor.productivity = productivity
        
        @parameter(units='g_{' + scenario.product + '}/g_{cell}', element='Oleochemical production', 
                   bounds=[0.45, 2.7], baseline=1.57, distribution='uniform')
        def set_yield(product_yield):
            self.gas_fed_bioreactor.product_yield = product_yield
        
        # https://www.eia.gov/energyexplained/natural-gas/prices.php
        # @parameter(distribution=dist.natural_gas_price_distribution, element='Natural gas', units='USD/m3',
        #            baseline=4.73 * 35.3146667/1e3)
        # def set_natural_gas_price(price): 
        #     self.BT.natural_gas_price = price * V_ng
    
        # @parameter(distribution=dist.electricity_price_distribution, units='USD/kWh',
        #            element='electricity', baseline=dist.mean_electricity_price)
        # def set_electricity_price(price): 
        #     bst.settings.electricity_price = price
        
        # https://pmc.ncbi.nlm.nih.gov/articles/PMC3947793/
        # https://www.capturemap.no/the-biogenic-co2-breakdown/
        self.BT.CO2_emissions_concentration = 15.0 / 100 # 
        
        if scenario.carbon_source == 'biomass':
            @parameter(units='MT/yr', element='oleochemical', bounds=[20000, 50000], baseline=35000)
            def set_production_capacity(production_capacity):
                self.production_capacity = production_capacity
                
            # @uniform(units='USD/MT', element='Carbon capture', baseline=100) 
            # def set_carbon_capture_cost(price):
            #     self.CC.b = 4.230769230769226 + price
            
            # @parameter(
            #     units='wt %', element='Boiler flue gas', 
            #     distribution=shape.Trunc(shape.Normal(6.3 * 1.55, 0.5 * 1.55), 5.3 * 1.55, 7.3 * 1.55), 
            #     baseline=6.3 * 1.55, 
            #     bounds=(5.3 * 1.55, 7.3 * 1.55)
            # ) 
            # def set_boiler_flue_gas_CO2_content(CO2_content):
            #     self.BT.CO2_emissions_concentration = CO2_content / 100
            
            @system.add_specification(simulate=True)
            def adjust_production_capacity():
                capacity = self.production_capacity / system.operating_hours * 1000 # kg / hr
                self.system.simulate()
                self.system.rescale(self.AcOH_media, capacity / self.product.F_mass) 
        elif scenario.carbon_source == 'BFG':
            total_pig_iron_produced_US = 22.3e6 # MT / yr
            N_facilities_US = 12
            BFG_per_ton_pig_iron = 2.5 # Blast furnace gas (2.5 to 3.5 BFG / steel by wt)
            pig_iron_per_facility = total_pig_iron_produced_US / N_facilities_US # MT / yr
            BFG_per_facility = pig_iron_per_facility * BFG_per_ton_pig_iron  
            
            @parameter(units='MT/yr', element='Flue gas',
                       bounds=[BFG_per_facility / 30, BFG_per_facility / 15]) # Only a fraction is used to prevent TCI > 1 billion
            def set_flue_gas_processing_capacity(processing_capacity):
                self.flue_gas.imass[scenario.carbon_source] = processing_capacity / system.operating_hours * 1000 # kg / hr
        else:
            # Must be glucose, but no uncertainty is accounted for at this level
            pass
            
        if scenario.carbon_capture:
            baseline_length_to_diameter = 8
        else:
            baseline_length_to_diameter = 12
        
        optimized_parameter = model.optimized_parameter
        
        @optimized_parameter(bounds=[2, 12], baseline=baseline_length_to_diameter, element='AcOH bioreactor', name='length to diameter')
        def set_AcOH_bioreactor_length_to_diameter(length_to_diameter):
            if scenario.carbon_source == 'glucose': return
            self.AcOH_production.length_to_diameter = length_to_diameter
        
        @optimized_parameter(bounds=[2, 12], baseline=baseline_length_to_diameter, element='oleochemical bioreactor', name='length to diameter')
        def set_oleochemical_bioreactor_length_to_diameter(length_to_diameter):
            self.oleochemical_production.length_to_diameter = length_to_diameter
        
        @optimized_parameter(bounds=[0.2, 0.6], baseline=0.5, element='oleochemical bioreactor', name='agitation power')
        def set_oleochemical_bioreactor_agitation_power(kW_per_m3):
            self.oleochemical_production.kW_per_m3 = kW_per_m3
        
        if not scenario.dewatering: self.ethyl_acetate = bst.MockStream('ethyl_acetate')
        
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
        key = scenario.biomass
        try:
            self.BT.fuel.set_CF(GWPkey, CFs[key.capitalize()])
        except:
            breakpoint()
        if key == 'miscanthus':
            price_ub = 59 / 907.185 * 0.8 # https://www.sciencedirect.com/science/article/pii/S096195340700205X
            price_lb = 61.98 / 907.185 * 0.8 # https://farmdoc.illinois.edu/fast-tools/biomass-crop-budget-tool-miscanthus-and-switchgrass
        elif key == 'cornstover':
            price_lb = 59 / 907.185 * 0.8 # Humbird NREL 2011 cellulosic ethanol
            price_ub = 64.96 / 907.185 * 0.8 # https://www.extension.purdue.edu/extmedia/ec/re-3-w.pdf
        else:
            raise ValueError('invalid carbon source')
        self.BT.fuel.price = price_baseline = 0.5 * (price_lb + price_ub)
        
        @parameter(units='USD/MT', element='biomass', 
                   bounds=[price_lb * 1000, price_ub * 1000], 
                   baseline=price_baseline * 1000)
        def set_biomass_price(price):
            self.BT.fuel.price = price / 1000
        
        # bst.settings.electricity_price = 0.060 # Maryland solar REC (renewable energy certificates) # https://escholarship.org/uc/item/80n4q8xc
        if scenario.carbon_source != 'glucose':
            self.hydrogen.set_CF(GWPkey, CFs['H2'])
        self.hexane.set_CF(GWPkey, CFs['Hexane'])
        self.ethyl_acetate.set_CF(GWPkey, CFs['Ethyl acetate'])
        
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
            if scenario.carbon_source == 'glucose': return 0
            return self.hydrogen.F_mass * self.system.operating_hours / 1e6
        
        @metric(units='10^3 MT/yr')
        def glucose_consumption(): 
            if scenario.carbon_source == 'glucose':
                glucose = self.feedstock.imass['Glucose'] + self.seedtrain_feed.imass['Glucose']
            elif scenario.glucose_growth:
                glucose = self.seedtrain_feed.imass['Glucose']
            else:
                return 0
            return glucose * self.system.operating_hours / 1e6
        
        @metric(units='kWh/kg-H2')
        def electricity_demand(): 
            return self.system.get_electricity_consumption() / (self.product.F_mass * self.system.operating_hours)
        
        if scenario.carbon_source != 'biomass':
            @metric(units='10^3 MT/yr', element='oleochemical')
            def production_capacity():
                return self.system.get_mass_flow(self.product) / 1e6
        
        return model
    
    def MSP_contributions(self):
        total_cost = self.MSP() * self.product.F_mass * self.tea.operating_hours
        cost = self.tea.total_production_cost(self.product)
        f = cost / total_cost
        return {
            'OPEX': f,
            'CAPEX': 1 - f,
        }
    
    def to_experimental_conditions(self):
        if 'acetate' in self.scenario.name:
            # -Titer = 600 mg/L alcohols (dodecanol)
            # -Yield = 0.11 g alcohols (dodecanol) / g acetate (0.265 max)
            # -Specific yield = 0.49 g alcohols / g biomass
            # -Productivity = 0.01 g alcohols / L / h, or 0.008 g alcohols / gDCW/h
            self.set_oleochemical_titer.setter(0.6)
            self.set_oleochemical_bioreactor_yield.setter(42)
            self.set_oleochemical_specific_yield.setter(0.49)
            self.set_oleochemical_productivity.setter(0.01)
            self.system.simulate()
        elif self.scenario.name == 'glucose':
            # -Titer = 1,551 mg/L
            # -Yield = 0.126 g alcohols / g glucose (0.32 max)
            # -Specific yield = 1.5 g alcohol / gDCW
            # -Productivity = 0.016 g alcohol / gDCW / h 
            self.set_oleochemical_titer.setter(1.55)
            self.set_oleochemical_bioreactor_yield.setter(39)
            self.set_oleochemical_specific_yield.setter(1.5)
            self.set_oleochemical_productivity.setter(0.016)
            self.system.simulate()
        else:
            raise NotImplementedError(f'experimental conditions for scenario {self.scenario.name!r}')
    
    def H2_price_breakeven_configurations(self):
        if self.scenario.glucose_growth:
            br_glucose = self
            if hasattr(self, 'acetate_growth_biorefinery'):
                br_acetate = self.acetate_growth_biorefinery
            else:
                self.acetate_growth_biorefinery = br_acetate = type(self)(scenario=self.scenario, glucose_growth=False)
        else:
            br_acetate = self
            if hasattr(self, 'glucose_growth_biorefinery'):
                br_glucose = self.glucose_growth_biorefinery
            else:
                self.glucose_growth_biorefinery = br_glucose = type(self)(scenario=self.scenario, glucose_growth=True)
        
        H2 = br_acetate.hydrogen.F_mass
        product = br_acetate.product.F_mass
        contribution = H2 / product
        original_price = br_acetate.hydrogen.price
        br_acetate.hydrogen.price = 0
        MSP_acetate = br_acetate.MSP()
        br_acetate.hydrogen.price = original_price
        MSP_glucose = br_glucose.MSP()
        return (MSP_glucose - MSP_acetate) / contribution
    
    def MSP_CI_vs_specific_yield(self):
        specific_yields = [0.7, 1.0, 1.5, 2.0, 2.5, 3, 3.5]
        CIs = []
        MSPs = []
        for specific_yield in specific_yields:
            self.oleochemical_production.specific_yield = specific_yield
            self.system.simulate()
            CIs.append(self.carbon_intensity())
            MSPs.append(self.MSP())
        return CIs, MSPs
    
    def MSP_CI_vs_H2_over_C(self):
        H2_over_Cs = [1.0, 1.5, 2.0]
        CIs = []
        MSPs = []
        CC = []
        for H2_over_C in H2_over_Cs:
            self.AcOH_production.H2_over_C = H2_over_C
            self.system.simulate()
            CIs.append(self.carbon_intensity())
            MSPs.append(self.MSP())
            CC.append(self.credited_carbon_intake())
        return CIs, MSPs, CC
