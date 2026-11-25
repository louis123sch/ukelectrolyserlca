"""
Assets that outlive the data centre: Terlouw's sell-off at year 25.
=============================================================================

The data centre runs for ``dc_config.DC_OPERATION_YEARS`` (25). Three assets
outlive it: onshore wind (35 y), solar (38 y; their step-up transformers are
inside both prices) and the grid connection (40 y). Until 25 Nov 2026 each was
repaid over its own life, which quietly counts its unused years at their share.

Now, following the outlives-the-project branch of Terlouw et al.'s OPTIMES
(2025, Applied Energy 377; ``opt_lca_functions.rep_annual_int``), each is

1. repaid over the data centre's 25 years, and
2. sold at year 25 for ``RESALE_SHARE`` (Terlouw's 75 %) of its remaining
   straight-line value, (L - 25) / L of its build cost,
3. that sale discounted to today at the asset's own rate.

Per £ of build cost, at rate r and life L > 25:

    factor = CRF(r, 25) x (1 - share x (L - 25) / L x (1 + r)^-25)

which takes the place of CRF(r, L). It is Terlouw's
``CRF(r, lt) + rep_annual_int(1, lt, r, L)`` with ``lt`` = 25, exactly
(``tests/test_sell_off.py`` runs his function beside it). An asset whose life
is 25 years or less is not touched: the function hands back the caller's own
CRF, so batteries, stacks, fuel cells, the electrolyser, the tank and the gas
engines, and their replacements, are exactly as before.

Cost only. Carbon stays spread over each asset's own life, as in Terlouw et al.

The setting: ``dc_config.SELL_OFF`` (on) and ``RESALE_SHARE`` (0.75), which a
run can override through ``dc_inputs.build_tech(sell_off=, resale_share=)``.
``build_tech`` holds them in a context (``setting``) while it builds, so the
two cost modules (``tech_costs``, ``connection_cost``) read them without new
arguments threaded through every caller. Every number is recorded with
``trace.cost``, so the cost map, the explainer and the cost workbook show it,
and a push on ``cost.sell_off.resale_share`` moves all three assets at once.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager

import dc_config as cfg
from optimisation import trace as T

SOURCE_KEY = "terlouw_2025_optimes"
PROJECT_KEY = "cost.sell_off.project_years"
SHARE_KEY = "cost.sell_off.resale_share"

_SETTING: contextvars.ContextVar[tuple] = contextvars.ContextVar("sell_off_setting", default=(None, None))


def _check_share(share) -> None:
    if share is not None and not (0.0 <= float(share) <= 2.0):
        raise ValueError(f"resale_share must be between 0 and 2, got {share!r}")


@contextmanager
def setting(sell_off: bool | None = None, resale_share: float | None = None):
    """Hold a run's sell-off setting while its coefficients are built. None keeps
    ``dc_config``'s."""
    _check_share(resale_share)
    token = _SETTING.set((sell_off, resale_share))
    try:
        yield
    finally:
        _SETTING.reset(token)


def active() -> tuple[bool, float]:
    """(sell-off on, resale share) in force now."""
    on, share = _SETTING.get()
    return (bool(cfg.SELL_OFF) if on is None else bool(on),
            float(cfg.RESALE_SHARE) if share is None else float(share))


def labels() -> dict:
    """The setting as a run records it."""
    on, share = active()
    return {"sell_off": on, "resale_share": share if on else None,
            "sell_off_project_years": float(cfg.DC_OPERATION_YEARS) if on else None}


def capital_recovery_factor(rate, lifetime_years):
    """The yearly repayment of £1 over ``lifetime_years`` at ``rate``."""
    rate, n = float(rate), float(lifetime_years)
    if n <= 0:
        raise ValueError("lifetime_years must be positive")
    return 1.0 / n if rate == 0 else rate * (1.0 + rate) ** n / ((1.0 + rate) ** n - 1.0)


def sell_off_factor(rate, life_years, project_years, resale_share):
    """Plain twin of ``repayment`` (no trace): yearly charge per £ of build cost."""
    rate, life, h = float(rate), float(life_years), float(project_years)
    if life <= h:
        return capital_recovery_factor(rate, life)
    return capital_recovery_factor(rate, h) * (1.0 - resale_share * (life - h) / life * (1.0 + rate) ** -h)


def repayment(prefix: str, rate: float, life_years: float, own_crf: float, own_key: str,
              rate_key: str, life_key: str, what: str) -> tuple[float, str]:
    """The yearly charge per £ of build cost for one asset, and the trace key it sits under.

    ``own_crf`` / ``own_key`` are the caller's repayment over the asset's own life,
    recorded already; they come straight back when the sell-off is off or the asset
    does not outlive the data centre, so nothing else moves and nothing new is
    recorded. Otherwise the steps below are recorded under ``prefix``."""
    on, share = active()
    project = float(cfg.DC_OPERATION_YEARS)
    if not on or float(life_years) <= project:
        return own_crf, own_key
    project = T.cost(PROJECT_KEY, project, "years",
                     "The data centre's life: the years every asset that outlives it is repaid over",
                     grade="assumed",
                     note="dc_config.DC_OPERATION_YEARS, the facility inventory's 25-year operating life "
                          "(optimiser_lca/data_centre.py, Zhang et al.), the life its own carbon is charged over")
    share = T.cost(SHARE_KEY, share, "fraction of remaining value",
                   "Resale share: what an asset left over at the data centre's end sells for, as a share "
                   "of its remaining straight-line value", grade="transcribed",
                   cites=[(SOURCE_KEY, "opt_lca_functions.py, rep_annual_int: rep_factor = 0.75, applied to "
                                       "the residual value of a component that outlives the project")],
                   note="Terlouw et al.'s own assumption, with no source given; tested at x0.5 and x1.5")
    crf_h = T.cost(f"{prefix}.sell_off.crf_project", capital_recovery_factor(rate, project), "per year",
                   f"{what}: capital recovery factor over the data centre's life",
                   uses=[rate_key, PROJECT_KEY])
    left = T.cost(f"{prefix}.sell_off.share_left", (life_years - project) / life_years,
                  "fraction of build cost", f"{what}: share of its life left when the data centre closes",
                  uses=[life_key, PROJECT_KEY])
    disc = T.cost(f"{prefix}.sell_off.discount_to_end", (1.0 + rate) ** -project, "multiplier",
                  f"{what}: £1 at the data centre's end, in today's money", uses=[rate_key, PROJECT_KEY])
    key = f"{prefix}.sell_off.factor"
    factor = T.cost(key, crf_h * (1.0 - share * left * disc), "per year",
                    f"{what}: yearly charge per £ of build cost, repaid over the data centre's life less the "
                    "discounted sale at its end (Terlouw et al. 2025)",
                    uses=[f"{prefix}.sell_off.crf_project", SHARE_KEY, f"{prefix}.sell_off.share_left",
                          f"{prefix}.sell_off.discount_to_end"],
                    note=f"In place of {own_key}, the repayment over its own life")
    return factor, key
