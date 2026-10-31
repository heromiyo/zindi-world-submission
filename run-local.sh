#!/usr/bin/env bash
# Full rebuild of submissions/final/prediction.csv (EqBuune1). Needs network access to the public challenge bucket.
set -euo pipefail
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python src/download.py
.venv/bin/python src/extract_features.py
.venv/bin/python src/extract_network.py
for r in eastern-ok maricopa-az northern-ca south-central-tx; do
  .venv/bin/python src2/road_classes.py $r
  .venv/bin/python src2/routes.py $r
done
for r in eastern-ok maricopa-az northern-ca south-central-tx eastern-wa; do .venv/bin/python src2/poi_alt.py $r; done
.venv/bin/python src2/features.py
.venv/bin/python src2/structural.py
.venv/bin/python src2/make_probes_and_blend.py
src2/fetch_yardsticks.sh
(cd src2 && ../.venv/bin/python make_final.py)
sha256sum submissions/final/prediction.csv
echo "expected 7f02eee6cbc46ba257e86d2b309f2fc6bc970163b7cbfc0bab457f14137c2331"
