> Public result observed23October2026: RMSE **0.140188939**, submission **uG9arWJm**. Provisional estimate; no private score or prize result.

# demographic peer-shortfall candidate

**Provisional, publicly scored.** The observed public RMSE is recorded above; final private error remains unknown.

Uses only supplied Overture building bbox centres, clipped all-road geodesic lengths, POI counts and supplied population/land area/urban share. Never uses removed references, reference-derived building counts or sample labels.

Within each region, take up to32 other positive-population tracts nearest in standardized log(1+population), log(1+land km²), urban fraction and urban-missing indicator. Geography is limited to region membership; peers need not be nearby.

For each of three observed quantities, expected count/length is the peer25th percentile. Proxy shortfall=max(0,1-observed/expected) where expected>0. Average defined proxy shortfalls equally. Undefined proxies are omitted; if none exist, or population=0, use the zero-baseline fallback. This does not reproduce organiser-defined flags/components.

The lower quartile is a conservative prior choice, not tuned against leaderboard scores. No supervised fit is possible without labels. Counts measure both true supply and mapping intensity; their effects cannot be separated here. Some complete maps may receive high scores. Proximity does not measure emergency travel time.

Diagnostics include peer expectations, counts, distance and low-evidence flags. Sensitivity and synthetic county-held-out tests are in reports/. Synthetic omission detection is not target-gap validation. Building assignment is approximate and its diagnostic sample is recorded separately.

SHA256: 18cd9ec4982efd1d6454822fb64bed770ede55854a58974165ae9adb929d4970
