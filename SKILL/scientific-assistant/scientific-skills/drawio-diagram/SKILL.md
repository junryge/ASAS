# Draw.io 다이어그램 생성 스킬

## 개요
코드, 아키텍처, 데이터 흐름, 시스템 구조 등을 분석하여 Draw.io (diagrams.net) 호환 XML을 생성합니다.
생성된 다이어그램은 `.drawio` 파일로 저장하거나 Draw.io에서 직접 열 수 있습니다.

## 핵심 규칙

### 1. 출력 형식
- 반드시 ```drawio 코드블록 안에 XML을 출력하세요
- 프론트엔드가 자동으로 미리보기 + 복사 + 다운로드 버튼을 렌더링합니다

### 2. Draw.io XML 기본 구조
```drawio
<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" agent="skill" version="21.0.0" type="device">
  <diagram id="diagram1" name="Page-1">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- 여기에 도형과 연결선 추가 -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### 3. 주요 도형 패턴

#### 사각형 (프로세스/모듈)
```xml
<mxCell id="2" value="모듈명" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="60" as="geometry"/>
</mxCell>
```

#### 다이아몬드 (조건/분기)
```xml
<mxCell id="3" value="조건?" style="rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
  <mxGeometry x="110" y="200" width="140" height="80" as="geometry"/>
</mxCell>
```

#### 원통형 (데이터베이스)
```xml
<mxCell id="4" value="DB" style="shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
  <mxGeometry x="100" y="300" width="80" height="80" as="geometry"/>
</mxCell>
```

#### 화살표 (연결선)
```xml
<mxCell id="5" value="데이터 흐름" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jetSize=auto;html=1;" edge="1" parent="1" source="2" target="3">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

#### 그룹/컨테이너 (패키지/서비스)
```xml
<mxCell id="6" value="서비스 그룹" style="swimlane;startSize=25;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;" vertex="1" parent="1">
  <mxGeometry x="50" y="50" width="300" height="200" as="geometry"/>
</mxCell>
```

#### 문서 (파일/문서)
```xml
<mxCell id="7" value="설정 파일" style="shape=document;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=0.27;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="1">
  <mxGeometry x="100" y="400" width="120" height="80" as="geometry"/>
</mxCell>
```

### 4. 색상 팔레트 (Draw.io 기본)
| 용도 | fillColor | strokeColor |
|------|-----------|-------------|
| 파란색 (프로세스) | #dae8fc | #6c8ebf |
| 초록색 (성공/DB) | #d5e8d4 | #82b366 |
| 노란색 (조건/경고) | #fff2cc | #d6b656 |
| 주황색 (중요) | #ffe6cc | #d79b00 |
| 빨간색 (에러) | #f8cecc | #b85450 |
| 보라색 (외부) | #e1d5e7 | #9673a6 |
| 회색 (컨테이너) | #f5f5f5 | #666666 |

### 5. 코드 분석 → 다이어그램 변환 가이드

#### Python/Flask 앱 분석 시:
1. **라우트/엔드포인트** → 사각형 노드로 표현
2. **함수 호출 관계** → 화살표로 연결
3. **데이터베이스 접근** → 원통형 노드
4. **조건 분기** → 다이아몬드
5. **외부 API 호출** → 구름(cloud) 도형
6. **파일 I/O** → 문서 도형

#### 클래스 다이어그램:
1. **클래스** → 상단에 클래스명, 속성, 메소드 구분
2. **상속** → 실선 + 삼각형 화살표
3. **구성** → 실선 + 채워진 다이아몬드
4. **의존** → 점선 화살표

#### 시퀀스 다이어그램:
1. **액터/시스템** → 상단 사각형 + 생명선
2. **메시지** → 실선 화살표 (동기) / 점선 (비동기)
3. **반환** → 점선 화살표

### 6. 레이아웃 규칙
- **수평 간격**: 최소 40px
- **수직 간격**: 최소 40px
- **노드 크기**: 최소 width=120, height=60
- **폰트 크기**: 기본 12px, 제목 14px
- **정렬**: 가능한 한 그리드에 맞춤 (10px 단위)
- **흐름 방향**: 위→아래 또는 왼쪽→오른쪽 (사용자가 지정하지 않으면 위→아래)

### 7. 복잡한 다이어그램 팁
- 노드가 10개 이상이면 그룹/swimlane 사용
- 교차하는 연결선은 waypoint 조정
- 범례(legend) 추가 권장
- 각 노드에 의미 있는 ID 부여 (순차 번호)

## 사용 예시

사용자가 "이 Flask 앱의 구조를 Draw.io로 그려줘"라고 요청하면:

1. 코드의 라우트, 함수, 데이터 흐름을 분석
2. 적절한 도형과 색상으로 Draw.io XML 생성
3. ```drawio 코드블록으로 출력
4. 다이어그램 설명도 함께 제공

### 8. UserObject 패턴 (메타데이터 포함 노드)
복잡한 다이어그램에서는 `UserObject`로 타입/속성 메타데이터를 포함할 수 있습니다.

#### 외부 엔티티 (DFD용)
```xml
<UserObject label="사용자" type="externalEntity" placeholders="1" id="e1">
  <mxCell style="shape=rectangle;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;" parent="1" vertex="1">
    <mxGeometry x="100" y="10" width="120" height="40" as="geometry"/>
  </mxCell>
</UserObject>
```

#### 프로세스 (DFD용 타원형)
```xml
<UserObject label="데이터 처리" type="process" flow="데이터 흐름" placeholders="1" id="p1">
  <mxCell style="shape=ellipse;perimeter=ellipsePerimeter;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;" parent="1" vertex="1">
    <mxGeometry x="100" y="120" width="140" height="50" as="geometry"/>
  </mxCell>
</UserObject>
```

#### 데이터 저장소 (DFD용)
```xml
<UserObject label="데이터베이스" type="dataStore" placeholders="1" id="d1">
  <mxCell style="html=1;dashed=0;whiteSpace=wrap;shape=partialRectangle;right=0;left=0;" parent="1" vertex="1">
    <mxGeometry x="100" y="240" width="140" height="40" as="geometry"/>
  </mxCell>
</UserObject>
```

#### 데이터 흐름 화살표
```xml
<mxCell id="f1" value="요청 데이터" style="endArrow=blockThin;endFill=1;fontSize=11;orthogonal=1;" parent="1" source="e1" target="p1" edge="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### 9. 다이어그램 유형별 가이드

#### DFD (데이터 흐름 다이어그램)
- 외부 엔티티: 사각형 (사용자/외부 시스템)
- 프로세스: 타원 (데이터 변환/처리)
- 데이터 저장소: 열린 사각형 (DB/파일)
- 데이터 흐름: 레이블된 화살표

#### 구름(Cloud) 도형 (외부 서비스)
```xml
<mxCell id="c1" value="외부 API" style="ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="100" as="geometry"/>
</mxCell>
```

#### 액터 (사용자/역할)
```xml
<mxCell id="a1" value="관리자" style="shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="30" height="55" as="geometry"/>
</mxCell>
```

## 주의사항
- mxCell의 id는 반드시 고유해야 합니다 (0과 1은 root용 예약)
- parent="1"은 기본 레이어입니다
- vertex="1"은 노드, edge="1"은 연결선입니다
- source와 target은 연결할 노드의 id입니다
- XML은 반드시 유효한 형태여야 합니다 (태그 닫기 등)
- UserObject 사용 시 type 속성으로 노드 유형을 명시하면 Draw.io에서 편집할 때 유용합니다
