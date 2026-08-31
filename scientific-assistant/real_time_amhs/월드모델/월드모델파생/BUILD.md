# OHT 월드모델파생 — Windows .exe 빌드

## 빌드 절차

### 1. 사전 준비
- Python 3.10+ 설치 (PATH 등록)
- `build.bat` 와 같은 폴더에서 작업

### 2. 빌드
```cmd
build.bat
```
의존성 자동 설치 → PyInstaller 실행 → `dist\oht_world.exe` 생성.

(약 1~3분 소요. 최초 1회만.)

### 3. 배포 폴더 구성
빌드된 `dist\oht_world.exe` 를 운영 폴더로 옮긴 뒤 다음 구조로 둡니다.

```
배포폴더\
├── oht_world.exe              ← 빌드 결과물 (단일 EXE)
└── OHT_MAP\                   ← 사용자 데이터 (수동 배치)
    └── MAP\
        ├── M14A\A.layout.zip
        ├── M16A\BR.layout.zip
        └── ...
```

`_logpresso_cache\` 는 실행 중 자동 생성, 종료 시 자동 삭제됩니다.

### 4. 실행
```cmd
oht_world.exe
```
콘솔 창이 뜨면 `http://localhost:10005` 로 접속.

종료는 콘솔에서 Ctrl+C.

---

## 파일 역할

| 파일 | 역할 |
|---|---|
| `build.bat` | 윈도우용 빌드 진입점 |
| `oht_world.spec` | PyInstaller 빌드 설정 |
| `app_paths.py` | frozen/개발 모드 경로 자동 처리 |
| `main.py` 등 | 앱 본체 (변경 없이 그대로 빌드됨) |

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `pyinstaller: not found` | PyInstaller 미설치 | `pip install pyinstaller` |
| `Failed to fetch /api/fabs` | OHT_MAP 폴더가 exe 옆에 없음 | exe와 같은 폴더에 OHT_MAP 복사 |
| 첫 실행이 느림 | _MEIPASS 임시 추출 | 정상. 2번째부터 빠름 |
| 백신이 차단 | PyInstaller 산출물 흔한 false positive | 신뢰 목록 등록 |
