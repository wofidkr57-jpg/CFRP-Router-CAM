# Changes

## V1.11 — 2026-09-05

- Preserved user-assigned contour cut orders when creating automatic or manual arrays. Repeated order values across array instances act as array-wide machining stages; duplicate-order warnings remain limited to duplicates inside the same part instance.
- Added optional distance-based cutter-wear compensation. The assumed diameter decreases linearly from the nominal tool diameter using the previous accumulated cutting distance plus the current job distance, with a user-defined diameter loss per 100 m and minimum diameter.
- Applied one stable wear-adjusted diameter at each contour's estimated cutting-distance midpoint to avoid a changing offset distorting a single closed contour.
- Recorded wear settings and estimated job-start/job-end diameters in the ASCII NC header and each contour's applied diameter in its NC comment.
- Fixed source-name extraction for Windows paths when tests or project files are processed on another operating system.
- Verification: 28 unit tests, including array-order preservation, wear-rate/minimum calculations, and progressive G-code diameters.

## V1.10 — 2026-09-01

- Fixed the first-run language dialog being hidden behind a withdrawn main window on Windows. The language dialog is now a standalone, centered window that is shown before grabbing input.
- Added stock thickness after the tool name in NC filenames: `YYMMDD_2.0endmill_T3.0_source_quantity_35min.nc`. Split output retains the same thickness with `_PART1` and `_PART2` suffixes.
- Published the actual Python source, tests, pinned build dependencies and Windows build instructions in this repository and a separate release source ZIP.
- Kept existing settings, G-code machining logic and update replacement behavior unchanged.
- Verification: 24 unit tests; clean first-run Korean, English and close-button paths; saved-language restart; English UI and tab-control order. The first-run regression check fails on V1.09 and passes on V1.10.

## V1.09 — 2026-08-30

- Added Korean/English language selection and English UI.
- Added ASCII-only NC output with a full machining-settings header.
- Grouped tab-operation buttons under tab settings.

## V1.07–V1.08

- Introduced verified GitHub updates and portable settings compatibility.
