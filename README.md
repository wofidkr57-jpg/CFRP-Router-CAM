# CFRP Router CAM

Mach3용 CFRP 2D/2.5D CAM 프로그램의 공식 배포 및 업데이트 저장소입니다.

## 최신 버전 다운로드

[CFRP_Router_CAM.exe](https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/latest/download/CFRP_Router_CAM.exe)

현재 최신 버전은 **V1.10**입니다.

- 설정 파일 없는 첫 실행에서 언어 선택창이 숨는 문제 수정
- NC 파일명에 판재 두께 추가: `260831_2.0endmill_T3.0_panel_12_35min.nc`
- 두 파일로 나누면 `..._PART1.nc`, `..._PART2.nc`로 저장
- 여러 원본 파일을 불러오면 원본 이름 대신 `multi` 사용
- 실제 Python 소스, 검사 코드, Windows 빌드 방법을 저장소와 릴리스에 포함

한국어/영어 UI, NC 영문 전체 가공조건 헤더, 탭 설정 버튼 배치는 유지됩니다.

V1.07부터 프로그램을 시작할 때 새 버전을 확인합니다. 사용자가 업데이트를 승인하면 새 EXE를 내려받아 SHA-256을 검증하고, 기존 프로그램 종료 후 실행 파일을 자동으로 교체합니다. 다운로드나 검증에 실패하면 기존 EXE는 변경하지 않습니다.

## 설정과 최초 실행

설정 또는 언어 선택이 없으면 첫 실행에 한국어/English 선택창이 표시됩니다. 선택 후 메인 화면이 열리고, `settings.json`이 EXE 옆에 자동 저장됩니다. 쓰기 권한이 없으면 기존 방식대로 AppData의 `CFRP_Router_CAM` 폴더를 사용합니다. 기존 `settings.json`은 업데이트해도 보존됩니다. 관리자 권한은 필요하지 않습니다.

## 소스 코드

- [소스 코드](cfrp_router_cam.py)
- [V1.10 소스 패키지](https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/download/v1.10/CFRP_Router_CAM_V1.10_source.zip)
- GitHub의 **Code → Download ZIP** 또는 릴리스의 **Source code**에도 실제 소스가 포함됩니다.

Windows Python 3.12 (Tkinter 포함)에서 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe cfrp_router_cam.py
```

검사 및 EXE 빌드:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s verification -p "test_*.py" -v
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py ko
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py en
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py close
.\.venv\Scripts\python.exe verification/gui_smoke_v108.py
.\build_windows.ps1
```

빌드 결과는 `dist/CFRP_Router_CAM.exe`입니다. GUI 검사는 잠깐 테스트 창을 띄우고 자동으로 닫습니다. 배포용 ZIP에는 개인 `settings.json`, NC 작업물, 인증정보를 넣지 않습니다.

버전별 변경 내역은 [CHANGELOG.md](CHANGELOG.md)를 참고하세요.

## 주의

CNC에서 사용하기 전에 생성된 G-code, 작업 원점, Z 방향과 공구경로를 확인하고 공중 드라이런을 진행하세요.
