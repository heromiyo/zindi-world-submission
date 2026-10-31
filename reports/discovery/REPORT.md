# Emergency-record discovery report

**Local exploratory analysis; no writeup has been submitted.**

Of 4,478 supplied fire/EMS POI records, 91 are explicitly marked permanently_closed. Another 1,171 have unknown status. These are observations about the supplied map snapshot, not verified closures of real services.

## Primary comparison

Covered records: 4,440; excluded for incomplete community context: 38. Heat means historical summertime days above a locally defined percentile of maximum heat index (2015–2023), not current weather. Region-specific cutoffs are in context-thresholds.csv. It is relative unusual-heat frequency, not an absolute cross-region temperature ranking.

Region/service-standardised high-context minus comparison difference: -0.424 percentage points.
Known-status-only sensitivity: -0.780 percentage points.

The primary positive-disparity hypothesis is not established by this design. Do not replace it with a favourable subgroup and describe that as confirmation. The snapshot still contains source-reported closed emergency records worth reviewing.

County resampling is a sensitivity/generalisation model, not a confidence statement about the exact snapshot totals. Its assumptions and interval are in findings.json. Cells require at least5 records per group; primary groups must also have at least20 records overall. Few-record cells and context exclusions limit interpretation.

## Named record examples — verification queue, not findings of real closure

| Region | GEOID | Name | Street recorded in source |
| --- | --- | --- | --- |
| eastern-ok | 40109980006 | Emsa | 1111 Classen Dr |
| eastern-ok | 40113940013 | Central Med Ems Inc | 201 E 6th St |
| eastern-ok | 40143006703 | Jenks Fire Department | 205 N Elm St |
| eastern-wa | 53017950500 | Ballard Ambulance | 1100 Valley Mall Pkwy |
| eastern-wa | 53017950500 | Lifeline Ambulance | 230 Grant Rd |
| eastern-wa | 53057951101 | Marblemount Fire Hall | 60099 State Route 20 |
| maricopa-az | 04007000200 | Beaver Valley Fire Department | 911 W Beaver Flat Rd |
| maricopa-az | 04013105501 | Jdr Research | 8055 N 24th Ave |
| maricopa-az | 04013113800 | Lifebot | 4600 E Washington St |
| northern-ca | 06007000201 | Merit Medi-trans | 1355 Eaton Rd  # A |
| northern-ca | 06057000502 | Nevada County Consolidated Fire District | 11329 McCourtney Rd |
| northern-ca | 06061020300 | American Medical Response | 451 Grass Valley Hwy |
| south-central-tx | 48021950401 | Metrocare Ambulance | 104 Grady Tuck Ln |
| south-central-tx | 48029152201 | Sandyoaks Volunteer Fire Department | 3306 Hardy Rd |
| south-central-tx | 48029171401 | Express Handicap Inc | 5707 Grey Rock Dr |

## Why this could matter

A map consumer that counts every emergency-category record without examining identity or status may mistake stale records for usable services. This is a plausible mechanism. We have not shown an actual dispatcher used these records, that an ambulance was delayed or that any person was harmed. Existing services may have moved, changed operators, shared dispatch contacts or stale status metadata.

## Reproduce and review

Run src/discovery.py after the supplied-data POI extraction. All thresholds, denominators, exclusions, cell comparisons and named record IDs are exported. The80-record review queue is deliberately marked not_independently_verified; it requires evidence before any stronger assertion. No additional source data were used. Data provenance and fixed-seed decisions are in metadata/ and preparation/IMPLEMENTATION-DECISIONS.md.

Files: emergency-record-evidence.csv; source-closed-records.csv/.geojson; raw-group-comparison.csv; primary-comparisons.csv; known-status-sensitivity.csv; context-thresholds.csv; record-review-queue.csv; findings.json.
