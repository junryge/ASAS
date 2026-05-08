# PPT Templates

`ppt_builder.py` 가 사용하는 5개 디자인 템플릿.

## 📁 파일 구성

| 파일 | 테마 | 특징 |
|---|---|---|
| `corporate.pptx` | 파랑 계열 기업용 | 구글 블루, 깔끔한 선 |
| `academic.pptx` | 회색 계열 논문용 | 차분, 레드 액센트 |
| `creative.pptx` | 보라→핑크 | 디자인 강조 |
| `minimal.pptx` | 흑백 | 여백 많음, 레드 포인트 |
| `dark.pptx` | 어두운 배경 | 테크/개발자 발표용 |

각 파일은 **6종 샘플 슬라이드** 포함:
1. Title Slide (표지)
2. Section Header (섹션 구분)
3. Title and Content (일반 내용)
4. Two Content (두 단)
5. Title and Table (표)
6. Title Only (이미지/차트 자유배치)

## 🚀 초기 생성

최초 1회만 실행:

```bash
cd scientific-assistant
python demos_v1/ppt_templates/generate_templates.py
```

→ 이 폴더에 5개 `.pptx` 파일 자동 생성.

의존성: `python-pptx` (`pip install python-pptx`).

## 🎨 커스터마이징

생성된 `.pptx` 를 PowerPoint 로 열어서 직접 수정 가능:
- 폰트 변경 (맑은고딕 → 사내 브랜드 폰트)
- 색상 교체 (디자인 > 색 테마)
- 로고 추가 (슬라이드 마스터 편집)
- 추가 layout 슬라이드 (ppt_builder 가 인덱스로 접근)

수정 후 저장하면 자동 반영.

## 🔧 추가 테마 만들려면

`generate_templates.py` 의 `THEMES` dict 에 새 항목 추가:

```python
THEMES["forest"] = {
    "bg": RGBColor(0xFF, 0xFF, 0xFF),
    "primary": RGBColor(0x16, 0xA3, 0x4A),  # 녹색
    ...
}
```

재실행 → `forest.pptx` 추가 생성.

## ⚠️ 주의

- 한글 폰트는 각 실행 OS 에 설치돼 있어야 함 (맑은 고딕 기본)
- 16:9 와이드스크린 (13.333 x 7.5 인치) 고정
- 슬라이드 마스터가 아닌 **개별 슬라이드 배경** 방식 (이식성 ↑)
