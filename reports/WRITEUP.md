# Coverage gaps without the reference layers: method, checks, and the ambulances filed as fire stations

Francis Miyoba · Zindi user **hero76** · Bias Bounty Mapping Equity Challenge · 31 October 2026

Entered for **Best Documentation** and **Best Bias Discovery**.

Submissions this writeup covers:

| ID | Public RMSE | What it is |
| --- | ---: | --- |
| **EqBuune1** | **0.079801846** | Final model (selected for private scoring) |
| ruvjs19G | 0.089560921 | Constant 0.05, no model (selected as the fallback) |

Code and every table quoted below are public at https://github.com/heromiyo/zindi-world-submission (MIT). Section 9 rebuilds the final file and checks its hash.

---

## 1. What I did

The organisers removed the four reference layers (TIGER roads, Microsoft footprints, USGS facilities, County Business Patterns). So I could not compute the gap. I could only estimate what it is likely to be.

I wrote the organiser's formula as an expected value. Each missing reference count becomes a guess built from the challenge package. The biggest single improvement came from roads. TIGER's S1100/S1200 classes are the roads that carry an interstate, US or state route number. Overture keeps those route numbers in its `routes` field. So I built a TIGER-like road length from Overture's own route designations and compared it with the Overture classes the organisers use.

I then set a handful of global numbers from the public scores of my own submissions, and I checked the result with a method that gives an exact score for anything inside the span of files whose scores I know.

## 2. Data

Base URL for every challenge file (public, no login):
`https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/`

| Input | Path under the base URL | Retrieved | Used for |
| --- | --- | --- | --- |
| Overture roads | `reference/<region>/<region>-overture-roads.parquet` (`class`, `geometry`; `routes` re-read) | 23 Oct 2026; `routes` 31 Oct 2026 | Compared road length and the TIGER-like proxy |
| Overture places | `reference/<region>/<region>-overture-pois.parquet` | 23 Oct 2026 | Fire, EMS, school and all-place counts |
| Overture buildings | `reference/<region>/<region>-overture-buildings.parquet` (`bbox` only) | 23 Oct 2026 | Building count per tract |
| ACS housing | `reference/<region>/<region>-census-acs-housing.csv` | 23 Oct 2026 | Places-per-home scale, zero-housing flag |
| Tract polygons | `strata/<region>/<region>-census-tracts.parquet` | 23 Oct 2026 | Geometry, land area |
| Strata table | `strata/<region>/<region>-strata-tract-table.parquet` (`pop_total`, `ALAND`, `pct_urban`, `ur_class`, `tribal_any`, `aiannh_name`, `svi_overall`) | 23 Oct 2026 | Population, urban share, tribal flags |
| Sample files | `reference/<region>/<region>-sample-submission.csv` | 23 Oct 2026 | The 9,794 rows, GEOID read as text |

`<region>` is `eastern-ok`, `maricopa-az`, `northern-ca`, `south-central-tx` and `eastern-wa`. Every file's URL, size and sha256 is logged in `metadata/download-manifest.json`.

Used to check and choose between my candidates, never copied into my file (sections 5 and 6), retrieved 31 Oct 2026:

- `https://github.com/kevin9327/ZindiBiasBounty`: `zindi_v8_pure_package_hierarchical.csv` (public 0.084048897), `zindi_v7_pure_package_structural.csv` (0.08513992)
- `https://github.com/kainwangroger/bias-bounty-mapping-equity-public`: `submissions/sub_13_permitted_heuristic.csv` (0.091386601), `sub_14_permitted_roadmix.csv` (0.088906556), `sub_16_tuned_public_blend.csv` (0.082014142)

Not used: the USFS and CarbonPlan building columns in the strata table (`usfs_BuildingCount_sum`, `usfs_HUCount_sum`, `carbonplan_buildings` and the rest). Several participants asked whether they count as copies of the Microsoft footprints. No organiser answered, so I left them out. A grep of the code confirms none of them is read. The removed reference layers were never downloaded.

No paid service runs anywhere in the pipeline.

## 3. How I computed each component

All lengths are in EPSG:5070 metres after clipping each road to the tract. Points go to the tract that contains them; on a boundary the smallest GEOID wins.

### Roads

- **Overture side (O):** length of `motorway`, `trunk`, `primary`, `secondary`. This is the organiser's numerator.
- **Reference side (R), the TIGER-like proxy:** length of every segment whose route network is an interstate (`US:I...`), a US route (`US:US...`), a state route (`US:XX`), a Texas farm/ranch road (`US:TX:FM`, `US:TX:RM`) or a state sub-network (Loop, Spur, Business, Beltway, Toll and similar), plus unrouted motorways. County routes (`US:OK:Washita`, `US:CA:CR` and so on) count at 0.45.
- **Defined** when R is at least 100 m.
- **Gap** = E[max(0, 1 − O/R)] with R treated as log-normal around the proxy (σ fitted, 0.68). This turns a hard ratio into a smooth expectation, because the proxy is not the real TIGER length.

The 0.45 county weight is not fitted to any score. It comes from two facts the organisers printed. First, the Overture/TIGER ratio ranges from 0.71 to 1.59 across regions. Second, at least one component is undefined in 21% of Eastern Oklahoma, 37% of Northern California, 28% of South-Central Texas and 55% of Maricopa tracts. With w = 0.45 my proxy gives:

| Region | O / R | Tracts with no reference road |
| --- | ---: | ---: |
| Eastern Oklahoma | 0.76 | 22% |
| Maricopa | 1.62 | 54% |
| Northern California | 1.44 | 31% |
| South-Central Texas | 1.03 | 20% |

The ratios span 0.76 to 1.62, close to the printed 0.71 to 1.59. Three of the four undefined shares sit below the printed "at least" figures, which fits, because buildings and POIs add undefined tracts of their own. Oklahoma sits one point above (22% against 21%).

### Facilities (fire, EMS, schools)

Overture counts use the primary category: `fire_department`; `ambulance_and_ems_services`; `school`, `elementary_school`, `middle_school`, `high_school`, `public_school`, `private_school`.

For each type I need two things: the chance the reference has one in this tract, and the expected gap if it does.

- A logistic model gives the chance Overture has the type, from population, land area, urban share, place count, building count and region.
- I assume Overture finds 70% of real facilities. Then P(reference has one | Overture has none) = a(1 − 0.7)/(1 − w), with a = w/0.7.
- Where Overture has one or more, the type is defined and the expected gap is 0.5/(count + 1).
- Where Overture has none, the gap is 1 whenever the type is defined.
- The facility half is the probability-weighted mean of the defined types.

### Establishments

Overture places per home is fairly steady inside a region. I take the regional median places-per-home, halve it as a floor, and score the shortfall: max(0, 1 − places / (0.5 × median rate × homes)).

### Buildings

Overture ingests Microsoft's footprints where no hand-drawn building exists, so the reference is partly inside the numerator. The fitted building gap came out at 0. I kept the component in the divisor (it is defined wherever Overture has a building) but it adds nothing to the numerator.

### Composite

Score = (transport × defined_T + building + POI) / (defined_T + defined_B + 1), the organiser's "mean of the defined components". POI = 0.5 × facilities + 0.5 × establishments, or establishments alone when no facility type is defined.

Two light post-steps: a term for unrouted tertiary roads (0.05 × tertiary/(tertiary + compared + 500 m)), and a pull of 50% toward the county mean, because neighbouring tracts share mappers, imports and road agencies.

## 4. Edge cases

| Case | Count | Handling |
| --- | ---: | --- |
| Zero population | 26 scored tracts | Computed like any other tract. Transport and POI references do not depend on residents. |
| Zero housing units | 80 | Building component still defined if Overture has buildings; establishments floor uses one home so the ratio stays finite. |
| Water-dominated (ALAND = 0) | 2 | No roads, no places: transport undefined, POI falls to the establishments term, which the county pull keeps near the county level. |
| No Overture data at all (no roads, places or buildings) | 2 | Every component falls back to its undefined rule; the county pull and calibration give the tract its county level. |
| No Overture road in the compared classes | 173 | Transport gap is 1 wherever the route proxy finds a reference road, and undefined where it finds none. |
| No Overture facility of a type | varies by type | Never treated as complete. Zero Overture facilities with a likely reference gives a gap of 1 for that type. |
| Eastern Washington (415 rows) | 415 | In the sample file but outside the four scored regions. Kept in the file at 0. |
| New Mexico tract 35023970000 | 1 | Treated as Maricopa, as the challenge page says. |
| Scores outside [0, 1] | none after clipping | Final scores run 0.0 to 0.24. |

## 5. How I set the numbers

Without labels, the only ground truth is the public score. I used my own submissions as measurements. One upload gives one number: the RMSE of that file. Because RMSE² = E[y²] − 2⟨p, y⟩ + E[p²], and the all-zero upload gives E[y²], each further upload tells me ⟨p, y⟩ for that file.

My nine uploads:

| ID | File | Public RMSE | Why |
| --- | --- | ---: | --- |
| oEhc56z5 | all zeros | 0.107246299 | gives E[y²] |
| uG9arWJm | demographic peer shortfall | 0.140188939 | first model, worse than zero |
| eokiTaFt | geographic peer shortfall | 0.139906454 | first model, worse than zero |
| otAG1PYG | 0.8 zero + 0.2 peers | 0.102887364 | shrinkage |
| w89UKeSA | facility component alone | 0.097931153 | probe |
| kbULCqLs | establishments component alone | 0.109089522 | probe |
| fYoHzJoW | building component alone | 0.124615516 | probe |
| ruvjs19G | constant 0.05 | 0.089560921 | probe; gives mean(y) = 0.0598 |
| **EqBuune1** | **final** | **0.079801846** | |

The numbers fitted from these scores are global, the same for every tract:

- four model scales, fitted to my own probe scores only: facility 0.055, establishments 0.102, building 0, road σ 0.68;
- an affine calibration, 0.0127 + 0.917 × score, and a mix, 0.85 × model + 0.15 × the own-probe blend. These three numbers were chosen with the checking method in section 6, which also uses five public files from other participants. So those files influenced three global numbers in my final file. None of their tract values enters my file.

No tract-level value was inferred.

Two participants asked the organisers whether fitting global weights from your own public scores is allowed (#35532, #35657). There was no organiser answer by 31 October. I am stating exactly what I did so the judges can decide. If it is not allowed, ruvjs19G (a plain 0.05) is selected as my second submission and uses no fitting at all.

## 6. How I checked it without labels

For any file p, I split it into a part inside the span of files with known public scores, plus a residual r. The inside part has an exact score contribution. For the residual, |⟨r, y⟩| ≤ ‖r‖·‖y⊥‖, and ‖y⊥‖ is also known. That gives a guaranteed interval and a central estimate.

For the checking span I used my own probes plus five files other participants published with their public scores (kevin9327 v7 and v8, kainwangroger sub 13, 14 and 16). None of their predictions is copied or blended into my file. Their scores did shape my choice among candidates and the three numbers named in section 5. If the judges consider that use of other participants' public files out of bounds, ruvjs19G is unaffected. A test confirmed they share my public split: their 0.05 file scored exactly 0.089560921, like mine, and the joint covariance matrix is positive definite.

The final file was predicted at 0.0835 central, interval 0.068 to 0.097. It scored 0.0798, inside the interval.

Stability checks:

- **300 random 30% public splits:** the final beat every other candidate in 79% of draws (5th to 95th percentile 0.0832 to 0.0837 central).
- **Dropping each external file in turn:** the estimate stayed between 0.0835 and 0.0843.
- **With my own probes alone:** the central estimate was 0.0919. My probes cannot see the road signal at all, which is why I needed outside directions to trust it.

## 7. What did not help

| Change | Central estimate | Kept |
| --- | ---: | --- |
| Own-probe blend only | 0.0880 | as 15% of the mix |
| Route proxy without county routes | 0.0873 | no |
| Route proxy, county 0.45 | 0.0867 | yes |
| Defined threshold 1 km instead of 100 m | 0.0867 | no difference |
| Counting places whose alternate category is fire/EMS/school as evidence of a reference facility | 0.0835 vs 0.0835 | no gain, dropped |
| Tertiary term | 0.0856 (from 0.0867) | yes |
| County pull 30% / 50% | 0.0837 / 0.0835 | 50% |

The first two models, which compared each tract with 32 similar tracts, scored worse than predicting zero. They read low real supply as missing data.

## 8. What my bias scorecard shows

Zindi's scorecard for EqBuune1 (saved in `reports/scorecard/`):

| Stratum | Disparity ratio |
| --- | ---: |
| Rural vs urban | 1.70× |
| Tribal vs non-tribal | 1.49× |
| Wildfire hazard | 1.34× |
| High climate vulnerability | 1.25× |
| High social vulnerability | 1.01× |
| Drought, heat, hazard + vulnerability | 0.94× to 1.05× |

The rural and tribal ratios come mostly from roads. Eastern Oklahoma has 19,338 km of county and state sub-network routes in tribal tracts that sit outside the four compared classes, against 5,807 km in non-tribal tracts. Those roads exist and carry route numbers, but Overture files them as tertiary, so the score counts them as missing.

What I can't separate is real absence from classification. A gap of 1.70× rural over urban is partly a statement about how Overture labels rural roads, not only about what is on the ground. Anyone planning evacuation from these scores should read the road component as "route-numbered roads that Overture does not label as major", and check the tertiary layer before calling a road missing.

## 9. Reproduce

Environment: Python 3.12.3 on Ubuntu (WSL2). Pinned packages are in `requirements.txt`; the ones the model uses are numpy 2.5.4, pandas 3.1.0, geopandas 1.2.0, shapely 2.2.0, pyarrow 26.0.0, scipy 1.18.1 and scikit-learn 1.9.1. No GPU, no account, no API key.

```bash
git clone <this repository> && cd <repository folder>
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run-local.sh
```

`run-local.sh` downloads the package from the public bucket, builds the tract, place, building and road features (`src/`), adds route-network road lengths and alternate-category facility counts (`src2/routes.py`, `src2/poi_alt.py`), builds the model inputs (`src2/features.py`, `src2/structural.py`), rebuilds the probe files and the own-probe blend (`src2/make_probes_and_blend.py`), fetches the five public yardstick files from GitHub (`src2/fetch_yardsticks.sh`), and runs `src2/make_final.py`. It ends by printing the sha256 of `submissions/final/prediction.csv`.

Expected sha256: `7f02eee6cbc46ba257e86d2b309f2fc6bc970163b7cbfc0bab457f14137c2331`, identical to the uploaded EqBuune1 file. I rebuilt it in a fresh copy on 31 October, from the cached feature files, and the hash matched.

There is no random step in the model. The fit uses Nelder-Mead from fixed starting points. The logistic models are deterministic. The checks in section 6 run with `src2/evaluate.py` and `src2/robustness.py` (seed 20261031). The probe files are in `submissions/probes/`, and `src2/solve_blend.py` rebuilds the own-probe blend from their scores.

## 10. Limits

- The road proxy is my construction, not TIGER. It matches two printed aggregates, not tract values.
- The 70% facility recall is an assumption. The fitted facility scale (0.055) is small, which says my facility model is too confident and the fit shrank it.
- The checking method is exact only inside the known span. Outside it, the interval is wide.
- The public split is 30% of tracts. Private scores will differ.

---

## Best Bias Discovery: rural ambulances that are only filed as fire stations

### The pattern

In rural America the fire department often runs the ambulance. Overture records many of those stations with `fire_department` as the primary category and `ambulance_and_ems_services` only as an alternate. Anything that looks for EMS by primary category does not see them. If the challenge's EMS term counts by primary category, as the place counts in the package suggest, it does not see them either.

The scorecard's Emergency Access Gap counts what is mapped against a reference. It cannot see this, because the station is mapped. It is filed under a different service.

### The evidence

I took every Overture place whose alternate categories include EMS (`ambulance_and_ems_services`, `emergency_service`, `emergency_medical_service`) but whose primary category does not. There are 2,022 across the four scored regions:

- 1,334 have primary `fire_department` and 249 `fire_protection_service`;
- 1,626 of the 1,683 in tracts with no primary EMS record come from Meta's places feed;
- all 1,683 are marked open.

For each tract, "known EMS" means Overture has an EMS record under either category. "Visible" means the primary category is EMS. The table below shows the visible share, with 95% intervals from 1,000 county-level bootstrap resamples (tracts in one county are not independent):

| Region | Counties | Rural: visible share | Urban: visible share | Rural minus urban, hidden-only tracts |
| --- | ---: | ---: | ---: | ---: |
| All four | 298 | **23%** (20–26) | **36%** (32–41) | **+22.2 pp** (19.7 to 24.7) |
| Eastern Oklahoma | 73 | 23% (18–29) | 41% (32–54) | +24.8 pp (19.1 to 29.3) |
| Maricopa | 16 | 21% (9–33) | 27% (21–41) | +20.9 pp (13.2 to 29.0) |
| Northern California | 24 | 15% (7–25) | 27% (17–35) | +27.3 pp (15.6 to 35.7) |
| South-Central Texas | 185 | 25% (21–29) | 38% (32–43) | +20.6 pp (17.1 to 23.9) |

In rural Northern California, 85% of the tracts where Overture knows of an EMS service do not list it as EMS.

In Eastern Oklahoma, EMS is hidden in 22.6% of tribal tracts against 12.4% of non-tribal tracts. The hidden-only tracts cluster in the Cherokee OTSA (36 tracts), Creek OTSA (35), Chickasaw OTSA (25), Choctaw OTSA (17) and Kiowa-Comanche-Apache-Fort Sill Apache OTSA (16).

Named examples:

| Tract | Record | Primary category | Area |
| --- | --- | --- | --- |
| 40031002301 | Chattanooga Fire Department | fire_department | Kiowa-Comanche-Apache-Fort Sill Apache OTSA, rural |
| 40051000902 | Tuttle Fire Department | fire_department | Chickasaw OTSA, rural |
| 40009966800 | Sayre Fire Department | fire_department | Cheyenne and Arapaho OTSA, rural |
| 48091310703 | Bulverde Spring Branch Fire and EMS, Station 3 | fire_department | Comal County TX, rural |
| 48325000103 | Castroville Volunteer Fire Dept | fire_protection_service | Medina County TX, rural |
| 48055960103 | Travis County Fire Rescue Station 1107 | fire_department | Caldwell County TX, rural, SVI 0.76 |
| 06035040400 | Litchfield Town Standish Litchfield Fire Department | fire_protection_service | Lassen County CA, rural |
| 04013050621 | Buckeye Fire Department Station 705 | fire_department | Maricopa County AZ, rural |

The full list of records with coordinates is `reports/discovery/ems-alternate-only-records.csv`. Tract tables are `ems-hidden-by-stratum.csv`, `ems-hidden-eastern-ok-tribal.csv`, `ems-hidden-rural-tracts.csv` and `ems-hidden-ci.csv`.

### Who it affects

The people affected are rural and tribal residents whose nearest ambulance is crewed out of a fire station: volunteer departments in Medina and Caldwell counties in Texas, the town departments of the Oklahoma OTSAs, Lassen County in California.

Three concrete failures follow:

- **Dispatch and mutual aid.** A regional tool that pulls ambulance services from open map data by category finds no EMS record in tract 40031002301, even though the Chattanooga Fire Department there carries an EMS tag. A planner sees an EMS desert and may route a call to a distant private ambulance when the town's own fire-based EMS is closer.
- **Disaster relief allocation.** Funders who use mapped EMS counts to pick where to place staging posts or grant money will rank these tracts as the most under-served, and the gap will look like a missing station rather than a mislabelled one. Money goes to building what exists, while the real constraint (crew numbers, vehicle age) goes unmeasured.
- **The coverage-gap score itself.** If the EMS term compares primary-category Overture records with a station reference, then where the station is there but filed as fire, the term reads 1, a total gap. The score then says rural tribal Oklahoma is badly mapped for EMS, when what it lacks is a second category label.

### How to reproduce

From the challenge package only, no extra data:

```bash
.venv/bin/python src2/poi_alt.py <region>     # sibling-category counts per tract
.venv/bin/python src2/discovery_frame.py       # tract frame (needs road-routes2 from src2/routes.py)
.venv/bin/python src2/ems_alt.py              # records, strata tables, named tracts
.venv/bin/python src2/discovery_ci.py         # county-cluster bootstrap, seed 20261031
```

"Rural" and "Urban" are the tract table's `ur_class`. "Tribal" is `tribal_any`.

### What this does and does not show

It shows how Overture categorises emergency services, and that this differs sharply between rural and urban tracts, in all four regions and inside each one.

It does not prove every one of these stations runs an ambulance today. An alternate tag is a claim from the source, mostly Meta's places feed, and 16% of the hidden records name EMS, rescue, ambulance or medic outright. A judge can test the claim by calling a sample of the named departments.

I tested two candidate patterns before choosing this one; the other was the Oklahoma county routes in section 8. I report the stronger one and say so.

On the data side the fix is cheap. When a place carries EMS as an alternate category, emergency queries should count it as EMS.
