# M16_BR 2D 맵 생성 (리프터 + HID IN/OUT)

## 구성
- make_map.py          : 2D 지도 생성 (메인)
- hid_zone_csv_cre.py  : HID Zone 파싱 (make_map가 자동 사용)

## 폴더 배치 예시
F:\M14_Q\리프터_HID_신규\
├─ make_map.py
├─ hid_zone_csv_cre.py
└─ MAP\M16A\
   ├─ BR.layout.zip      (또는 BR.layout.xml)
   └─ BR.station.dat

## 실행
python make_map.py MAP\M16A\BR.layout.zip MAP\M16A\BR.map.html MAP\M16A\BR.station.dat

→ MAP\M16A\BR.map.html 생성 후 브라우저로 열기

## 조작
휠=확대/축소, 드래그=이동, H=좌우반전, F=상하반전, R=리셋

## 표시
●IN(노랑) ●OUT(초록)  →HID-IN(청록) →HID-OUT(자홍)
▭M16(주황) ▭M14(파랑)  ●노드(회색) ─연결(파랑)

※ hid_zone_csv_cre.py 가 없으면 HID 화살표는 생략되고 맵만 생성됩니다.
