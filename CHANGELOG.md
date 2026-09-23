## 미배포 — 설정 패널 폭 자동 조절

- 수동 배치 테두리 스냅(가장자리 여유 유지), 스냅 후 다음 두 번 드래그 자유 조정, 다중 선택 묶음 스냅을 추가했다.
- 배치 중 공구 지름·치수 보정의 간단한 중심선 미리보기를 추가했다. 무거운 충돌 계산과 리드인/마모/포켓은 제외한다.

- 수동 배치 Ctrl+클릭 다중 선택/해제와 전체 강조, 공동 드래그/방향키 이동 및 복사/삭제를 연결했다. R/F는 각 선택 개체 중심 기준으로 적용한다.

- 고정 285px 설정창 대신 입력칸의 필요 폭으로 좌우 패널을 배분하고 설명을 줄바꿈한다. 좁은 설정창에는 가로 스크롤을 제공한다.
- 경계 드래그 비율을 창 크기 변경 시 유지하고 더블클릭/글자 크기 변경 시 자동 폭으로 복원한다.

## V1.25 — 2026-09-23 · 배치 키보드 편집

- 방향키를 누르고 있는 동안 키 반복으로 선택 개체를 연속 이동한다. 반복당 0.1mm, Shift 1mm이며 입력란/점 선택/드래그 중에는 적용하지 않는다.
- 수동 배치 R 90° 회전을 유지하고 F 좌우 반전을 추가했다. 개체 중심 기준이며 내부 윤곽·탭·시작점·포켓·브리지 보존 및 되돌리기를 지원한다.

## V1.24 — 2026-09-23 · 두께별 추천 피드·1회 점 선택·개체 편집

- 선택 수량 변경을 실제 미리보기에 반영하고 기존 배치 유지·0개 후 복원·되돌리기를 지원한다. 추가 복사본은 빠른 임시 배치이며 판재 초과를 표시한다.
- 화면 선택 개체 Del 삭제와 CAM 내부 Ctrl+C/V 복사를 추가했다. 내부 윤곽까지 묶음 처리하고 다중 개체 상대 위치·시작점·탭 보존, 실제 수량 갱신, 입력란 단축키 분리, 새 파일의 복사 버퍼 초기화를 적용했다.

- 2T F600 / 3T F550 / 6T F500 사용자 시험값을 표시하고 버튼으로 적용한다. 기존 피드 자동 덮어쓰기와 임의 보간은 하지 않는다.
- 시작점·수동탭은 유효한 1회 선택 후 OFF, 측정·두 선 연결은 완료 후 OFF로 전환한다. 시작점과 수동탭/연결 모드의 상호 배제 및 수동 배치 드래그 모드 종료를 보완했다.
- 추천값/수동탭 회전 보존 단위 검사와 실제 GUI 클릭·재선택·어레이 복사·재시작 검증을 추가했다.

## V1.23 — 2026-09-23 · 내경·외경 치수 보정

- CAM 설정에 내경/외경 지름·폭 보정을 추가했다. 양수 확대, 음수 축소, 경로는 절반 이동. 요청 초기값 +0.10/-0.14mm를 설정하며 0으로 비활성화한다.
- 원본 형상·공구 지름·마모 보정률을 유지하고 닫힌 윤곽의 미리보기·안전검사·황삭·정삭·NC 헤더에 반영한다. 포켓·열린 선 제외. 설정 저장과 코드 캐시 무효화를 지원한다.

## V1.22 — 2026-09-23 · 윤곽 네스팅과 어니언스킨 황삭/정삭 파일 분리

- 실제 외곽으로 빈 공간을 활용하는 촘촘한 배열과 180° 엇갈림을 추가했다. 기존 박스 배열은 유지한다.
- 파츠별 외곽 여유를 합산해 최소 간격을 확보한다. 빈칸은 공통 간격의 절반이며 파츠 복사본에 같은 값을 적용한다. 원본 치수·공구 보정은 변경하지 않는다.
- 가공 공간 부족 경고, 배치 취소, 여유 설정 되돌리기와 검사 5개 및 GUI 경로를 추가했다.
- 배열 복사본의 회전 형상은 파츠·각도별로 한 번만 준비해 중복 계산을 줄였다.

- 기존 선택 윤곽 PART1/2 버튼을 제거하고 어니언스킨 황삭/정삭 분리 체크박스로 교체했다.
- 분리 시 기본 바닥 잔여율 10%, 전체 측면 정삭, 마이크로탭 없음. ROUGH와 FINISH는 공통 XY 원점을 유지하며 새 공구 기준으로 각각 계산한다.
- FINISH 전용 START/END 편집·저장을 추가했다. 항목별 빈 입력은 기존 START/END를 사용하며 ROUGH에는 기존 코드만 적용한다.
- 파일별 예상거리/시간, 8m 경고·10m 생성 차단 및 파일명 시간을 유지한다.

## V1.21 — 2026-09-22

- Tkinter 3D 시뮬레이션의 공구경로/깊이맵 전환과 급속선 표시 변경에서 Canvas 선을 재사용하고 태그 표시 상태만 전환한다.
- 시점·확대·이동·뷰포트 크기 변경 시에만 투영 캐시를 무효화한다. 모드별 범례 공간을 고정해 불필요한 창 크기 이벤트를 막는다.
- 공구경로 모드에서도 완료 절삭 깊이 상태를 유지해 깊이맵 복귀와 되감기에 반영한다.
- 10,000개 이동 반복 전환, 급속 표시, 진행/되감기, 카메라/리사이즈 회귀 검사 추가. 가공 경로 생성은 변경하지 않는다.
- 2분할 저장 파일명의 시간은 전체 시간이 아니라 PART1·PART2 각각의 예상 절삭시간으로 표기한다.
- 기존 누적거리·누적시간 입력과 NC 누적 표기를 제거한다. 각 작업의 마모 보정은 0m부터 시작하며, 2분할은 안내대로 PART2 전에 새 공구로 교체하는 전제로 두 파일을 각각 계산한다.
- 공구 마모 감소량 단위를 100m당 값에서 10m당 값으로 변경하고, D2.00 공구가 11.44m 가공 후 D1.91로 측정된 결과를 반영해 기본값을 `0.079mm/10m`로 설정한다. 기존 사용자 지정 100m당 값은 불러올 때 10으로 나눠 변환한다.
- 한 공구의 예상 절삭거리가 8m 이상이면 확인 경고를 표시하고, 10m 이상이면 G-code 생성을 차단한다. 분할 출력은 PART1·PART2 각각의 거리를 판정한다.

## V1.20 — 2026-09-20

- 경로 허용오차 기본값을 0.02mm에서 0.01mm로 변경. UI와 NC 생성 기본값 일치.
- V1.19 이하 저장 설정의 0.02mm를 0.01mm로 전환. 0(비활성) 등 다른 지정값과 V1.20 이후 설정 유지.

## V1.19 — 2026-09-20

- 어니언스킨/황삭 측면여유 후 벽면정삭 기본OFF. 이전 버전 설정을 처음 불러올 때 두 옵션을 OFF로 전환하고 이후 명시적 선택은 보존.
- 경로 허용오차 기본0.02mm(0=비활성, 최대0.1mm). 일정 Z 구간의 불필요한 G1 선분 축소, 10도 이상 코너와 탭/램프 Z 변화 보존. 기존 G2/G3 리드 동작 유지.
- 포켓 연속 가공 기본ON. 공구 전체 이동 영역을 검사한 G1 연결로 같은 깊이의 인접 경로를 연결. 먼 연결은 마지막 스텝오버 외에 이미 가공된 영역만 사용.
- 다음 깊이로 이동할 때도 이미 비운 영역에서 안전하게 연결되면 Z 상승 없이 Plunge로 다음 깊이 진입. 양각/다른 부품 간섭 또는 검증 불가 구간은 안전Z로 복귀.
- 포켓 연결 거리와 절입 횟수를 거리/예상시간에 반영. 단순화로 잔삭 검증에 실패하면 해당 포켓은 기존 정밀 경로로 복귀.

## V1.18 — 2026-09-19

- 기본 안전 Z를 소재 윗면 + 판 두께×2로 자동 계산. 두께 변경/STEP 가져오기/설정 복원 시 표시와 NC에 반영.
- 급속 접근 여유 기본1mm 유지. 자동 안전 Z를 끄면 수동 값 사용.
- 접근 여유가 안전 높이보다 큰 경우 기존 검증으로 차단(두께0.5mm 미만은 수동 안전 높이 조정 필요).

## V1.17 — 2026-09-19

- 안전 Z로 급속 상승 → XY 급속 이동 → 소재 윗면 + 접근 여유까지 G0 → 설정 Plunge로 G1 절입.
- 급속 접근 여유 기본1mm, 안전 Z와 독립 설정. TOP/BOTTOM 원점에서 실제 소재 윗면 기준 계산.
- 프로파일/홀/열린 경로/포켓/다단/정삭에 적용. XY 이동은 안전 Z 유지.
- NC 헤더·설정 저장·작업 변경 감지·절입 시간 추정에 반영.

## V1.16 — 2026-09-19

- 일반 G코드 파일 쓰기와 닫기가 완료되면 저장 완료 알림창과 파일 경로 표시. 한국어/영어 지원.
- 취소 또는 쓰기 실패 시 성공 알림 없음. 2분할 저장은 기존 완료 안내 유지.

## V1.15 — 2026-09-19

- 평면 삼각형의 내부 경계를 가짜 홀/긴 선으로 가져오던 오류 수정. 실제 평면 외곽·홀 경계를 우선 사용.
- STEP 회전/원점 변경 후 일치하는 삼각형 경계가 분리 외곽으로 오판되는 오류 수정.
- 0.0000001mm 허용오차 내 틈만 연결하고 원래 홀과 면적을 검증. 실제 분리 형상은 계속 차단.
- Defender 실행파일 검사 성공을 배포 필수 조건으로 추가. 검사 불가/탐지 시 릴리스와 자동 업데이트 변경 중단.
- V1.14의 Sabsik 탐지 원인은 미확정이며 이 형상 수정은 백신 문제 해결을 의미하지 않음.

## V1.14 — 2026-09-19

- 윤곽 목록에 `가공 여부` 열과 적용/제외 드롭다운 추가. 즉시 반영.
- Ctrl/Shift 다중 선택 후 선택 행의 가공 셀 클릭으로 일괄 변경.
- 제외 행 회색 표시, 복원 및 Undo/Redo, 왼쪽 가공 포함 설정 동기화.
- Windows GUI 회귀: 실제 셀/드롭다운 이벤트, 다중/단일 변경, NC 제외, 안전검사 설정 독립, Undo/Redo 및 복원.

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

