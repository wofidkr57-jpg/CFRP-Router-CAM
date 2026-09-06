# CFRP Router CAM 프로젝트 상태

- 기준일: 2026-09-06
- 저장소: `wofidkr57-jpg/CFRP-Router-CAM`
- 공개 범위: **공개 저장소(기존 운영 상태 유지)**
- 기본 브랜치: `main`
- 현재 애플리케이션 버전: **V1.11**
- V1.11 코드 기준 커밋: `75df745841c890911ac94e945b7f77b8cd94f6fe`
- V1.11 업데이트 매니페스트 기준 커밋: `4ad0c9e44d3fad34305d36e58947cce873c36df5`
- 이 문서는 클라우드 채팅과 여러 로컬 PC가 같은 작업 상태를 이어받기 위한 정본이다.

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
