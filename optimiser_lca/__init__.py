"""
optimiser_lca — the LCA side of the Data Centre Optimiser.
=============================================================================

One module per inventory, each readable top to bottom on its own, in the shape
``common`` defines and docs/LCA_STYLE.md writes down (docstring with source and
functional unit, graded parameters, scope dict, check(), processes, flows,
activities, inventory()):

    upv                   Smith et al. 2024 utility PV, rescored on apos; the
                          IEA PVPS 2026 fixed-tilt mounting
    gb_grid               the study's own GB grid kWh (optimiser_lca.grid is the
                          basis: sources per API fuel, losses, delivery)
    hydrogen              Hermesmann & Müller 2022 fossil routes; Gerloff 2021
                          AE / PEM / SOEC electrolysers
    data_centre           Zhang et al. 2025 hyperscale facility
    fuel_cell             Babatunde et al. 2024 stack, Usai 2021 balance of
                          plant, the per-kWh operation
    bess                  Jasper et al. 2026 liquid-cooled container, Voß et al.
                          2025 LFP cell
    h2_tank               Gandiglio et al. 2022 steel vessel
    stepup_transformers   Leng et al. 2026 wind step-ups and grid intake, IEA
                          PVPS 2026 solar step-ups, Jasper's container unit
    exclusions            the cut-off register: every flow left out, with its
                          upper estimate, tested by optimisation/cutoff.py

``common`` supplies the shape and the verbs (``check``, ``show``, ``pin``,
``resolve``, ``to_bw_dict``, ``write``); ``registry`` holds every database name
and activity code; ``build`` writes the databases; ``validate`` reproduces the
papers.

    python -m optimiser_lca.build        # (re)write every foreground database
    python -m optimiser_lca.validate     # reproduce the papers' published results
"""
