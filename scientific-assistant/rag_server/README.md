# RAG 서버 (데모스 지식검색용)

데모스와 **별도 프로세스**(같은 PC). 데모스의 `knowledge/<user>/*.md` 를 청킹·인덱싱하고
질문에 맞는 **청크만** 골라준다. 채팅 LLM 은 데모스가 API 로 받고, 이 서버는 **임베딩(bge-m3, CPU)** 만 담당.
모델이 없으면 **lexical(BM25+청킹)** 모드로 그대로 동작한다.

## 실행 (윈도우)
```
cd scientific-assistant\rag_server
pip install flask          # 없을 때만 (보통 데모스에 이미 있음)
python app.py
```
→ `http://127.0.0.1:8765`

## bge-m3 임베딩 켜기 (의미검색)
1. `bge-m3-q8_0.gguf` 를 `rag_server\models\` 에 복사
2. `rag_config.json` 의 `embed_backend: "local"`, `local.model_path` 확인
3. `python app.py` 재시작 → 콘솔에 `모드=hybrid(bge-m3)` 뜨면 OK
   - 기존 인덱스를 임베딩까지 채우려면: `curl -X POST http://127.0.0.1:8765/reindex -d "{\"reembed\":true}"`
- GPU 안 씀 (`n_gpu_layers: 0` = CPU). 채팅 모델과 안 싸움.

## 동작 확인
```
curl http://127.0.0.1:8765/health
curl -X POST http://127.0.0.1:8765/search -H "Content-Type: application/json" ^
     -d "{\"user_id\":\"<유저ID>\",\"query\":\"M16B SLA 임계\"}"
```
- `/health` 의 `mode`: `lexical`(모델없음) / `hybrid`(bge-m3 로드됨)
- 첫 검색 시 그 사용자 문서 자동 인덱싱(mtime 증분). 새 문서 등록하면 다음 검색에 자동 반영.

## 설정 (rag_config.json)
| 키 | 뜻 |
|---|---|
| embed_backend | `local`(bge-m3 GGUF) / `api`(사내 /v1/embeddings) / `none`(BM25만) |
| local.model_path | bge-m3 gguf 경로 |
| local.n_gpu_layers | 0=CPU (권장) |
| knowledge_dir | 데모스 knowledge 폴더 (기본 `../knowledge`) |
| chunk_size/overlap | 청크 크기/겹침 |

## 데모스 연동 (Phase 2 — 별도)
`demos_v1/rag_client.py` 가 이 서버 `/search` 를 호출하고, 죽으면 기존 BM25 로 폴백.
`api_config.json` 에 `"rag": {"enabled": true, "url": "http://127.0.0.1:8765"}` 추가.
