# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 11:35:44 2023

@author: BRENDA
"""
import biosteam as bst
from biosteam.units.decorators import cost
from biosteam.units.design_tools.Gibbs_equilibrium_reaction import minimize_Gibbs_free_energy

__all__ = (
    # H2 + CO2 -> CO + H2O
    'ReverseWaterGasShiftReactor',
    # Carbon capture
    'CarbonCaptureCost',
    'MembraneSeparation',
    'CryogenicDistillation',
)

# %% H2 + CO2 -> CO + H2O

# TODO: Use detailed kinetic modeling, design, and cost correlations from paper
# https://www-sciencedirect-com.libproxy1.nus.edu.sg/science/article/pii/S0016236122003064

@cost('Feed flow rate', S=72.05e3, cost=5.2e6 * 1.12, CE=608, BM=3.02, n=0.6)
class ReverseWaterGasShiftReactor(bst.Unit):
    # https://www-sciencedirect-com.libproxy1.nus.edu.sg/science/article/pii/S0016236122003064
    _units = {'Feed flow rate': 'kg/hr'}
    _ins_size_is_fixed = False
    _outs_size_is_fixed = False
    _N_ins = 2
    _N_outs = 2
    auxiliary_unit_names = ('mixer', 'preheater', 'condenser')
    
    def _init(self):
        self.T = 800 + 273.15
        self.P = 5 * 101325
        self.reaction = bst.Reaction('CO2 + H2 -> CO + H2O', 'CO2', X=1)
        self.auxiliary('mixer', bst.Mixer, ins=(0-self, 1-self))
        self.auxiliary('preheater', bst.HXutility, ins=self.mixer-0, outs='', T=529.2 - 10) # TODO: Make this 400 degC, but use bagasse to avoid natural gas 
        self.auxiliary('valve', bst.IsenthalpicValve, P=2*101325)
        self.auxiliary('condenser', bst.Flash, ins=self.valve-0, outs=[self-0, self-1], T=273.15 + 37, P=2*101325)
    
    def _run(self):
        ins = self.ins
        if len(ins) == 3:
            CO2, H2, utility = self.ins
            self.external_utility = True
        else:
            CO2, H2, = self.ins
            self.external_utility = False
        F_H2 = CO2.imol['CO2'] - CO2.imol['H2']
        if F_H2 < 0: F_H2 = 0
        H2.imol['H2'] = F_H2 
        self.mixer.run()
        self.preheater.run()
        reactor_feed = self.preheater-0
        reactor_product = 0-self.valve
        reactor_product.copy_like(reactor_feed)
        reactor_product.T = self.T
        reactor_product.P = self.P
        minimize_Gibbs_free_energy(
            reactor_product, ('CO2', 'CO', 'H2', 'H2O'), 
            method='COBYLA', 
        )
        self.valve.run()
        self.condenser.run()
        if self.external_utility:
            _, _, emissions, remaining_utility = self.outs  
            self._furnace_heat_utility = hu = bst.HeatUtility()
            duty = (
                reactor_product.H + reactor_product.Hf
                - reactor_feed.H - reactor_feed.Hf
            )
            hu(duty, self.T, agent=utility.to_agent(isfuel=True))
            remaining_utility.copy_like(utility)
            remaining_utility.mol -= hu.inlet_utility_stream.mol
            emissions.copy_like(hu.outlet_utility_stream)
        
    def _design(self):
        self.design_results['Feed flow rate'] = sum([i.imass['CO2', 'H2'].sum() for i in self.ins])
        if self.external_utility:
            self.heat_utilities.append(self._furnace_heat_utility)
        else:
            reactor_feed = self.preheater-0
            reactor_product = 0-self.condenser
            duty = (
                reactor_product.H + reactor_product.Hf
                - reactor_feed.H - reactor_feed.Hf
            )
            self.add_heat_utility(duty, self.T)
        for i in self.auxiliary_units: i.simulate(run=False)

def test_reverse_water_gas_shift_reactor():
    bst.settings.set_thermo(['CO2', 'CO', 'H2', 'H2O'])
    RWGSH = ReverseWaterGasShiftReactor(
        ins=[bst.Stream('CO2', CO2=50, phase='g'),
             bst.Stream('H2', H2=50, phase='g')]
    )
    RWGSH.simulate()
    RWGSH.show()
    print(RWGSH.results())
    
        
# %% H2 recycling

@cost('H2 flow rate', S=32.52, cost=38.21e6, CE=596.2, n=0.6, kW=2.53 * 3600)
class CryogenicDistillation(bst.Splitter):
    # https://www.energy-proceedings.org/wp-content/uploads/2022/03/Ahmad-Naquash_ICAE2021_Revised_proceedings.pdf
    _units = {'H2 flow rate': 'kg/s'}
    
    def _init(self, split=None):
        if split is None: split = dict(H2=1)
        super()._init(split=split)
    
    def _setup(self):
        super()._setup()
        for i in self.outs: i.phase = 'g'
    
    def _design(self):
        self.design_results['H2 flow rate'] = self.outs[0].imass['H2'] / 3600

@cost('H2 flow rate', S=32.52, cost=34.36e6, CE=596.2, n=0.6, kW=0.88 * 3600)
class MembraneSeparation(bst.Splitter):
    # https://www.energy-proceedings.org/wp-content/uploads/2022/03/Ahmad-Naquash_ICAE2021_Revised_proceedings.pdf
    _units = {'H2 flow rate': 'kg/s'}
    
    def _init(self, split=None):
        if split is None: split = dict(H2=0.8991)
        super()._init(split=split)
    
    def _setup(self):
        super()._setup()
        for i in self.outs: i.phase = 'g'
    
    def _design(self):
        self.design_results['H2 flow rate'] = self.outs[0].imass['H2'] / 3600


# %% Carbon capture
        
class CarbonCaptureCost(bst.Facility):
    _N_ins = 1
    _N_outs = 2
    _ins_size_is_fixed = False
    network_priority = 2
    ticket_name = 'CC'
    
    def _init(self, m=-76.92307692307692, b=104.23076923076923):
        self.m = m
        self.b = b
        self.USD_per_MT = 100
        self.define_fee('Carbon capture', self.outs[0])

    @property
    def USD_per_MT(self):
        return -bst.settings.stream_prices['Carbon capture'] * 1000
        
    @USD_per_MT.setter 
    def USD_per_MT(self, USD_per_MT):
        bst.settings.register_fee('Carbon capture', -USD_per_MT / 1000)

    def _assert_compatible_property_package(self):
        pass

    def _run(self):
        CO2, other = self.outs
        other.mix_from(self.ins)
        CO2.imol['CO2'] = other.imol['CO2']
        other.imol['CO2'] = 0
    
    def _design(self): pass
    def _cost(self): 
        CO2, other = self.outs
        F_CO2 = CO2.imass['CO2']
        z_CO2 = F_CO2 / (other.F_mass + F_CO2)
        self.USD_per_MT = self.m * z_CO2 + self.b

if __name__ == '__main__':
    test_reverse_water_gas_shift_reactor()