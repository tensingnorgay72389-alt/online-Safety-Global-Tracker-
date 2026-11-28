from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_signal_page_groups_countries_from_the_recorded_signals():
    script = ROOT / "dashboard" / "scripts" / "signal-view.test.ts"
    completed = subprocess.run(
        ["node", "--experimental-strip-types", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert '"countriesWithRecent": 25' in completed.stdout
    assert '"summaryOnlyCountries": 13' in completed.stdout
    assert '"undatedSignals": 0' in completed.stdout
    assert '"asOf": "2026-11-28"' in completed.stdout
    assert '"windowStart": "2026-08-28"' in completed.stdout
