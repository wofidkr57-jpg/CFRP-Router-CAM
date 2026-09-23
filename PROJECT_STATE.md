# CFRP Router CAM 프로젝트 상태

- 기준일: 2026-09-23
- 저장소: `wofidkr57-jpg/CFRP-Router-CAM`
- 공개 범위: **공개 저장소(기존 운영 상태 유지)**
- 기본 브랜치: `main`
- 현재 애플리케이션 소스 버전: **V1.25 + 미배포 패널 폭 개선**
- 배포 상태: **V1.25 릴리스·자동 업데이트 반영 완료**. Windows CI 검사94개·GUI11경로·EXE 빌드·Defender 검사 통과. 실제 CNC 가공은 미검증.
- V1.11 코드 기준 커밋: `75df745841c890911ac94e945b7f77b8cd94f6fe`
- V1.11 업데이트 매니페스트 기준 커밋: `4ad0c9e44d3fad34305d36e58947cce873c36df5`
- 이 문서는 클라우드 채팅과 여러 로컬 PC가 같은 작업 상태를 이어받기 위한 정본이다.

## 현재 작업 — 2026-09-22

### 후속 작업 — 2026-09-23
- 같은 PR #6에 수동 배치 Ctrl+클릭 다중 선택/해제를 추가했다. 전체 선택 강조, 상대 위치를 유지하는 공동 드래그/방향키, 전체 복사/삭제 연결, R/F 각 개체 중심 적용. 회귀94개·GUI13경로·Windows EXE 빌드·구문/diff 검사 통과. 단일 선택/빈곳 해제/다중 드래그/다른 복사본 보존/되돌리기를 검증했다. V1.25 배포는 유지한다. 사용자 판재 밖 경로 질문에 실제 코드를 확인: 현재 경계 검사는 형상 bbox 기반 경고이며 승인 후 생성 가능, 공구·리드인 전체 이동 범위의 판재 이탈 차단은 미구현. 클램프/받침판/기계 한계는 검증하지 않는다.
- `fix/responsive-panels`: 고정 폭 설정 패널에서 입력칸이 잘리는 문제를 수정했다. 컨트롤 필요 폭 기반 자동 배분·긴 설명 줄바꿈·좁은 패널 가로 스크롤, 경계 드래그 비율 유지 및 더블클릭/글자 크기 변경 시 자동 폭 복원을 추가했다. 회귀94개·GUI12경로·Windows EXE 빌드·구문/diff 검사 통과. 실제 Tk 최대화/1600·1200 폭/입력칸 경계/스크롤/글자 크기 검사 완료. V1.25 배포 유지, 가공 코드와 기계 제어 변경 없음.
- V1.25 배포 확인: PR #5 병합 b177f57, Actions 35816637996 성공, 매니페스트 1a2f6a7. 공개 EXE 2종 재다운로드 SHA-256 8814b656660828e5dd775f5c7de81c91e8dbf91ee303eb66a128beeeb3a0af32가 원격 latest.json/릴리스 digest와 일치. 소스 ZIP 해시·무결성·버전·NC/개인 설정 제외 확인. 개인 OneDrive ChatGPT_Projects/CFRP_Router_CAM/v1.25 버전별 보관 사본 해시 확인. 서버 동기화·사용자 PC 실제 업데이트·물리 키보드 및 실가공은 미확인. 촘촘한 배열 성능 개선은 별도 남은 작업이다.
- 사용자 요청으로 PR #5를 V1.25로 배포한다. 방향키 연속 이동과 수동 배치 F 좌우 반전 포함. Windows CI 검사/빌드/백신 검사를 통과한 실행파일의 실제 해시로 자동 업데이트를 갱신한다. 아래 미배포 표현은 배포 전 기록이다.
- `feat/arrow-placement`: 방향키를 누른 동안 Windows 키 반복마다 0.1mm 연속 이동(Shift 1mm), 수동 배치 R 90° 회전 유지, F 좌우 반전 추가. 캔버스 선택 인스턴스 전체에 적용하며 다중 선택 이동·입력란 및 점 지정/드래그 보호·되돌리기 지원. 반전은 개체 중심 기준, 원본 파츠/타 복사본 유지 및 탭·시작점·포켓·브리지 보존. 전체 회귀94개·기존 GUI11경로와 최종 반복키/Shift/F/R/되돌리기 검사·Windows EXE 빌드·구문/diff 검사 통과. 테스트는 키 반복 이벤트를 재현했으며 실제 물리 키보드 길게 누르기는 별도 미검증. V1.24 배포 유지, 실가공 미검증.
- V1.24 배포 확인: PR #4 병합 1d2ee4d, Actions 35809426931 성공, 매니페스트 899fdb0. 공개 EXE 2종 재다운로드 SHA-256 16494438bf267777de7a92c3de336b54f644d0aa9ecc3765b41f29b260d2d81d가 latest.json 및 릴리스 digest와 일치. 소스 ZIP 무결성·버전·NC/개인 설정 제외 확인. 개인 OneDrive ChatGPT_Projects/CFRP_Router_CAM/v1.24에 버전별 파일 복사와 해시 일치 확인. 서버 동기화·사용자 PC 업데이트 적용·실가공은 미확인. 촘촘한 배열 성능 개선은 남은 작업이다.
- 사용자 요청으로 PR #4의 검증된 기능을 V1.24로 배포한다. 로컬 회귀93개·GUI11경로·EXE 빌드 통과. 최신 매니페스트는 Windows CI 빌드/Defender 검사 후 실제 해시로 생성한다. 촘촘한 배열 최적화는 포함하지 않는다. 아래 미배포 표현은 배포 전 기록이다.
- 같은 PR #4에 선택 수량 미리보기 반영과 화면 Del/Ctrl+C/Ctrl+V를 추가했다. 수량 화살표/Enter/적용은 기존 배치 보존 후 추가분만 임시 배치, 감소는 뒤쪽 복사본 제거, 0개 후 복원 지원. Del은 내부 윤곽 포함 선택 인스턴스 전체 삭제 및 실제 수량 갱신. 복사는 현재 작업 내부 버퍼로 다중 선택 상대 위치·시작점·탭·포켓·브리지를 보존한다. 키 바인딩은 캔버스에 한정하며 새 파일 로드 시 버퍼 초기화, Ctrl+Z/Y 지원. 판재 밖 개수를 표시하며 추가 배치는 자동 네스팅 결과가 아니다. 회귀93개·GUI11경로·Windows EXE 빌드·구문/diff 검사 통과. 배포 및 실기 검증은 미실시. 촘촘한 배열 성능/개수 개선은 아직 남아 있으며 이번 수량/편집 동작에서는 해당 탐색을 실행하지 않는다.
- `feat/feed-presets-single-pick`: 두께별 2T F600 / 3T F550 / 6T F500 시험값과 명시적 적용 버튼을 추가했다. 두께 변경/설정 로드 시 피드 자동 덮어쓰기 없음, 기타 두께 보간 없음. 시작점·수동탭 1회 성공 후 OFF, 거리 측정/두 선 연결 완료 후 OFF, 잘못된 클릭은 모드 유지. 원점은 기존 1회 동작 유지. 수동 어레이 드래그와 점 선택 충돌을 방지했다. 원본 수동탭의 배열·회전 복사는 유지하며 배열 후 개별 수정은 다른 복사본으로 전파하지 않는다. 회귀93개·GUI10경로·Windows EXE 빌드·구문/diff 검사 통과. 기존 V1.23 배포본 유지, 실가공 미검증.
- V1.23 배포 확인: PR #3 병합 `0baa9d0`, Actions `35806594731` 성공, 매니페스트 `4a98301`. 공개 EXE 재다운로드 SHA-256 `38b83b1330701ffa6bd4e84730d66e9100159bb602d847b1f74f83d52e335911`가 원격 latest.json 및 릴리스 자산 digest와 일치. 소스 ZIP 무결성/버전/시험 NC와 개인 설정 제외를 확인했다. 개인 OneDrive ChatGPT_Projects의 CFRP_Router_CAM/v1.23에 실행본·소스 ZIP·매니페스트를 새로 보관하고 로컬 사본 해시를 확인했다. 서버 동기화와 사용자 PC 자동 업데이트 실행, 실제 절삭 정밀도는 미확인이다. 아래 미배포 표현은 배포 전 작업 기록이다.
- `feat/dimension-compensation`: 사용자가 요청한 CAM 일반 기능으로 내경/외경 치수 보정 입력을 추가했다. 초기 시험값 +0.10/-0.14mm(지름·전체 폭 기준), 0 비활성. 경로는 절반 이동하며 실제 공구 지름과 기존 마모 보정률은 그대로다. 설정 저장·코드 캐시·미리보기·공구 통과 안전검사·황삭·정삭·NC 헤더에 연결했다. 닫힌 윤곽만 적용하며 별도 포켓/열린 선 제외를 UI에 표시한다. 회귀91개와 새 GUI 입력/재시작/생성 검증 통과. 기존 V1.22 배포와 시험 NC는 변경하지 않는다. GUI 총9경로·Windows EXE 빌드·구문 및 diff 검사도 통과했다. 실가공은 미검증이다.
- V1.22 배포 확인: PR #2 병합 `e90a611`, Actions `35803075863` 성공, 매니페스트 커밋 `e2ff31b`. 공개 실행본 재다운로드 SHA-256 `e158d02bd1b88b691e8916fc3faca960b00c15901ca68093bd0e3c673b418072`가 원격 latest.json·릴리스 자산 digest와 일치한다. 소스 ZIP 무결성/버전 및 NC·개인 설정 제외 확인. 개인 OneDrive ChatGPT_Projects의 CFRP_Router_CAM/v1.22에 실행본·소스 ZIP·매니페스트를 보관하고 로컬 사본 해시 일치 확인; 서버 동기화 및 사용자 PC 자동 업데이트 실제 실행은 미확인. 기계 제어는 수행하지 않았다.
- 치수시험 최신본 v0.03(`local-handoff/dimension-test-v03/`)은 v0.02 시험 경로 뒤 100×100 외곽 절단을 추가했다. D2 외측 반경 보정, F500/24000rpm/Z−6.2 1회, 탭 없음. G54 XY는 완성판 좌하단이며 공구 통과 범위 X−2~102/Y−3~102로 큰 원판과 분리판 고정이 필요하다. 원본 시험 블록 동일·2966이동·원호 반경·시험부 비간섭·XY 급속 Z12 정적 검증 및 ZIP/사용자 보관 사본 해시 확인. 이전 버전 유지, 실기/서버 동기화 미검증. NC는 공개 Git 제외.
- 사용자 요청으로 V1.22 배포를 진행한다. 어니언스킨 분리/전용 코드와 윤곽 네스팅/파츠별 여유를 포함하며, 테스트 NC·개인 설정은 배포에서 제외한다. latest.json은 검증된 CI 빌드의 실제 해시로 갱신한다. 아래 미배포 표현은 배포 전 작업 기록이다.
- 치수시험 최신본은 v0.02(`local-handoff/dimension-test-v02/`): 사각형을 F500·황삭+정삭의 G1/원호 내·외곽 4개만 남겨 총 44형상/68단계로 축소했다. 홀 40개/60단계 NC는 v0.01과 동일함을 비교 확인했고 CAM 파서 2929이동 및 범위·간섭·원호·급속 검증을 통과했다. 절삭 XY 약 .723m, 이론 절삭+절입 약 6.19분(급속/가감속/대기 제외). NC·배치도·측정표·ZIP과 사용자 보관 위치 사본을 새 v0.02 이름으로 저장, ZIP 무결성/사본 해시 확인. v0.01 원본 유지, 실기·서버 동기화 미확인.
- 별도 치수시험 v0.01을 Git 제외 `local-handoff/dimension-test-v01/`에 준비했다. 100×100×6mm, D2, 홀 2.5/3/4/4.15/5 및 내·외곽 10mm 사각형(외곽 R1)을 G1/원호 × F500/800 × 1회 목표치수/황삭+정삭의 8조건으로 비교한다. Z0 상면, 최종 -6.2mm, 24000rpm, 탭/어니언스킨 없음. G1 현 오차 .001mm, 정삭 여유 .10mm이며 전체 및 구역별 NC·배치도·측정표·설명서·검증 JSON·ZIP을 작성했다. 56형상/84단계의 범위·공구 통과 비중첩·원호 반경·목표 치수·급속 Z12 정적 검사와 CAM 파서 3589이동 검증 통과. 사용자 지정 NC 보관 위치에 미검증 폴더로 복사하고 해시 일치를 확인했으나 서버 동기화는 미확인이다. NC/개인 경로는 공개 Git에 넣지 않았다. 실제 기계·고정·절삭 검증은 수행하지 않았다.
- 같은 작업 브랜치/PR #2에 촘촘한 윤곽 배열을 추가했다. 파츠별 외곽 여유는 합산(A=1/B=2→3mm)하며, 빈칸은 공통 간격의 절반이다. 같은 파츠 복사본에 동일 적용하고 원본 치수·가공 보정은 변경하지 않는다. 판재 경계에는 가장자리 여유와 파츠 여유를 더한다.
- 실제 닫힌 윤곽 충돌·거리 판정, 180° 엇갈림, 공구 지름/황삭 여유 대비 간격 경고, 취소·되돌리기를 구현했다. 구멍 내부 배치와 거울 반전은 제외한다. 기존 빠른 박스/수동 배열은 유지한다. 파츠·각도별 회전 형상은 한 번만 생성한다.
- 파츠 여유는 현재 작업/되돌리기에 보존하며 새 파일 불러오기 시 기본값이다. 배열 모드는 설정에 저장한다. 전역 최적 배치를 보장하지 않으며 복잡한 형상·대량·5° 탐색은 느릴 수 있다. 실제 6T 암 원본 성능은 미측정이다.
- 최신 검증: 단위 검사 87개, GUI 6경로(파츠별 여유·촘촘한 배열·경고 거절·되돌리기·설정 재시작 포함), Windows EXE 빌드 성공. 삼각형 시험은 박스 1개 대비 윤곽 2개 배치 및 간격 충족, 암 형태 시험 8개 간격 충족. 기계 제어·실가공은 수행하지 않았다. 기존 V1.21 배포본을 유지한다.
- `feat/onion-rough-finish`에서 기존 선택 윤곽 PART1/2를 제거하고 어니언스킨 분리 체크박스를 추가했다. 일반 생성/저장에서 ROUGH와 FINISH를 함께 출력한다.
- 기본 잔여율 10%(6T→황삭 5.4mm), 기존 측면 정삭 여유 적용, 분리 모드는 마이크로탭 없음. 같은 명목 지름의 새 공구로 FINISH를 실행하며 마모거리·시간·8m/10m 판정을 파일별 계산한다. 공통 XY 원점을 사용하고 FINISH 내부 형상을 외곽보다 먼저 완료한다.
- FINISH 전용 START/END 편집란은 분리 체크 시 활성화된다. 항목별 빈 입력은 기존 코드를 사용하고 전용값은 설정에 저장한다. ROUGH는 항상 기존 코드를 사용한다.
- 검사: 생성 NC 깊이·측면 여유·마이크로탭 제외·원점·새 공구 마모 초기화·기존 코드 fallback 및 전용 코드·설정 재시작·두 파일 저장 검사 통과. 전체 82개 검사, GUI 5경로, Python 구문 검사와 Windows EXE 빌드 통과. 기존 V1.21 릴리스는 유지하며 이번 변경은 소스 PR로 반영한다.
- 실기·Mach3 동작 미검증. 마무리 관통 시 별도 고정 필요. 두께별 피드 제안과 파손 후 재시작 기능은 이번 변경에 포함하지 않았다.

- 정본 작업 체크아웃: `%USERPROFILE%\Documents\CFRP-Router-CAM` (이 PC의 실제 위치는 Git 제외 `local-handoff/README.md`에 기록). 개인/회사 OneDrive 등록 루트 밖의 로컬 폴더이며 쓰기·빌드 확인 완료.
- ChatGPT 프로젝트 미러는 읽기 전용 참조로 유지. 비어 있는 `sources/` 대신 연결 GitHub 원격을 확인하여 복제했다. 기존 AGENTS.md와 본 문서를 읽고 수정했다.
- 작업 시작 기준 main `404c50e` / 릴리스 `v1.20`. PR #1을 merge commit `a57ef20`으로 병합했고, GitHub Actions가 매니페스트 커밋 `1479d61`과 `v1.21` 릴리스를 생성했다. 공개 범위는 그대로 유지했다.
- 원인: `Toolpath3D.mode_changed()` → `draw()`에서 `canvas.delete("all")` 뒤 이동마다 `create_line()`을 다시 호출했다. 범례 pack/forget도 뷰포트 크기를 변경해 추가 재생성을 유발했다.
- 실제 렌더러는 Tkinter Canvas다. BufferGeometry/EdgesGeometry/WireframeGeometry/LineSegments 및 GPU draw call은 없다. 대응 비용은 이동별 Canvas 선 생성과 스타일 지정이다.
- 수정: 경로선을 최초 투영 시 생성·보관하고 공구경로/깊이맵 및 급속 표시 전환은 태그의 normal/hidden 상태를 바꾼다. 범례 공간은 고정한다. 카메라/줌/팬/창 크기가 변경될 때만 전체 투영 캐시를 재생성한다.
- 공구경로 모드에서도 완료된 깊이 항목을 유지해 복귀 시 다시 만들지 않는다. 되감기 시 이후 깊이 항목을 제거하고 전진 시 필요한 항목만 만든다. 공구 위치·부분 선·탭 오버레이는 기존 프레임 갱신을 유지한다.
- 이동별 재생 스타일을 보존하기 위해 모든 선을 한 개로 병합하지 않았다. 경로선 수는 N개이며 전환 시 기존 N개 생성 호출은 0개다. 초기 생성 시간·메모리 비용 및 시점 변경의 N개 재투영 비용은 남는다.
- 검증: Windows Python 3.12.14, 저장소 고정 의존성으로 전체 단위 검사 **78개 통과**. 10,000개 이동의 캐시 회귀, 8m/10m 경계, 100m→10m 설정 변환, 분할 새 공구 초기화를 포함한다. 한국어·영어·첫 실행·포켓·가공 제외 GUI 스모크 **6회**, `py_compile`, `git diff --check`, `build_windows.ps1` 성공.
- 검증 범위: V1.21 최종 소스로 `dist/CFRP_Router_CAM.exe` 로컬 빌드 성공(80,249,407 bytes, SHA-256 `C54AD6ED114795330292A7789A411B9E4093BAA9001548BAB588499096711CFC`). EXE 직접 실행, Mach3·실기 제어와 절삭은 수행하지 않았다. 실제 8m/10m 소재 가공, UI 전환 시간 및 백신 판정은 미검증이다. 정식 배포 자산은 GitHub Actions에서 별도 빌드·Defender 검사한다.
- 마모 파일: 연결 파일에서 `CFRP_200x200_T2_D2_wear_slot_test_F800.nc`(34,610 bytes, 파일 시각 2026-09-06)를 발견하고 `local-handoff/`에 변경 없이 복사, SHA-256 일치 확인. 탐색 범위 내 유일한 시험 NC이며 전체 과거 첨부 기준 최신성은 미확인. 원본 조건/수식과 경로는 비공개 로컬 README에 기록. NC·개인 경로·빌드 로그는 공개 Git에서 제외.
- 원격 배포 검증: GitHub Actions `35690423548`에서 회귀78개·GUI6회·Windows EXE 빌드·Defender `found no threats` 통과. 릴리스 EXE 두 개와 `latest.json` SHA-256 `fc52d8703d9a7d7bc3ef44cc7a895c30c70e1cab7b4698bda10c6adfac175a5b` 일치. 공개 EXE를 다시 내려받아 같은 해시를 확인했다. 소스 ZIP SHA-256은 `4337ab68c9206ca487d217aa30d12a8ff29796761843217d59e9a80d38c960e3`이며 정본 소스·문서·검사 파일만 포함한다.
- 다음 작업: 사용자 PC 자동 업데이트와 실제 GUI 전환 속도, 8m 경고/10m 차단 창을 확인한다. 실제 소재 가공과 Mach3 공중 운전은 별도 검증이 필요하다. 아래 버전별 내역의 대기 항목은 과거 기록이며 현재 검증 범위는 이 절을 우선한다.
- 후속 반영: 2분할 저장 시 기존 전체시간 파일명 대신 각 작업 예상시간을 사용한다. 예: 전체 35분, PART1 12.4분, PART2 22.6분이면 `_12min_PART1.nc`, `_23min_PART2.nc`. NC 내부 개별시간 계산과 가공 내용은 기존대로 유지한다.
- 후속 반영: `기존 누적거리/기존 누적시간` UI·설정·NC 누적 헤더를 삭제. 한 작업은 새 공구 기준 0m부터 마모를 계산한다. 2분할은 기존 안내대로 PART2 전에 공구를 교체하므로 PART1·PART2를 각각 0m부터 계산한다.
- 후속 반영: 마모 보정 입력을 `10m당 지름 감소량`으로 바꾸고, D2.00 공구가 11.44m 가공 후 D1.91로 실측된 값에서 계산한 `0.079mm/10m`를 기본값으로 설정했다. 기존 100m당 사용자 지정값은 설정 로드 시 10으로 나눠 보존한다.
- 후속 반영: 각 공구/분할 파일의 예상 절삭거리가 8m 이상이면 확인 경고를 표시하고, 10m 이상이면 G-code 생성을 차단한다. 길이 판정은 마모 보정 사용 여부와 관계없이 항상 적용한다.

## 1. 프로젝트 목적

Windows에서 DXF와 STEP 형상을 불러와 CFRP 판재용 Mach3 2D/2.5D G-code를 생성하는 단일 파일 Python CAM 프로그램이다. 한국어/영어 UI, 경로 미리보기, 배열·네스팅, 탭, 다단 가공, 공구 마모 보정, NC 조건 헤더와 검증된 자동 업데이트를 제공한다.

실제 CNC 가공 전에는 생성 G-code, 작업 원점, Z 방향, 공구 지름과 보정 방향을 검토하고 시뮬레이션 및 공중 드라이런을 수행해야 한다.

## 2. 정본 파일

- `cfrp_router_cam.py`: 애플리케이션 전체 코드 정본
- `verification/`: 단위 및 GUI 회귀 검사
- `requirements.txt`: 검증된 Windows Python 3.12 의존성 고정
- `build_windows.ps1`: PyInstaller 단일 EXE 빌드
- `latest.json`: 자동 업데이트 버전·다운로드 URL·SHA-256
- `CHANGELOG.md`: 버전별 변경 내역
- `README.md`: 사용자 설치·실행·검증 안내
- `AGENTS.md`: 자동 저장, 공개 저장소 보안 및 CNC 안전 규칙
- `PROJECT_STATE.md`: 현재 작업 상태와 다음 작업의 정본

개인 `settings.json`, NC 작업물, 고객 도면, 인증정보와 개인 경로는 저장소에 넣지 않는다.

## 3. V1.11 확정 기능

- 사용자가 지정한 윤곽 가공 순서를 자동·수동 배열의 모든 복사본에 유지한다.
- 누적 절삭거리 기반 공구 마모 보정을 선택적으로 적용한다.
- `100m당 지름 감소량`과 `최소 가정 지름`을 설정한다.
- 한 윤곽 내부에서 보정량이 계속 바뀌어 형상이 왜곡되지 않도록 윤곽 예상 절삭거리의 중간 지점에서 계산한 지름을 해당 윤곽 전체에 고정 적용한다.
- NC ASCII 헤더에 마모 설정, 작업 시작/종료 예상 지름을 기록하고 각 윤곽 주석에 적용 지름을 남긴다.
- 설정 파일이 없는 첫 실행에서도 언어 선택창을 앞에 표시한다.
- NC 파일명에 판재 두께를 포함하고 분할 출력은 `_PART1`, `_PART2`를 사용한다.
- 여러 원본을 불러온 작업은 파일명 원본 부분에 `multi`를 사용한다.
- 자동 업데이트는 승인 후 EXE를 내려받아 SHA-256을 검증한 다음 기존 실행 파일을 교체한다.

## 4. 코드 수준 확인

2026-09-06에 원격 `main`의 실제 소스를 확인했다.

- `cfrp_router_cam.py::APP_VERSION`은 `"1.11"`이다.
- `UPDATE_MANIFEST_URL`은 저장소의 `latest.json`을 가리킨다.
- `validated_update_manifest()`는 버전, 허용된 릴리스 URL 형식과 64자리 SHA-256을 검사한다.
- `download_verified_update()`와 `replace_executable_files()`는 다운로드 파일과 교체 결과의 SHA-256을 검사한다.
- `effective_tool_diameter()`는 누적 거리와 100m당 감소량을 사용하고 최소 지름 이하로 내려가지 않게 제한한다.
- `contour_wear_plan()`은 윤곽 절삭거리 중간 지점의 지름을 선택한다.
- `prepare_gcode_routes()`와 `generate_gcode()` 경로에서 윤곽별 보정 지름이 G-code 생성에 전달된다.
- `gcode_settings_header()`는 마모 사용 여부, 감소량, 최소 지름과 작업 시작/종료 지름을 NC 헤더에 기록한다.
- `latest.json`은 버전 `1.11`, 릴리스 `v1.11/CFRP_Router_CAM.exe`, SHA-256 `6d4953bf2fddbc75547651443e8d59eaa9771c94fc31fee90009414d1c079175`를 지정한다.

위 항목은 코드로 확인한 사실이다. 실제 장비에서의 절삭 품질과 공구 수명 예측 정확도는 별도 실가공 검증이 필요하다.

## 5. 검증 상태

### 저장소에 기록된 결과

- `CHANGELOG.md`에는 V1.11 단위 검사 28개 통과가 기록되어 있다.
- 검사 범위에는 배열 순서 유지, 마모율/최소 지름 계산과 단계적 G-code 지름이 포함된다.
- V1.10에는 단위 검사 24개와 한국어·영어·닫기 첫 실행 경로, 저장 언어 재시작, 영어 UI 및 탭 순서 검증이 기록되어 있다.

### 이 문서 작성 시 수행한 확인

- 원격 README, CHANGELOG, 애플리케이션 소스, 빌드 스크립트, 의존성 및 업데이트 매니페스트를 직접 대조했다.
- 이 채팅에서는 Windows GUI 스모크 검사, PyInstaller EXE 빌드, Mach3 시뮬레이션과 실제 CNC 절삭을 새로 실행하지 않았다.

## 6. 빌드 및 검사

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s verification -p "test_*.py" -v
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py ko
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py en
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py close
.\.venv\Scripts\python.exe verification/gui_smoke_v108.py
.\build_windows.ps1
```

빌드 결과는 `dist/CFRP_Router_CAM.exe`다.

## 7. 미해결 및 다음 작업

1. Windows PC에서 전체 단위 검사와 GUI 스모크 검사를 재실행한다.
2. 깨끗한 가상환경에서 `build_windows.ps1`로 EXE를 재현 빌드한다.
3. 생성 G-code를 Mach3에서 시뮬레이션하고 원점·Z·공구 보정·탭·종료 동작을 확인한다.
4. 공구별 실제 누적 절삭거리와 측정 지름을 축적해 마모율 기본값의 타당성을 검증한다.
5. 다음 릴리스에서는 코드, README, CHANGELOG, `latest.json`, 릴리스 태그와 EXE 해시를 한 묶음으로 갱신한다.

## 8. 클라우드·로컬 연계 규칙

- 새 채팅이나 새 PC에서는 이 저장소를 열고 `AGENTS.md`와 이 문서를 먼저 읽는다.
- 의미 있는 변경은 실제 파일에 반영하며, 별도 저장 요청이 없어도 이 문서의 변경 내용·검증 결과·미해결 항목·다음 작업을 갱신한다.
- GitHub 쓰기가 가능하면 커밋·푸시하거나 PR을 만들고 원격을 다시 확인한다.
- 로컬 OneDrive 복제본을 사용할 때는 시작 전에 `git pull`, 종료 전에 상태 확인과 `git push`를 수행한다.
- OneDrive 또는 GitHub 저장 완료는 실제 동기화·원격 내용을 확인한 경우에만 말한다.

## 9. 문서 변경 기록

- 2026-09-06: 원격 V1.11 코드와 매니페스트를 기준으로 최초 `PROJECT_STATE.md`를 생성하고 자동 인계 규칙을 추가했다.


## 10. V1.12 — STEP 전체 외곽 및 가공 전 프리뷰

### 확정 변경
- 정본 기준: 원격 main `e8b80728908481f4f4c760392c0a97528bc59241`.
- `step_component_projection`: 선택면 소속 바디의 투영 삼각형 합집합에서 외곽을 추출. 위쪽 수평면의 홀과 관통 투영 홀을 수집하며 양각 외곽은 절단선에서 제외.
- 같은 바디 중복 선택 제거, 다른 바디는 선택하지 않으면 제외. 기존 깊이 면 매칭은 같은 바디로 제한.
- 전체 두께와 Z0은 바디 최상단 기준. 가져오기 완료 시 사용자 안내. 양각 주변 면의 포켓 제거 경로는 미지원.
- `preflight_gcode`: 기본 OFF, 소재 상단 위 30mm, 1000mm/min, 사용자 높이/속도 설정 저장. START 후·절삭 전 활성 외곽 각각 1회 추종. 홀 전용 작업은 경계 사각형 추종.
- Top/Bottom 및 XY 원점, 비활성 윤곽, 분할 출력 유지. 높이는 안전 Z 이상, 속도는 양의 유한값이어야 함.
- 프리뷰 중 START의 스핀들·M8 상태 유지. 명목 윤곽만 추종하며 절삭거리/마모에는 프리뷰 이동 미포함. 예상 절삭시간은 프리뷰 시간을 포함하지 않음.
- Shapely 2.1.2 추가 및 PyInstaller 수집 설정.

### 검증
- Linux Python 3.12: 단위 검사 37개 통과, py_compile 및 git diff --check 통과.
- 사용자 첨부 STEP 로컬 검사: 양각 면 2곳과 낮은 면 각각 및 양각 2면 동시 선택에서 모두 외곽 1개·홀 14개·두께 1.6mm. 외곽 투영 크기 19×50.6mm.
- 사용자 원본 STEP와 화면, 생성 NC는 공개 저장소에 포함하지 않음.
- 합성 STEP 회귀: 양각/하부 면 선택 일치, 카운터보어 깊이 0.6mm, 회전·이동, 다른 바디 제외.
- 프리뷰 회귀: OFF, 절삭 전 1회, Top/Bottom 높이, XY 이동, 비활성 제외, 홀 전용 경계, 잘못된 높이/속도 차단.
- 이 Linux 환경에는 화면 서버가 없어 Windows GUI/EXE 실행 미검증. 실제 Mach3와 절삭도 미검증.

### 다음 작업
1. Windows 릴리스 workflow에서 기존 GUI 검사와 EXE 빌드 결과 확인.
2. 검증된 EXE의 자동 생성 매니페스트와 릴리스 일치 확인.
3. 실제 PC에서 STEP Z0을 바디 최상단으로 맞추고, 프리뷰 높이·XY 범위·기존 절삭경로 확인.
4. 실제 가공은 장비 공중 운전 이후 확인.

### V1.12 배포 확인 — 2026-09-19
- 소스 커밋: `0295bb68a2765b28decdf21b42242d6862c5f1f3`.
- Windows Actions 실행: https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35441438583
- Windows 단위 검사 37개와 기존 GUI smoke 검사 4회 통과, EXE 빌드 및 v1.12 릴리스 생성 완료.
- 원격 main 소스 blob과 로컬 수정본 hash 일치: `7f84d3ee1f8d7629f8cee7b7452f9051bab4fd17`.
- 원격 latest.json 버전 1.12 및 GitHub 릴리스 EXE 2개 자산 digest와 동일 SHA-256 확인: `e4b49b8c9901e71d6ab3e0c526259f35a5e831c3ac7b43bc3c3e8737120c88c5`.
- 릴리스: https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.12
- Windows GUI 검사는 Python 소스 기준이다. 패키징된 EXE의 실제 사용자 PC 실행, Mach3 공중 운전과 실제 절삭은 아직 미검증이다.
- 릴리스 ZIP의 상태 문서는 빌드 직전 기록이며, 이 main 문서에 배포 결과를 후속 기록했다.
- 남은 작업: 사용자 PC에서 새 EXE 실행, 소재 최상단 Z0 확인, 프리뷰 ON 및 실제 이동/가공경로 확인.

## 11. V1.13 — 양각 주변 아일랜드 포켓

### 확정 구현
- 기준 main: `a08b3f4e8d5ddb2739a19d4a8d32750fa5019ec7`.
- STEP 수평 단차 레벨과 상부 재료 투영 차집합으로 포켓 영역 인식. 양각 및 닫힌 아일랜드 보호. 관통 구멍만 있는 독립 영역은 포켓에서 제외.
- STEP 가져오기 옵션 기본 ON, 끄면 V1.12 방식의 프로파일만 가져오기. 포켓 목록에서 가공 포함 여부 선택.
- 오프셋 경로, 스텝오버 기본40%(1~50), 패스 깊이0.25mm, 정삭 여유0.1mm. 각 깊이에서 황삭 후 80% Feed 경계 정삭.
- 경로 간 안전 Z 후 XY 이동. 포켓 우선/얕은 순서. 기존 프로파일 수동 순번과 홀 우선 정책 유지.
- 배열·회전·이동·원점 변경에 보호 경계 동반 변환. Top/Bottom, 분할 NC 지원.
- 매 생성 시 공구 스윕이 보호 영역을 침범하지 않는지와 다른 부품 충돌 검사. 가져온 바닥 초과 깊이 차단.
- 청록 경로 미리보기, 잔여 면적 경고, NC 헤더 및 절삭거리 반영.

### 검증
- Linux Python3.12 단위 검사49개 통과, py_compile/git diff --check 통과.
- 공개 합성 형상: 닫힌/외곽 오픈 아일랜드, 스윕 보호, 단계별 깊이, 안전높이 연결, Top/Bottom, XY 원점, 배열/회전, 인접 부품 충돌, 깊이/설정 오류, 깊이순 및 옵션OFF.
- 사용자 STEP은 로컬 검사만 수행하고 도면/생성 NC를 공개 저장소에 포함하지 않음.
- BATT.step: 외곽1/홀14에 깊이0.5mm 포켓1 추가. Ø2mm 기준 황삭16경로+경계정삭1경로, 0.25mm씩2패스. 최종 공구 스윕이 양각을 침범하지 않음. 잔여 면적 약0.196mm2는 모서리/계산 안전 여유.
- Windows GUI 포켓 렌더/NC/설정 재시작 검사 추가. Windows 빌드·배포 결과는 후속 기록.

### 제한/미해결
- 수평바닥·수직벽 2.5D만 지원. 경사진 면이 있으면 포켓 ON 가져오기 중단, OFF 프로파일 가져오기 가능.
- 포켓 활성 상태에서는 공구 마모 보정 OFF 필수. 자동 잔삭, 헬리컬 진입, 연결 최적화 미구현.
- 수직 진입을 사용하므로 공구와 소재의 수직 절입 적합성 확인 필요.
- 반경으로 못 깎는 모서리와 수치 안전 여유 잔재는 경고. 완전 제거로 표시하지 않음.
- 실제 CNC 검증 전. 클램프·소재 바깥 여유 및 최상단 Z0을 확인해야 함.

### 다음 작업
1. Windows 단위/기존GUI/새포켓GUI 검사 후 EXE 빌드와 원격 릴리스 확인.
2. 사용자 PC에서 BATT.step을 포켓ON으로 다시 가져와 청록 경로/깊이 확인.
3. Mach3 공중 운전 후 시험 소재 가공과 단차/양각 치수 확인.

### V1.13 배포 확인 — 2026-09-19
- 소스 커밋 `67ab1051fa013bdf77f579d3eb8edce70120462a`, 매니페스트 커밋 `f2da16246e1cc3bc91481189a2e5df87733c002d`.
- Windows 실행 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35443282213 전체 성공.
- 단위49개, 새포켓GUI(청록 경로 렌더·NC·설정 저장/재시작), 기존GUI4회, EXE 빌드 및 릴리스 생성 통과.
- 원격/로컬 소스 blob 일치 `bb8e42f68a483412aaf26a3aa4a501ec1ae2b687`.
- V1.13 매니페스트 SHA-256와 릴리스 두 EXE digest 일치: `f46ac387c1379298367c819ad8a75067c33119c50d78ad3f7f94f21667ad0aca`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.13
- BATT 출력 NC 좌표(소수4자리) 기준 개별 경로 공구 스윕의 양각 침범면적0, 최저Z -0.5mm, 안전Z 아래 XY급속0 확인.
- GUI 검사는 Python소스 기준이며 실제 사용자 PC EXE 실행 및 Mach3/시험절삭은 미검증.
- 릴리스 ZIP 상태문서는 빌드 직전 기록이며 배포 완료 기록은 main 정본에 후속 반영.
- 다음 작업: 새 EXE에서 STEP 다시 가져오기(포켓ON), Z0 최상단/마모보정OFF/단차와 스텝다운 확인, 공중 운전 후 시험 가공.

## 12. V1.14 — 목록에서 가공 여부 적용/제외
- 기준 원격 main: `019582549f6adc8abf44ffea37fbb101f8366aae`.
- 윤곽 목록 `가공 여부` 열, 적용/제외 셀 편집 및 선택한 여러 행 일괄 변경. Ctrl/Shift 선택 동작 유지.
- `Contour.enabled` 변경이 기존 NC 필터와 작업 서명에 반영됨. 왼쪽 설정 동기화, 회색 제외 행과 재적용, Undo/Redo 지원.
- 공구경로 알고리즘 및 안전검사 제외 설정 변경 없음.
- Python 문법 및 diff 검사 완료. 기존 단위49개와 Windows 새 셀 편집 GUI 회귀는 배포 절차에서 확인.
- 다음 작업: Windows 단위/GUI 검사·EXE 빌드 후 릴리스/매니페스트 확인. 실제 PC에서 셀 클릭과 다중 제외 확인.

### V1.14 배포 확인 — 2026-09-19
- 소스 커밋 `4089621adac9365c8b5feaa93ec9738782a59ce7`, 매니페스트 커밋 `6410269fc22c45d38b757371b8f1b1305f5d5edc`.
- Windows 실행 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35444132158 전체 성공.
- 단위49개, GUI6회(새 가공 여부 셀/다중 선택/제외 NC/Undo·Redo·복원, 포켓, 기존 GUI), EXE 빌드 및 릴리스 생성 통과.
- 원격/로컬 소스 blob 일치 `b2f754eb7ea1e42f0589e7c07f68e5216c6f6882`.
- V1.14 매니페스트 SHA-256와 릴리스 두 EXE digest 일치: `b32e1b48297cc457d8931375a4eeeb807e4db3c70053f0d1785ce8aa33b1b061`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.14
- GUI 검사는 Python소스 기준. 실제 사용자 PC EXE 실행 및 Mach3/시험절삭은 미검증.
- 릴리스 ZIP 상태문서는 빌드 직전 기록이며 배포 완료 기록은 main 정본에 후속 반영.
- 다음 작업: 사용자 PC에서 가공 여부 셀의 적용/제외와 다중 선택 확인.

## 13. V1.15 — STEP 투영 수치 틈 수정 및 백신 배포 검사
- q20.step 원본 좌표는 성공, 37도 회전/원점 이동 시 MultiPolygon으로 분리되어 오류 재현. 분리 조각 간 거리0으로 계산되는 수치 경계 문제.
- connected_step_projection에서 1e-7mm 미세 closing, 둥근 조인으로 홀 보존, 대칭차 면적 제한 검증. 떨어진 큰 조각을 버리거나 최대 외곽만 선택하지 않음.
- 합성 회귀: 회전/이동 시 미세 틈과 홀 면적 보존, 실제 0.001mm 이상 틈 거부, 정상 형상 불변. 전체 단위53개 통과.
- 사용자 STEP 로컬 재현: 회전/이동 후 바디3개 가져오기 성공, 두께2mm, 외곽 면적 원본 일치. 고객 STEP/NC는 공개 저장소에 넣지 않음.
- V1.14 사용자 Defender 탐지명 Trojan:Win32/Sabsik.FL.A!ml. 오탐 여부와 정확한 원인 미확정, Microsoft 판정 제출은 수행하지 않음.
- V1.15부터 EXE 빌드 후 Defender 활성/시그니처 갱신/검사 성공 필수. 실패하면 신규 릴리스 및 매니페스트 갱신 차단.
- Windows/Defender/EXE 실사용 및 CNC 검증 결과는 후속 기록.

- 후속 캡처의 홀 간 긴 선/가느다란 삼각형 원인: 삼각형 union의 내부 수치 틈이 가짜 홀로 유입. 수평면은 mesh 경계 루프를 먼저 폴리곤화하고 mesh 면적 일치 검증 후 union하도록 변경.
- q20 좌표 이동 + 회전0/37도 모두 바디별 윤곽85/66/5개(외곽3, 내부153) 동일. 최소 내부 면적5.723mm2, 이전 수치 틈 윤곽 제거. 판 두께2mm.

### V1.15 배포 확인 — 2026-09-19
- 소스 커밋 `0399f5bac3f04cfab71f63839ab6e3cdda4ba4bb`, 매니페스트 커밋 `5ad0b590d5c5bdede9616ba27d962f7fb3ab5673`.
- Windows 실행 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35445128157 단위53개/GUI6회/EXE 빌드/릴리스 생성 성공. Defender 단계는 exit0이지만 로그에서 skipped 확인하여 검사 통과 취소.
- 원격/로컬 소스 blob 일치 `f03bfd835266105e4624350d1c137f99366fd031`.
- 릴리스 두 EXE와 latest.json SHA-256 일치: `f1a194abae02a76c83e04f3e17845f5ca75e02dd2cba73a9a95a68f3f6e83da1`.
- https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.15
- Defender 결과는 빌드 서버 검사 범위이며 사용자 PC의 클라우드/행위 탐지 해소 또는 V1.14 오탐 확정을 의미하지 않음.
- 다음 작업: 사용자 PC에서 V1.15 탐지 여부 확인, q20.step 다시 가져와 긴 선/가짜 홀 소멸 및 가공경로 확인. 실제 CNC 검증 전.

- Defender 검사 보정: GitHub runner의 빌드 경로에서 검사 skipped가 exit0으로 반환됨. 배포 EXE를 C:/CAM_Defender_Validation으로 복사하고 skipped/excluded 출력도 실패 처리. 백신 제외 설정은 변경하지 않음.
- V1.15 공개 EXE의 SHA-256를 고정한 독립 검증 workflow로 다시 검사. 결과 확인 전 백신 통과로 표시하지 않음.

### V1.15 Defender 재검사 완료
- https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35445342543 성공.
- GitHub 공개 릴리스 EXE를 다시 내려받고 SHA-256 일치 확인 후 C:/CAM_Defender_Validation에서 검사.
- 실제 로그: `Scanning C:\CAM_Defender_Validation\CFRP_Router_CAM_V1.15.exe found no threats.`
- 엔진4.18.26080.4, 시그니처1.459.287.0. 검사 전후 해시 일치, 백신 제외 설정 변경 없음.
- 사용자 PC 탐지 해소/클라우드·행위 검사 및 V1.14 오탐 여부는 여전히 미확인.

## 14. V1.16 — G코드 저장 완료 알림
- 일반 저장 파일의 with open 종료 후 저장 완료 팝업과 실제 파일 경로 표시. 취소/쓰기 실패는 성공 팝업에 도달하지 않음.
- 2분할 저장 기존 완료 안내 유지, 한국어/영어 번역 지원.
- Windows 회귀/GUI/EXE/Defender 검증 및 배포 결과 대기.

### V1.16 배포 확인
- 소스 커밋 `032085f4795455899229c6c1c00071c9222565b7`, 매니페스트 `be501f2feccd0aef8c2bbbe6f24156e564a6f516`.
- Windows https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35445829582 전체 성공. Linux/Windows 회귀53개, 기존 GUI6회, EXE 빌드 성공.
- Defender 별도 경로 실검사 로그 `found no threats` 확인. EXE 두 개와 매니페스트 SHA-256 일치 `871cf65ffc4fb3ed72711200331e69b508fe83c1978ada421fbdfb3390a99436`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.16
- 다음 작업: 사용자 PC에서 일반 NC 저장 후 알림창 확인. 실기 가공/사용자 PC 백신 판정은 미검증.

## 15. V1.17 — 급속 접근과 절입 분리
- 안전 Z는 횡이동, approach_z 기본1mm는 소재 윗면 기준 급속 하강 종료 높이. 이후 Plunge로 절입.
- TOP/BOTTOM, 프로파일/열린 경로/홀/포켓/다단/정삭에 적용. phase 첫 XY 전에도 안전 Z 상승 명시.
- 설정 저장/작업 서명/NC 헤더/절입 시간 추정 반영. 급속 시간은 기존과 같이 절삭 시간 추정에서 제외.
- Linux 단위59개 통과: 좌표 파싱으로 모든 XY 급속 높이, 급속 하강 종료 높이, G1 절입 직전 G0 접근, 설정 Plunge 확인. TOP/BOTTOM 및 포켓 반복/정삭/탭 포함.
- Windows GUI/EXE/Defender/릴리스 결과 대기. 실제 CNC 검증 전이며 NC 재생성 및 공중 운전 필요.

### V1.17 배포 확인
- 소스 `27be735d7ddbe3e10181f30890e56570e06a3c95`, 매니페스트 `296d24bcad00ed30309c07c01044f2ab4e03b322`.
- Windows https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35457278206 단위59개/GUI6회/EXE 빌드/Defender/릴리스 성공.
- 원격/로컬 소스 blob 일치 `57c7a60219331cfa4226a47bf57c41c313a74165`.
- Defender 실제 로그 `found no threats`, 매니페스트와 두 EXE SHA-256 일치 `ccacbc6f2882f32581be0ce3388d771933244b4d3c14172d5995eb24b0ca5c94`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.17
- 다음 작업: 사용자 PC에서 안전Z10/접근1로 NC 재생성 후 시뮬레이션·공중 운전 확인. 실제 CNC 검증 전.

## 16. V1.18 — 기본 안전 높이 자동 계산
- safe_z_auto 기본ON: 소재 윗면 기준 stock*2. stock 변경 trace와 load_settings 마지막 동기화로 표시 갱신. config/generate_gcode에서도 계산 보장.
- 급속 접근 기본1mm 유지. 자동 OFF이면 수동 안전 Z 유지. 설정 저장/작업 서명/NC 헤더 반영.
- TOP/BOTTOM stock1/2/3/5의 NC XY 높이, 수동 유지, 얇은 판의 접근 높이 충돌 검증 추가.
- Windows GUI에 두께 변경/자동·수동 전환/설정 복원 검사 추가. Windows/백신/릴리스 결과 대기.
- 다음 작업: 검사·배포 후 사용자 PC NC 재생성과 공중운전. 실가공 미검증.

### V1.18 배포 확인
- 소스 커밋 `ad94755fabdd6b41b68fc4fda47ff38fa8f53ea2`.
- Windows https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35457727158 전체 성공. 단위62개, GUI6회(안전Z 자동/수동/설정복원 포함), EXE 빌드 성공.
- Defender 실검사 `found no threats` 확인. 매니페스트1.18 및 두 EXE SHA-256 일치 `493d44ec3e271a84c7e4c4bc9e1884960e24b2731f1c8450de49ce0be38b6c1d`.
- 소스 blob `f262eb34f28e9e01429895674385ea713d633928`, 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.18
- v1.11~v1.18 릴리스별 EXE와 소스 ZIP 존재 확인. 최신 자동 업데이트1.18.
- 다음 작업: 사용자 PC에서 두께3mm/BOTTOM 안전Z9·접근Z4 확인 후 공중 운전. 실가공 검증 전.

## 17. V1.19 — 가공 기본값/선분 축소/포켓 연속
- wall_finish/onion_skin_enabled 기본OFF와 기존<=1.18 설정의 1회 OFF 전환. 새 버전 명시 선택은 유지.
- path_tolerance 기본.02mm/0~.1mm. 일정Z 구간을 Douglas-Peucker 단순화하되 10도 이상 코너/탭Z변화 보존. 원호 신규복원은 아님. 포켓은 공구스윕/잔삭검증 통과하는 단순화만 채택.
- pocket_stay_down 기본ON. 이전 경로의 정/역방향 기가공 구간 또는 직접 연결을 비교해 짧은 경로 선택. 인접 스텝오버 및 기가공영역 제약/양각 보호/타부품 공구스윕 검증. 다음층도 기가공영역 통과 가능한 경우만 연속절입.
- 회귀69개 통과. dense 원형360선분→104선분, 최대 경로편차.02mm 범위 검사. 코너/탭/설정이관/분리포켓/실제 NC 좌표 공구스윕/연속깊이 검사 포함.
- 로컬 BATT STEP 포켓 예: G0 Z 명령71→11, stay-down 연결30회. 단순 이동 시뮬레이션은279.4→295.2초로 증가(기가공 구간 G1 재이동 영향). 실제 가감속과 CV 미반영이므로 실가공 속도 개선을 단정하지 않음.
- Mach3 공식 CV 설명 확인: https://www.machsupport.com/wp-content/uploads/2013/02/Mach3_CVSettings_v2.pdf . 실제 사용자 Mach3 설정/모션컨트롤러 미확인, CV값/가감속 변경하지 않음.
- 고객 STEP/NC 비공개 유지. Windows GUI/EXE/Defender/릴리스 결과 대기. 이후 사용자 NC 재생성·공중운전/실기 비교 필요.

### V1.19 배포 확인 — 2026-09-20
- 소스 `9a513cac7ffc102600062833c689d4a96435a237`, 매니페스트 `e8e1403ca45eeea65ce0c6572c2daca94c4e42b0`.
- Windows https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35484017539 단위69개/GUI6회/EXE 빌드/Defender/릴리스 성공.
- 원격/로컬 소스 blob `a82a3b285f3b8d4776b89c2011046438047c921c` 일치.
- Defender `found no threats`, 두 EXE와 latest.json SHA-256 일치 `af335a6206e346c6a1469e4f2c0a92423d81adbf6f8dbb08fd743ab6f74f0a6b`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.19
- 다음 작업: NC 재생성 후 3D 연결/탭/양각 검사와 공중 운전, 사용자 Mach3 CV·LookAhead·가감속 설정 확인. 실가공 및 사용자 PC 백신 판정은 미확인.

## 18. V1.20 — 경로 허용오차 기본0.01mm
- UI/NC fallback 기본0.01mm. V1.19 이하 저장값0.02만 0.01로 전환, 기타 지정값과 V1.20 설정 유지.
- Linux/Windows 회귀70개 및 Windows GUI6회 통과, EXE 빌드와 릴리스 완료. 실제 CNC 검증 전.
- Windows 실행 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35484827795
- Defender 실검사 found no threats. 두 EXE와 latest.json SHA-256 일치: `0c26d5a79c77c9fed99ee88ca934c272c75fa9b8eab6bbfb774d9321185e271f`.
- 원격/로컬 소스 blob 일치: `db088b684ff33cb44253ed162f8e2d0a3f2ee47c`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.20
- 다음 작업: 사용자 PC에서 0.01mm 확인 후 NC 재생성 및 시뮬레이션/공중 운전. 사용자 PC 백신 판정과 실가공 미검증.

## 19. V1.21 — 3D 표시 캐시·공구거리 보호
- 깊이맵/공구경로와 급속선 표시 전환은 Tkinter Canvas 경로를 재사용하고 카메라·확대·이동·창 크기 변경 시에만 다시 투영한다.
- 마모 입력을 `10m당 지름 감소량`으로 변경하고 실측값 기반 기본값 `0.079mm/10m`를 적용했다. 기존 100m당 사용자 지정값은 자동 변환한다.
- 예상 절삭거리 8m 이상은 확인 경고, 10m 이상은 G-code 생성 차단. PART1·PART2는 각 파일 START G-code에서 새 공구를 쓰는 조건으로 따로 판정한다.
- 기존 누적거리·누적시간 입력을 제거하고 분할 파일명에는 각 파트 예상시간을 표시한다.
- 로컬 Windows 회귀78개, GUI6회, py_compile, diff 검사와 EXE 빌드 성공.
- GitHub Actions https://github.com/wofidkr57-jpg/CFRP-Router-CAM/actions/runs/35690423548 에서 Windows 회귀78개·GUI6회·빌드·Defender `found no threats`·릴리스 성공.
- 두 릴리스 EXE와 `latest.json` SHA-256 일치: `fc52d8703d9a7d7bc3ef44cc7a895c30c70e1cab7b4698bda10c6adfac175a5b`. 공개 EXE 재다운로드 해시도 일치. 소스 ZIP SHA-256 `4337ab68c9206ca487d217aa30d12a8ff29796761843217d59e9a80d38c960e3`.
- 릴리스 https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/tag/v1.21
- 실제 CNC·소재 절삭은 미검증. 사용자 PC에서 자동 업데이트 후 경고/차단 창, 생성 NC, 시뮬레이션과 공중 운전을 확인한다.
