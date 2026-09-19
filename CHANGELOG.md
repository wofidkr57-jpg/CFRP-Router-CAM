## V1.13 — 2026-09-19

- STEP 수평 단차면의 아일랜드 포켓 가져오기(기본 ON/옵션 OFF 지원).
- 양각 보호, 판 외곽 오픈 포켓, 반복 오프셋 황삭 및 경계 정삭.
- 스텝오버 40%, 패스 깊이 0.25mm, 정삭 여유 0.1mm 기본값 및 저장.
- 포켓 우선/깊이 순서, 각 경로 사이 안전 높이 이동, Top/Bottom·XY 원점 지원.
- 배열/회전/이동에 양각 보호 경계를 함께 변환. 보호영역 및 다른 부품과의 공구 스윕 충돌 차단.
- 가져온 바닥 이상 깊이, 잘못된 절입 설정, 포켓의 마모 보정 동시 사용 차단.
- 청록색 경로 미리보기·잔여 면적 경고·NC 헤더·절삭거리 계산 추가.
- 단위 검사 49개 및 포켓 GUI/설정 저장 검사 추가. Windows 배포 결과는 PROJECT_STATE 기준.

## V1.12 — 2026-09-19

- STEP 선택면 대신 선택 바디 전체 투영 외곽을 추출하여 양각 면 선택 시 부분 외곽으로 잘리는 문제 수정.
- 다른 높이의 위쪽 면에 있는 홀과 기존 깊이 대응을 유지; 같은 바디 선택 중복 제거.
- Z0을 바디 최상단으로 통일하고 가져오기 완료 안내에 명시.
- 높이/속도 설정 가능한 가공 전 외곽 1회 프리뷰 추가 (기본 OFF, 30mm, 1000mm/min).
- Shapely 2.1.2 투영 합집합 의존성과 Windows 빌드 수집 추가.
- 합성 STEP 양각/관통홀/카운터보어/회전/분리 바디 및 프리뷰 회귀 검사 추가.

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

