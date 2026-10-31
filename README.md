# hero76 · Bias Bounty Mapping Equity Challenge

Final submission: EqBuune1, public RMSE 0.079801846. Fallback: ruvjs19G (constant 0.05), 0.089560921.

Read `reports/WRITEUP.md` (or the PDF). Section 9 has the commands; the last one rebuilds
`submissions/final/prediction.csv` and its sha256 should be
`7f02eee6cbc46ba257e86d2b309f2fc6bc970163b7cbfc0bab457f14137c2331`.

- `src/`: download and base features (tract, place, building and road aggregates)
- `src2/`: route-network roads, alternate-category facilities, model v2, fitting, checks, the discovery
- `submissions/`: every file that was uploaded, with probes and the blend
- `reports/discovery/`: Bias Discovery evidence tables and the named records
- `reports/scorecard/`: Zindi's bias scorecard for EqBuune1
- `reports/score_writeup.py`, `reports/jev-writeup-scores.json`: a documentation check of the writeup itself; not part of the model

Code is MIT. Challenge data and the derived tables in `reports/` and `submissions/` follow the challenge's CC-BY-SA 4.0 licence; Overture data © OpenStreetMap contributors and Overture Maps Foundation.

The challenge data is not stored here. `run-local.sh` downloads it from the public challenge bucket.
