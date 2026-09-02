# 집에서 GGUF 로 돌리기

집은 **GPU 한 장**이다. 앱마다 llama-cpp 로 모델을 올리면 같은 모델이 VRAM 에
두 벌 세 벌 올라가서 결국 아무것도 안 뜬다.

그래서 **모델은 한 곳만 올린다.**

```
        [ app.py ]  ← GGUF 를 여기서만 올린다 (llama-cpp-python)
            │
            ├── 데모스        (같은 프로세스)
            ├── UIO           (같은 프로세스 · /uio)
            ├── 코딩어시스턴트 (같은 프로세스 · /code/)
            │
            └── /v1/*  ← OpenAI 호환 문
                    │
                    └── 아바타 (avatar_2d, 다른 프로세스)
```

## 1. GGUF 파일 두기

`app.py` 옆이나 `models/` 폴더에 `*.gguf` 를 둔다. (`*mmproj*.gguf` 는 비전
프로젝션이라 모델 목록에서 자동으로 빠진다.)

## 2. 띄우기

```
python app.py
```

부팅 로그에 이렇게 나오면 된다.

```
  💻 GGUF 자동 감지! (2개 모델)
     [gguf-0] Qwen3-14B-Q4_K_M.gguf (9.0 GB)
     [gguf-1] gemma-3-12b.gguf (7.3 GB)
     ✅ 기본 모델 로드 완료: Qwen3-14B-Q4_K_M.gguf
  🔌 GGUF OpenAI 호환 라우트 등록 완료 (/v1/models · /v1/chat/completions)
```

- 데모스 → http://localhost:10009
- UIO → http://localhost:10009/uio
- 코딩어시스턴트 → http://localhost:10009/code/

셋 다 **같은 모델 한 벌**을 쓴다. VRAM 은 한 번만 든다.

## 3. 아바타 붙이기

아바타는 다른 프로세스다. `--gguf` 만 주면 된다.

```
cd real_time_amhs/avatar_2d
python run.py --gguf
```

- 토큰이 필요 없다 (`token.txt` 없어도 뜬다)
- 주소는 기본 `http://127.0.0.1:10009` — 다른 PC 에 있으면
  `python run.py --gguf http://192.168.0.20:10009`
- 실행하면 `/v1/models` 로 GGUF 목록을 받아서 고르게 해 준다

회사에서는 지금까지대로 `python run.py` 하면 된다 (토큰 요구도 그대로).

## 왜 이렇게 했나

- **아바타는 원래 OpenAI 호환 게이트웨이만 말할 줄 안다.** 그래서 아바타에
  llama-cpp 를 심지 않고, 이미 모델을 든 쪽에 **문만 열었다**. 아바타 코드는
  주소가 바뀐 것 말고 달라진 게 없다.
- **빈 토큰을 보내지 않는다.** 예전엔 `Authorization: Bearer ` 를 늘 붙였는데,
  로컬 서버는 그걸 보고 401 을 내기도 한다 — 붙을 수 있는 것을 못 붙는다.
- **response_format 을 한 계단씩 낮춘다.** 아바타는 감정·모션 enum 까지 박은
  `json_schema` 로 보낸다. llama-cpp 빌드마다 아는 모양이 달라서, 모르면
  `json_object`+schema → `json_object` → 없음 순으로 낮춘다. 바로 버리면
  JSON 보장이 통째로 날아가서 본문에서 답을 긁어내야 한다.
- **한 번에 하나만 생성한다.** llama.cpp 모델 객체는 스레드 안전하지 않다.
  두 요청이 겹치면 토큰이 섞이거나 프로세스가 죽는다.

## UIO 에서 달라진 것

에이전트(최·이·서·김·박·윤·정·CEO)는 원래 **API 모델만** 쓰게 막혀 있었다.
집에는 API 모델이 하나도 없어서 전부 `auto` 로 떨어졌다 — 모델 고르는 칸이
죽은 것처럼 보였다.

이제 **API 모델이 하나도 없을 때만** GGUF 를 쓴다. 회사에서는 지금까지와
똑같다 (GGUF 는 여전히 에이전트 목록에서 빠진다).

## 고친 뒤 확인

```
python gguf_연결확인.py
```

GPU 도 모델 파일도 서버도 없이, **우리가 쓴 코드끼리 말이 통하는지**만
1초에 확인한다. llama-cpp 빌드 세 가지(json_schema 아는 것 / json_object 만
아는 것 / 아예 모르는 것)를 흉내 내서, 어느 쪽이든 답이 오는지까지 본다.
