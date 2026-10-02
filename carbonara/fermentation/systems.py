# -*- coding: utf-8 -*-
"""
"""
import biosteam as bst
from biorefineries import cane
from biorefineries.ethanol import create_ethanol_purification_system

__all__ = (
    'create_hydrogen_dilute_ethanol_system',
    'create_sugarcane_dilute_ethanol_system',
    'create_fluegas_hydrogen_ethanol_system',
    'create_sugarcane_ethanol_system',
    'create_sugarcane_hydrogen_ethanol_system',
)

# Price sources:
# https://catcost.chemcatbio.org/materials-library

# Unused price sources:
# https://www.chemanalyst.com/NewsAndDeals/NewsDetails/european-n-hexane-market-faces-price-decline-amid-downstream-sluggishness-25568
# https://www.chemanalyst.com/Pricing-data/ethyl-acetate-75

@bst.SystemFactory(
    ID='sugarcane_dilute_ethanol_sys', 
    ins=['sugarcane'], 
    outs=['vent', 'beer', 'bagasse', 'fiber_fines']
)
def create_sugarcane_dilute_ethanol_system(ins, outs, scrubber=True):
    sugarcane, = ins
    vent, beer, bagasse, fiber_fines = outs
    shredded_cane = bst.Stream()
    cane.create_feedstock_handling_system(
        area=100, ins=sugarcane, outs=shredded_cane, mockup=True,
    )
    juice = bst.Stream()
    cane.create_juicing_system(
        area=100,
        ins=shredded_cane,
        outs=[juice, bagasse, fiber_fines],
        pellet_bagasse=False,
        dry_bagasse=True,
        mockup=True
    )
    cane.create_sucrose_fermentation_system(
        area=200,
        ins=juice,
        outs=[beer, '', vent],
        scrubber=scrubber,
        mockup=True,
        add_urea=True,
    )
    
@bst.SystemFactory(
    ID='sugarcane_ethanol_sys', 
    ins=['sugarcane'], 
    outs=['ethanol']
)
def create_sugarcane_ethanol_system(ins, outs):
    ethanol, = outs
    sugarcane_to_EtOH_sys = create_sugarcane_dilute_ethanol_system(
        ins=ins, 
    )
    vent, beer, bagasse, fiber_fines = sugarcane_to_EtOH_sys.outs
    EtOH_sep_sys = create_ethanol_purification_system(
        ins=beer, 
        outs=(ethanol, 'stillage', 'process_water'),
        area=300,
    )
    bst.create_all_facilities(
        WWT_kwargs=dict(kind="high-rate", area=400), 
        HXN_kwargs=dict(force_ideal_thermo=True, cache_network=True),
        CHP_kwargs=dict(fuel_source='Biomass'),
    )

@bst.SystemFactory(
    ID='hydrogen_dilute_ethanol_sys',
    ins=[dict(ID='carbon_source', phase='g'), 
         dict(ID='hydrogen', H2=100, P=101325e1, price=2, phase='g')],
    outs=['vent', 'beer'],
)
def create_hydrogen_dilute_ethanol_system(
        ins, outs, 
    ):
    carbon_source, H2, = ins
    vent, beer = outs
    media = bst.Stream(Water=1000, T=298.15)
    H2.register_alias('hydrogen')
    watergas_shift = bst.Rxn(
        'CO + H2O -> CO2 + H2',
        reactant='CO', correct_atomic_balance=True, X=1
    )
    production = bst.Rxn(
        'H2 + CO2 -> Ethanol + H2O',
        reactant='CO2', correct_atomic_balance=True, X=1
    )
    growth = bst.Rxn(
        'H2 + CO2 -> Bacteria + H2O', reactant='CO2',
        X=1, correct_atomic_balance=True
    )
    recycled_cellmass = bst.Stream()
    gas_fed_bioreactor = bst.GasFedBioreactor(
        ins=[media, carbon_source, H2, recycled_cellmass], 
        outs=(vent, 'effluent'), 
        tau=100, 
        funneling_reactions=watergas_shift,
        reactions=bst.SeriesReaction([production, growth]), 
        gas_substrates=('H2', 'CO2', 'CO'),
        titer={'Ethanol': 20},
        batch=False,
        length_to_diameter=12,
        V_max=3785,
        theta=0.5,
        kW_per_m3=0.,
        design='bubble column',
        controlled_feeds=[0, 2],
        T=37 + 273.15,
    )
    for i in gas_fed_bioreactor.gas_coolers: i.cool_only = True
    gas_fed_bioreactor.productivity = 1 # g / L / h
    gas_fed_bioreactor.specific_yield = 20 # g-product / g-biomass
    
    # Stoichiometric molar production per mol CO2
    EtOH_per_CO2 = (
        production.istoichiometry['Ethanol']
        / -production.istoichiometry['CO2']
    )
    DCW_per_CO2 = (
        growth.istoichiometry['Bacteria']
        / -growth.istoichiometry['CO2']
    )
    # g produced per mol CO2 consumed
    m_EtOH = EtOH_per_CO2 * gas_fed_bioreactor.chemicals.Ethanol.MW
    m_DCW = DCW_per_CO2 * gas_fed_bioreactor.chemicals.Bacteria.MW
    
    def update_theoretical_yield():
        Y_PX = gas_fed_bioreactor.specific_yield
        gas_fed_bioreactor.reactions.X[0] = Y_PX * m_DCW / (m_EtOH + Y_PX * m_DCW) # Y_PX = X * m_EtOH / [(1 - X) * m_DWC]
    
    @gas_fed_bioreactor.add_specification(run=False)
    def adjust_fermentation_performance():
        productivity = gas_fed_bioreactor.productivity
        gas_fed_bioreactor.tau = gas_fed_bioreactor.titer['Ethanol'] / productivity
        update_theoretical_yield()
        gas_fed_bioreactor.run()
        error = gas_fed_bioreactor.atomic_balance_error()
        assert sum(error.values()) < 1e-3
    
    gas_fed_bioreactor.update_theoretical_yield = update_theoretical_yield
    
    cellmass_centrifuge = bst.SolidsCentrifuge(
        ins=gas_fed_bioreactor-1, 
        outs=(recycled_cellmass, beer),
        split=dict(Bacteria=0.9),
        solids=('Bacteria',),
        moisture_content=0.6,
        strict_moisture_content=False,
    )
    
@bst.SystemFactory(
    ID='fluegas_hydrogen_ethanol_sys',
    ins=[dict(ID='carbon_source', phase='g'), 
         dict(ID='hydrogen', H2=100, P=101325e1, price=2, phase='g')],
    outs=['ethanol', 'purge'],
)
def create_fluegas_hydrogen_ethanol_system(
        ins, outs, 
    ):
    carbon_source, hydrogen = ins
    ethanol, purge = outs
    vent = bst.Stream(phase='g')
    recycled_vent = bst.Stream(phase='g')
    bst.Splitter(
        (100, 'vent_splitter'),
        ins=vent, outs=[recycled_vent, purge], split=0.9
    )
    vent_mixer = bst.Mixer(
        (100, 'vent_recirculation_mixer'),
        ins=[carbon_source, recycled_vent],
    )
    H2_to_EtOH_sys, udct = create_hydrogen_dilute_ethanol_system(
        ins=[vent_mixer-0, hydrogen], 
        outs=['vent', 'beer'],
        area=100, udct=True
    )
    gas_fed_bioreactor = udct['gas_fed_bioreactor']
    cellmass_centrifuge = udct['cellmass_centrifuge']
    stripping_water = bst.Stream()
    vent_scrubber = bst.VentScrubber(
        (100, 'vent_scrubber'), 
        ins=(stripping_water, gas_fed_bioreactor-0), 
        outs=(vent, ''),
        titer=('Ethanol', 5), # g / L 
    )
    dilute_ethanol_mixer = bst.Mixer(
        (100, 'dilute_ethanol_mixer'), 
        ins=(cellmass_centrifuge-1, vent_scrubber-1)
    )
    EtOH_sep_sys = create_ethanol_purification_system(
        ins=dilute_ethanol_mixer-0, 
        outs=(ethanol, 'stillage', 'process_water'),
        area=200,
    )
    bst.create_all_facilities(
        WWT_kwargs=dict(kind="high-rate", area=300), 
        HXN_kwargs=dict(force_ideal_thermo=True, cache_network=True),
        CHP_kwargs=dict(fuel_source='Biomass'),
    )
    
@bst.SystemFactory(
    ID='sugarcane_hydrogen_ethanol_sys',
    ins=['sugarcane', 
         dict(ID='hydrogen', H2=100, P=101325e1, price=2, phase='g')],
    outs=['ethanol'],
)
def create_sugarcane_hydrogen_ethanol_system(
        ins, outs, 
    ):
    sugarcane, hydrogen = ins
    ethanol, = outs
    sugarcane_sys = create_sugarcane_dilute_ethanol_system(
        ins=sugarcane, scrubber=True
    )
    bioreactor_vent, beer, bagasse, fiber_fines = sugarcane_sys.outs
    recycled_vent = bst.Stream(phase='g')
    vent_mixer = bst.Mixer(
        (300, 'vent_recirculation_mixer'),
        ins=[bioreactor_vent, recycled_vent],
    )
    H2_to_EtOH_sys, udct = create_hydrogen_dilute_ethanol_system(
        ins=[vent_mixer-0, hydrogen], 
        outs=[recycled_vent, 'beer'],
        area=300, udct=True
    )
    dilute_ethanol_mixer = bst.Mixer(
        400, ins=[beer, H2_to_EtOH_sys-1],
    )
    EtOH_sep_sys = create_ethanol_purification_system(
        ins=dilute_ethanol_mixer-0, 
        outs=(ethanol, 'stillage', 'process_water'),
        area=400,
    )
    bst.create_all_facilities(
        WWT_kwargs=dict(kind="high-rate", area=500), 
        HXN_kwargs=dict(force_ideal_thermo=True, cache_network=True),
        CHP_kwargs=dict(fuel_source='Biomass'),
    )
    
