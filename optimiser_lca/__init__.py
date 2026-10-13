"""
optimiser_lca — the LCA side of the Data Centre Optimiser.
=============================================================================

One module per inventory, each readable top to bottom on its own:

    grid                  GB grid carbon: the ecoinvent source per API fuel,
                          losses, composite splits, the closed-form score, and
                          the network delivery terms
    hydrogen              Hermesmann: SMR, SMR-CCS, CCS, MP-E, AE/PEM/SOEC
    data_centre           Zhang et al. 2025 hyperscale facility
    fuel_cell             Babatunde et al. 2024 stack + the per-kWh operation
    h2_tank               Gandiglio et al. 2022 steel vessel
    stepup_transformers   Leng et al. 2026 wind, IEA PVPS 2026 solar
    upv                   Smith et al. 2024 utility PV, rescored on apos

Every inventory module has the same four sections, in this order: source and
scope (the docstring), parameters, processes, activities. ``common`` supplies
the verbs — ``show``, ``pin``, ``resolve``, ``to_bw_dict`` — and ``registry``
holds every database name and activity code. ``build`` writes the databases;
``validate`` reproduces the papers.

    python -m optimiser_lca.build        # (re)write every foreground database
    python -m optimiser_lca.validate     # check the fuel cell against its paper
"""
