**Title:** ENTRY FOR BEST BIAS DISCOVERY & BEST DOCUMENTATION · submission EqBuune1 · Rural ambulances filed as fire stations

---

Zindi user hero76 (Francis Miyoba). Writeup submitted through the special-prize form for both prizes.

Repository (MIT, public): https://github.com/heromiyo/zindi-world-submission
Writeup: `reports/WRITEUP.md` and `reports/hero76-writeup.pdf` in the repo.

Submissions: EqBuune1 (public 0.079801846, final) and ruvjs19G (constant 0.05, fallback).

**The finding.** In rural America the fire department often runs the ambulance. Overture lists many of those stations with `fire_department` as the primary category and EMS only as an alternate. Of 2,022 places across the four regions that carry EMS only as an alternate category, 1,334 are fire departments.

In rural tracts, only 23% of the tracts where Overture knows of an EMS service list it under the EMS category. In urban tracts it is 36%. The rural-minus-urban gap in "EMS hidden under another category" is 22.2 points (95% CI 19.7 to 24.7, county-clustered bootstrap). It holds in each region: Eastern Oklahoma +24.8, Maricopa +20.9, Northern California +27.3, South-Central Texas +20.6.

In Eastern Oklahoma it is hidden in 22.6% of tribal tracts against 12.4% of non-tribal ones, concentrated in the Cherokee, Creek, Chickasaw, Choctaw and Kiowa-Comanche-Apache-Fort Sill Apache OTSAs. Named records include the Chattanooga, Tuttle and Sayre fire departments in Oklahoma, Castroville VFD and Bulverde Spring Branch Fire and EMS in Texas, and Litchfield in Lassen County, California.

A tool that pulls ambulance services by category sees none of them. A planner reads an EMS desert where the town's own fire-based EMS sits. The scorecard can't flag this, because the station is mapped, just under another service.

**The method, briefly.** I wrote the organiser formula as an expected value. The road reference comes from Overture's own route numbers (interstate, US, state, Texas FM/RM, county routes at 0.45). That weight was set to match the printed 0.71 to 1.59 Overture/TIGER ratio range and the printed undefined shares, not to any score. Facilities and establishments use expected-gap models. No removed reference layer and no USFS/CarbonPlan building column is used.

I set four model scales from the public scores of my own probe uploads. I checked candidates with an exact projection method that also uses five public files other participants posted with their scores. Those files shaped three global numbers in my final (an intercept, a slope, a mix weight). None of their tract values is in my file. The writeup lists all nine of my uploads and says plainly what is unruled.

`./run-local.sh` rebuilds the final file and prints its sha256, which matches the upload byte for byte.

Feedback welcome, especially from anyone who knows how rural Oklahoma or Texas departments are listed in other directories.
