#!/usr/bin/env bash
# Public files other participants published with their public scores. Used only by src2/evaluate.py.
set -euo pipefail
cd "$(dirname "$0")/.."; mkdir -p outputs/yardsticks
K=https://raw.githubusercontent.com/kevin9327/ZindiBiasBounty/main
R=https://raw.githubusercontent.com/kainwangroger/bias-bounty-mapping-equity-public/main/submissions
curl -fsSL $K/zindi_v8_pure_package_hierarchical.csv -o outputs/yardsticks/kevin_v8.csv
curl -fsSL $K/zindi_v7_pure_package_structural.csv -o outputs/yardsticks/kevin_v7.csv
for f in sub_13_permitted_heuristic sub_14_permitted_roadmix sub_16_tuned_public_blend; do curl -fsSL $R/$f.csv -o outputs/yardsticks/$f.csv; done
sha256sum outputs/yardsticks/*.csv
