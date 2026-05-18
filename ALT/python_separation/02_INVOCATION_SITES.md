# 02. Python 호출 자바 코드 상세 — 5개 배치

> 각 호출 위치의 정확한 라인, 입력 CSV, 호출 파라미터, 출력 처리, 분리 시 영향을 정리.

---

## 0. 호출처 5개 한눈에

| # | 배치 | 호출 패턴 | Python 스크립트 | 입력 (CSV) | 출력 적재 |
|---:|---|---|---|---|---|
| 1 | `AmosMinBatch._predictor_atlas_hid` | ProcessBuilder 직접 | `deadlock_hub.py` | `python/atlas_hid/data/atlas_hid_inout_data_output.csv` | `M16A_BOTTLENECK_ANOMALY` |
| 2 | `AmosMinBatch._predictor_star_idc` | ProcessBuilder 직접 | `standard_detector.py` | `python/star_idc/data/star_idc_inout_data_output.csv` | `M14A_QUEUE_ANOMALY` |
| 3 | `AmosMinBatch._predictor_star_event` | ProcessBuilder 직접 (인자 `-o ./output`) | `3DO_PRETIME_TEST3.py` | `python/star_event/data/star_event_inout_data_output.csv` | (test 흔적, 활성 미확정) |
| 4 | `AmosBoundryBatch._predictor_star_idc_data` | ProcessBuilder 직접 (stdout 미읽음) | `boundary_batch.py` | (선행 작업) | (없음 — 파일 생성용?) |
| 5 | `HubroomTransPredictBatch._predictor` | `PythonUtil.executeWithParam(file, false, errorVhlState, errorAddData)` | **동적** `pyInfoList` (`HUB_ROOM_*.py`) | `python/HUBROOM_PIVOT_DATA.csv` | `test_hubroom_predict` |
| 6 | `QTransferPredictBatch._predictor` | `PythonUtil.executeWithParam(file, false)` | **동적** `pyInfoList` (default `Q_TRANSFER_PREDICTOR_10m.py`) | (Logpresso 직접 조회) | `ATLAS_TS_PREDICT` |
| 7 | `ServerResourceApmBatch` | `PythonUtil.executeWithParam("SERVER_RESOURCE_MODEL.py", false, outputRangeStr)` | `SERVER_RESOURCE_MODEL.py` | `python/data/APMWEEKDATA.csv` | `server_resource_predict` |

---

## 1. `AmosMinBatch.java`

**전체 라인:** 1213 / **Python 호출:** 3 군데

### 1.1 상수 (라인 40-45)

```java
private static final String FILE_PATH_ATLAS_HID   = FilePathUtil.PYTHON_FILE_PATH + "/atlas_hid/";
private static final String FILE_NAME_ATLAS_HID   = "data/atlas_hid_inout_data_output%s.csv";
private static final String FILE_PATH_STAR_IDC    = FilePathUtil.PYTHON_FILE_PATH + "/star_idc/";
private static final String FILE_NAME_STAR_IDC    = "data/star_idc_inout_data_output%s.csv";
private static final String FILE_PATH_STAR_EVENT  = FilePathUtil.PYTHON_FILE_PATH + "/star_event/";
private static final String FILE_NAME_STAR_EVENT  = "data/star_event_inout_data_output%s.csv";
```

### 1.2 `_predictor_atlas_hid()` (라인 ~395)

**선행:** `_create_atlas_hid_input_data("M16A", from, to)` 가
`{FAB}_ATLAS_HID_INOUT` 조회 → CSV 생성 (header `EVENT_DT, HID_1_FROM_SUM, ..., HID_N_FROM_SUM`)

**호출 (라인 406-432):**
```java
String pyFileName = "deadlock_hub.py";
File workingDir = new File(FILE_PATH_ATLAS_HID);   // python/atlas_hid/
command.add("python");
command.add(pyFileName);
ProcessBuilder processBuilder = new ProcessBuilder(command);
processBuilder.directory(workingDir);              // ★ 작업 디렉토리 설정
processBuilder.redirectErrorStream(stderrFlag);    // false
process = processBuilder.start();
```

⚠ `PythonUtil` 미사용 이유 = **working directory 설정 필요** (`processBuilder.directory(workingDir)`).
Python 스크립트가 자기 디렉토리의 `app` 모듈을 import 하기 때문 (주석 라인 417-418 명시).

**stdout 파싱 (라인 428-477):**
- JSON Array 안에 **JSON Array 가 2개** 들어있는 구조
  - 첫번째 Array → `features_data` (현재 코드에선 주석 처리, 사용 안 함)
  - 두번째 Array → `anomaly_data` (적재 대상)
- `num++` 카운터로 분기

```python
# Python 측 출력 예시
[
  [ {features1}, {features2}, ... ],   # 1번째: features (저장 안 함)
  [ {anomaly1}, {anomaly2}, ... ]      # 2번째: anomaly_data → DB 적재
]
```

**오류 처리 (라인 482-495):** exitCode != 0 이면 stderr 읽어서 로깅.

**적재 (라인 543):**
```java
LogpressoAPI.setInsertTuples("M16A_BOTTLENECK_ANOMALY", tuples, 10);
```

⚠ **`M16A`** 하드코딩 — `_create_atlas_hid_input_data("M16A", ...)` 도 동일.

---

### 1.3 `_predictor_star_idc()` (라인 ~835)

**선행:** `_create_star_idc_input_data(...)` 가 CSV 생성.

**호출 (라인 846-870):**
```java
String pyFileName = "standard_detector.py";
File workingDir = new File(FILE_PATH_STAR_IDC);    // python/star_idc/
// 이하 _predictor_atlas_hid 와 동일 패턴
```

**파싱 동일** (2-array 패턴) → `anomaly_data` 만 사용.
단, 이쪽은 `isJsonObject` 도 처리 (단일 객체 fallback).

**적재 (라인 974):**
```java
Util.insertInLogpressoDatabase(tuples, "M14A_QUEUE_ANOMALY", this.getClass().getSimpleName());
```

⚠ **`M14A`** 하드코딩.

---

### 1.4 `_predictor_star_event()` (라인 ~1100)

**선행:** `_create_star_event_input_data(...)` 가 CSV 생성.

**호출 (라인 1113-1145):**
```java
String pyFileName = "3DO_PRETIME_TEST3.py";
File workingDir = new File(FILE_PATH_STAR_EVENT);  // python/star_event/
command.add("python");
command.add(pyFileName);
command.add(file.getAbsolutePath());               // ← 입력 CSV 절대경로
command.add("-o");
command.add("./output");                           // ← 출력 디렉토리
```

→ **명령행 인자 3개 추가** (`csv-path`, `-o`, `./output`).

**적재:** (test_* 적재 코드가 모두 주석 처리, 라인 950-982) — 현재는 결과 사용 안 함으로 보임. **검토 필요**.

---

## 2. `AmosBoundryBatch.java`

**전체 라인:** 542 / **Python 호출:** 1

### 2.1 상수 (라인 38)

```java
private static final String FILE_PATH_STAR_IDC = FilePathUtil.PYTHON_FILE_PATH + "/star_idc/";
```

### 2.2 `_predictor_star_idc_data()` (라인 495-548)

```java
String pyFileName = "boundary_batch.py";
File workingDir = new File(FILE_PATH_STAR_IDC);
command.add("python");
command.add(pyFileName);
ProcessBuilder processBuilder = new ProcessBuilder(command);
processBuilder.directory(workingDir);
processBuilder.redirectErrorStream(stderrFlag);
process = processBuilder.start();

int exitCode = process.waitFor();
// ⚠ stdout 읽지 않음. exitCode 만 확인.
```

⚠ **이 호출은 결과를 stdout 으로 받지 않음**. Python 측이 자체적으로 파일/DB 에 결과를 쓰는 fire-and-forget 패턴으로 보임. → 분리 시 별도 응답 규약 필요.

---

## 3. `HubroomTransPredictBatch.java`

**전체 라인:** 308 / **Python 호출:** N개 (`pyInfoList` 만큼)

### 3.1 선행: `_createInputData()` (라인 ~117)

`HUB_ROOM_INPUT_DATA` 쿼리 → CSV → `HUBROOM_PIVOT_DATA.csv` 저장 (`folderPath = FilePathUtil.PYTHON_FILE_PATH`).

### 3.2 `_preparePredictor()` (라인 179-)

XML/properties 에서 동적 `pyInfoList: List<Map<String,String>>` 구성:
```java
map.put("FILE_NM", fileName);   // 예: HUB_ROOM_MODEL_001.py
map.put("FLOW",    flowName);   // 예: M14A.BB
```
→ **모델 파일이 정해진 게 아니라 설정/DB 로부터 옴**. 모델 추가/교체 시 자바 변경 없이 됨.

### 3.3 `_predictor()` 호출부 (라인 244-260)

```java
for (Map<String, String> info : pyInfoList) {
    String fileName = info.get("FILE_NM");
    String flowName = info.get("FLOW");

    List<Map<String, Object>> prediction = PythonUtil.executeWithParam(
            fileName,
            false,
            errorVhlState,   // ← env 변수 (VHL_OFF 여부)
            errorAddData     // ← XmlUtil.getVariableEnv("VHL_OFF_PLUS_DATA")
    );

    if (prediction == null) {
        // NO MODEL — 파일 없음
    } else {
        result.addAll(_validWarnYN(prediction, flowName, fileName));
    }
}
```

**파라미터 의미:**
| 순서 | 인자 | 출처 |
|---|---|---|
| 1 | fileName | `pyInfoList[i].FILE_NM` |
| 2 | stderrFlag | `false` |
| 3 | errorVhlState | "0"/"1" (VHL_OFF 발생 여부) |
| 4 | errorAddData | `XmlUtil.getVariableEnv("VHL_OFF_PLUS_DATA")` (default "30") |

**적재:** 라인 ~94 (`_validWarnYN` 후) →
```java
Util.insertInLogpressoDatabase(logpressoData, "test_hubroom_predict", ...);
```

⚠ 테이블 이름이 `test_*` — 운영 테이블인지 확인 필요.

---

## 4. `QTransferPredictBatch.java`

**전체 라인:** 1774 / **Python 호출:** N개 (`pyInfoList` 만큼)

### 4.1 `_selectDisplayedPrediction()` (라인 277-)

`XmlUtil.getVariableEnv("Q_TRANSFER_MODEL_MAPPER_DEFAULT")` 가
유효하면 그 값, 아니면 default `"Q_TRANSFER_PREDICTOR_10m.py"`.

### 4.2 `_predictor()` 호출부 (라인 ~308)

```java
for (Map<String, String> info : pyInfoList) {
    String fileName = info.get("FILE_NM");
    List<Map<String, Object>> prediction =
            PythonUtil.executeWithParam(fileName, false);   // ← 추가 인자 없음

    if (prediction == null) {
        predictionMap.put(fileName, new ArrayList<>());
    } else {
        predictionMap.put(fileName, prediction);
    }
}

List<Tuple> logpressoData = _buildLogpressoDataWithPrediction(predictionMap);
Util.insertInLogpressoDatabase(logpressoData, "ATLAS_TS_PREDICT", ...);
```

→ **모델 인자 없음** (`stderrFlag=false` 외에 추가 파라미터 없음).
Python 측이 자체적으로 Logpresso/MongoDB 조회해서 입력 가져옴.

---

## 5. `ServerResourceApmBatch.java`

**전체 라인:** 539 / **Python 호출:** 1

### 5.1 선행: CSV 생성 (라인 ~330-360)

`server_resource_apm` 테이블 조회 → `python/data/APMWEEKDATA.csv` 생성.

### 5.2 호출 (라인 369)

```java
String outputRangeStr = XmlUtil.getVariableEnv("APM_PREDICT_OUTPUT_RANGE", null);
if (outputRangeStr.contains("Unknown ALARM CODE")) {
    outputRangeStr = "7";    // ← default
}

List<Map<String, Object>> result =
        PythonUtil.executeWithParam("SERVER_RESOURCE_MODEL.py", false, outputRangeStr);
```

**파라미터:** `outputRangeStr` (default "7") = 며칠치 예측?

### 5.3 적재 (라인 381)

```java
LogpressoAPI.setInsertTuples("server_resource_predict", predictList, 15);
```

---

## 6. 호출 패턴 비교 표

| 항목 | AmosMin (×3) | AmosBoundry | Hubroom | QTransfer | ServerResource |
|---|---|---|---|---|---|
| 호출 방식 | ProcessBuilder | ProcessBuilder | PythonUtil | PythonUtil | PythonUtil |
| working dir 설정 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 입력 CSV | ✅ (사전 생성) | ✅ | ✅ | ❌ (Python 이 직접) | ✅ |
| stdout 읽음 | ✅ | ❌ | ✅ | ✅ | ✅ |
| stderr 분리 읽음 | ✅ (exitCode!=0 시) | ✅ | ❌ | ❌ | ❌ |
| Python 인자 | 0~3 | 0 | 2 (errorVhlState, errorAddData) | 0 | 1 (outputRangeStr) |
| 출력 구조 | 2중 Array (features+anomaly) | none | 1중 Array | 1중 Array | 1중 Array |
| 결과 적재 | M16A/M14A 하드코딩 | none | test_hubroom_predict | ATLAS_TS_PREDICT | server_resource_predict |
| 모델 동적 선택 | ❌ | ❌ | ✅ (pyInfoList) | ✅ (pyInfoList) | ❌ |

---

## 7. 분리 시 자바 측 변경 위치 요약

| 파일 | 변경 부분 | 새 동작 |
|---|---|---|
| `util/PythonUtil.java` | 전체 메서드 본체 | HTTP/gRPC 호출로 교체. 시그니처 유지 |
| `util/FilePathUtil.java` | `PYTHON_FILE_PATH` 사용처 | 더 이상 로컬 디렉토리 의존 없음. 단, CSV 임시 파일은 당분간 유지 가능 |
| `AmosMinBatch.java` 3곳 (라인 406, 848, 1113) | `ProcessBuilder` 블록 → `PythonUtil.executeWithParam` 호출 | working dir 개념을 endpoint path 로 치환 |
| `AmosBoundryBatch.java` 라인 506 | 동일 | fire-and-forget → POST 후 응답 무시 |
| `HubroomTransPredictBatch.java` 라인 249 | 변경 불필요 (이미 PythonUtil 사용) | URL 매핑만 |
| `QTransferPredictBatch.java` 라인 311 | 변경 불필요 | URL 매핑만 |
| `ServerResourceApmBatch.java` 라인 369 | 변경 불필요 | URL 매핑만 |

→ **`PythonUtil` 을 어댑터로 만들면 호출처 코드는 거의 무변경.**

---

*다음: [03_SCRIPTS_INVENTORY.md](03_SCRIPTS_INVENTORY.md) — Python 스크립트 파일 인벤토리*
