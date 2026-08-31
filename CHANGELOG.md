# Changes

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
