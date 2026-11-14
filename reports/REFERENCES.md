# References — Kansas Crop Rotation Advice (NASA Space Apps 2026)

Paste the relevant parts into the submission's References field. Items marked
[VERIFY] were written from Claude's general knowledge and should be checked
against the source before submitting.

## NASA data
1. NASA POWER (Prediction Of Worldwide Energy Resources), daily point data API, Agroclimatology
   community — rain, temperature, humidity, solar radiation, wind, soil wetness (GWETTOP,
   GWETROOT). https://power.larc.nasa.gov/
   POWER's Reference (official wording, power.larc.nasa.gov/docs/referencing/): "The data was
   obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's
   Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science
   Division."
   POWER's Data Reference: "The data was obtained from the POWER Project's Daily API v2.10.3 on
   2026/11/14." (version read from the downloaded files' header; sources listed there: MERRA-2,
   GEOS-IT, SYN1DEG, FLASHFlux, POWER)
2. O'Neill, P. E., Chan, S., Njoku, E. G., Jackson, T., Bindlish, R., Chaubell, J. & Colliander, A.
   SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture (SPL3SMP_E),
   Version 6. NASA NSIDC DAAC. https://doi.org/10.5067/M20OXIZHY3RJ
   (List only if the SMAP results are used in the final submission.)
3. Reichle, R., De Lannoy, G., Koster, R. D., Crow, W. T., Kimball, J. S., Liu, Q. & Bechtold, M.
   (2025). SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical
   Data (SPL4SMGP), Version 8. NASA NSIDC DAAC. https://doi.org/10.5067/T5RUATAQREF8
   (List only if the SMAP results are used in the final submission.)
4. NASA AppEEARS (Application for Extracting and Exploring Analysis Ready Samples), used to extract
   SMAP point time series. https://appeears.earthdatacloud.nasa.gov/
5. NASA Earthdata Common Metadata Repository (CMR), used to check dataset dates and versions.
   https://cmr.earthdata.nasa.gov/

## Other data
6. U.S. Drought Monitor, weekly county drought statistics (percent area D0–D4), via the USDM data
   services. National Drought Mitigation Center (University of Nebraska–Lincoln), USDA, NOAA and NASA.
   https://droughtmonitor.unl.edu/ — https://usdmdataservices.unl.edu/api
   Credit line (official wording, droughtmonitor.unl.edu/About/Permission.aspx): "The U.S. Drought
   Monitor is jointly produced by the National Drought Mitigation Center at the University of
   Nebraska-Lincoln, the United States Department of Agriculture, the National Oceanic and
   Atmospheric Administration and the National Aeronautics and Space Administration. Map courtesy
   of NDMC."
7. USDA NASS (2010). Usual Planting and Harvesting Dates for U.S. Field Crops, Agricultural
   Handbook 628 — Kansas "most active" planting/harvest dates, as tabulated by K-State Agronomy
   eUpdate, "Expected number of days to plant summer crops in Kansas".
   https://eupdate.agronomy.ksu.edu/article/expected-number-of-days-to-plant-summer-crops-in-kansas-501-6
8. FAO (1986), approximate seasonal crop water needs (maize 500–800 mm, sorghum 450–650,
   soybean 450–700, wheat 450–650), as tabulated by SSWM "Crop Selection".
   https://sswm.info/sswm-solutions-bop-markets/improving-water-and-sanitation-services-provided-public-institutions-0/crop-selection
9. Doorenbos, J. & Kassam, A. H. (1979). Yield Response to Water. FAO Irrigation and Drainage
   Paper 33 — seasonal Ky (maize 1.25, sorghum 0.9, soybean 0.85, winter wheat 1.05), as given in
   Table 1 of Steduto, P. et al. (2012), Crop Yield Response to Water, FAO Irrigation and Drainage
   Paper 66. https://fao.org/4/i2800e/i2800e02.pdf
10. Staggenborg, S. A. et al. (2008), on grain sorghum's drought tolerance in Kansas and Nebraska.
    https://mssoy.org/sites/default/files/documents/staggenborg-et-al-2008.pdf
11. zipcodes Python package (ZIP-code latitude/longitude, used to approximate Kansas county
    centres). https://github.com/seanpianka/zipcodes — MIT licence.

11b. Roozeboom, K. et al. [VERIFY author list] (2009). No-Till in Kansas: Rotations and Cultural Practices. K-State
    Research and Extension MF2908 - regional rotation guidance (west/central/east) and the
    double-cropping moisture rule. https://bookstore.ksre.ksu.edu/pubs/mf2908.pdf
11c. Schlegel, A., Haag, L., O'Brien, D. et al. Large-Scale Dryland Cropping Systems (K-State
    Southwest Research-Extension Center, Tribune, 2008-2015/2019) - rotations W-F, W-C-F, W-S-F,
    W-C-S-F, continuous sorghum; summer crops ~2x higher after wheat; W-S-F most profitable.
    https://core.ac.uk/download/267192795.pdf ; ASA 2014 abstract
    https://scisoc.confex.com/scisoc/2014am/webprogram/Paper86814.html
11d. Norwood, C. (1987). Continuous Cropping of Dryland Grain Sorghum. K-State Southwest Kansas
    Branch Experiment Station - fallow stores 20-30% of precipitation.
    https://ksu.janeway.systems/kaesrr/article/7459/galley/7390/download
11e. Sweeney, D. W. (2017). Tillage and Nitrogen Placement Effects on Yields in a Short-Season
    Corn/Wheat/Double-Crop Soybean Rotation. Kansas Agricultural Experiment Station Research
    Reports 3(2). https://doi.org/10.4148/2378-5977.1379
11f. USDA National Agricultural Statistics Service, Quick Stats database - Kansas county-level
    YIELD (corn, sorghum, soybeans, winter wheat; "ALL PRODUCTION PRACTICES"), 2015-2025, accessed
    2026-11-14 via the Quick Stats API. Used to validate the model's weather scores and to calibrate the heat factor (21).
    https://quickstats.nass.usda.gov/ - API: https://quickstats.nass.usda.gov/api
    Notice commonly shown by NASS API users [VERIFY on quickstats.nass.usda.gov/api terms]: "This product
    uses the NASS API but is not endorsed or certified by NASS."

11g. Allen, R. G., Pereira, L. S., Raes, D. & Smith, M. (1998). Crop Evapotranspiration - Guidelines for
    Computing Crop Water Requirements. FAO Irrigation and Drainage Paper 56 - Penman-Monteith reference
    evapotranspiration (ET0) computed daily from NASA POWER temperature, humidity, sunlight and wind, used to
    scale each season's crop water need. https://www.fao.org/3/x0490e/x0490e00.htm
11h. K-State Research and Extension heat thresholds used for the heat-stress factor: corn - temperatures above
    95 F around silking (Ciampitti & Knapp, "Impacts of hot weather", 2017,
    https://secondary.climate.ksu.edu/news/stories/2017/07/impacts_of_hot_weather); wheat - above 82 F just
    before flowering ("Effects of high temperatures on wheat",
    https://eupdate.agronomy.ksu.edu/article/effects-of-high-temperatures-on-wheat-546-3); sorghum - heat units
    capped at 100 F ("Too cool too soon? Finishing up grain sorghum before the first freeze",
    https://eupdate.agronomy.ksu.edu/article/too-cool-too-soon-finishing-up-grain-sorghum-before-the-first-freeze-661-1);
    wheat freeze at boot/heading below 28-30 F ("Wheat growth stage update and risk of freeze damage",
    https://eupdate.agronomy.ksu.edu/article/wheat-growth-stage-update-and-risk-of-freeze-damage-april-7-2017-624-5).
    Soybean heat threshold (95 F) is a team assumption; the calibration set its weight to 0.

## Software and services
12. Cloudflare R2 object storage: hosts the public app file app_rotation_advice.json (Public
    Development URL, r2.dev), uploaded through R2's S3-compatible API. https://developers.cloudflare.com/r2/
    Tiger Data / Tiger Cloud (managed PostgreSQL with TimescaleDB) was used as the database until
    2026-11-14 and then replaced by R2. https://www.tigerdata.com/
12b. GitHub and GitHub Actions: code hosting and the weekly automatic refresh
    (.github/workflows/weekly_refresh.yml). https://github.com/vp822-arch/spaceapps2026-kansas-crop-rotation
13. Python libraries: pandas 2.3.3 (BSD-3-Clause), NumPy 2.2.6 (BSD-3-Clause), scikit-learn 1.7.2
    (BSD-3-Clause), SciPy 1.15.3 (BSD-3-Clause), Matplotlib 3.10.9 (Matplotlib licence, PSF-based),
    zipcodes 3.0.1 (MIT), boto3 (Apache-2.0; R2 upload), psycopg 3 (LGPL-3.0-only; old Tiger loader
    only). Versions/licences read from installed package metadata, except NumPy/SciPy/Matplotlib
    licence names [VERIFY].
14. uv (Astral) Python package runner: installs Python 3.12 and the pinned libraries for each run.
    https://github.com/astral-sh/uv (Apache-2.0 / MIT [VERIFY]).

## AI assistance (disclosure)
15. Claude (Anthropic), an AI assistant, was used throughout the data-analysis work. Claude wrote
    the Python scripts in scripts/ (download, cleaning, normals, model, backtest, charts, crop
    ranking, rotation ranking with the current-crop feature, yield validation, app JSON export,
    Cloudflare R2 upload, weekly refresh and GitHub Actions workflow; each file is labelled), ran the analysis steps on the team's data,
    researched and checked data sources, and drafted explanations and this reference list. The
    team chose the problem, the workflow, the Kansas focus, the data stack, crop rotation advice with the current-crop
    feature, Tiger Data and later Cloudflare and GitHub, ran the
    downloads, and reviewed the results. A full time-stamped activity log of the AI's work is kept
    in the project files "ai-activity-log.md" and "ai-activity-log-part2.md". https://www.anthropic.com/claude
