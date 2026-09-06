# AGENTS.md

## 적용 범위

이 지침은 `CFRP-Router-CAM` 저장소 전체에 적용한다. 이 저장소는 사용자가 이미 공개 저장소로 운영 중이다.

## 작업 시작

1. 이 파일과 `PROJECT_STATE.md`를 먼저 읽는다.
2. `git status`, 현재 브랜치, 원격 주소, 최근 커밋과 릴리스 버전을 확인한다.
3. 사용자 변경을 덮어쓰지 않고, 다른 CAM·지그 프로젝트의 파일이나 상태를 섞지 않는다.
4. `PROJECT_STATE.md`가 없으면 실제 코드와 저장소 상태를 조사해 즉시 생성한다.

## 정본

- 애플리케이션 코드 정본은 `cfrp_router_cam.py` 한 파일이다.
- 변경 이력은 `CHANGELOG.md`, 빌드 환경은 `requirements.txt`와 `build_windows.ps1`, 작업 인계 상태는 `PROJECT_STATE.md`가 정본이다.
- 긴 코드와 로그는 파일로 유지하고 채팅에는 변경 요청, 에러 로그, 지시사항과 짧은 결과만 남긴다.
- 버전 배포 시 `APP_VERSION`, README의 최신 버전, CHANGELOG, `latest.json`, 릴리스 태그·파일을 서로 일치시킨다.

## 자동 저장과 인계

- 의미 있는 코드·설정·문서 변경은 사용자가 따로 “저장”이라고 말하지 않아도 실제 파일에 반영한다.
- 변경 뒤 `PROJECT_STATE.md`에 변경 내용, 검증 결과, 미해결 항목과 다음 작업을 갱신한다.
- GitHub가 연결되어 있고 쓰기 가능하면 현재 작업 방식에 맞춰 커밋·푸시하거나 PR을 만든다.
- 원격 내용을 다시 확인하기 전에는 GitHub에 저장됐다고 단정하지 않는다.
- 쓰기 권한이나 저장소 연결이 없으면 막힌 지점을 알리고 적용 가능한 패치나 상태 파일을 남긴다.

## 공개 저장소와 보안

- 현재 공개 상태는 의도된 것으로 취급하되, 가시성 변경은 별도 지시 없이는 수행하지 않는다.
- 인증정보, 개인 경로, 개인 `settings.json`, NC 작업물, 고객 도면, 빌드 임시파일과 무관한 바이너리를 커밋하지 않는다.
- 배포 EXE와 해시는 검증된 릴리스 절차로만 갱신한다.

## CNC 안전

- 원점, Z 방향, 공구 지름/보정, 가공 순서, 탭, 마모 보정, 포스트프로세서 변경은 고위험 변경으로 취급한다.
- 생성 G-code의 헤더·경로·종료 코드를 검토하고 시뮬레이션과 공중 드라이런을 권고한다.
- 실제 장비에서 검증하지 않았으면 실가공 검증 완료라고 쓰지 않는다.

## 조사 원칙

- 사용자가 요청하지 않으면 한국/한국어 유튜브와 해외직구·해외배송·구매대행·글로벌 마켓 판매처를 제외한다.
- 일반론보다 같은 제품·버전·증상의 실제 사례를 우선한다.
- 공개 펌웨어나 소스가 있으면 저장소, 버전/커밋, 파일 경로와 함수·상수·조건문을 확인하고 사실과 추론을 구분한다.

## 검증

코드 변경 뒤 가능한 범위에서 다음을 실행한다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s verification -p "test_*.py" -v
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py ko
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py en
.\.venv\Scripts\python.exe verification/gui_smoke_v110_first_run.py close
.\.venv\Scripts\python.exe verification/gui_smoke_v108.py
.\build_windows.ps1
```

실행하지 못한 Windows GUI, EXE 빌드, Mach3 또는 실제 장비 검증은 미검증으로 기록한다.
