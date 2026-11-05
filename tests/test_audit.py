"""The consistency audit has to run.

Since the connection became the optimiser's choice (30 Oct 2026) the default mode
stops on a site with no room nearby. The audit's own site, 360 MW in the Highlands,
is one, so `python optimisation/audit.py` stopped at its first line for a week with
nothing to say so. It now uses the one list the published rule gives.
"""
from __future__ import annotations

import pytest

from optimisation import audit


@pytest.fixture
def highland():
    from optimisation import sites as S
    return S.resolve(57.48, -4.22, transmission_connected=True)


def test_the_audits_site_checks_get_past_the_connection(highland):
    audit.FINDINGS.clear()
    audit.check_applicability(highland, "2025-01-01", "2025-02-01")
    audit.check_geography(highland, "2025-01-01", "2025-02-01")
    assert [f.what for f in audit.FINDINGS if f.severity == "error"] == []


def test_the_audits_scale_check_gets_past_the_connection():
    table = audit.check_scale_response("57.48,-4.22", "2025-01-01", "2025-02-01")
    assert len(table) == 3
