# M16_BR 2D 맵 생성 (리프터 + HID 구역)

## 구성 파일
- make_map.py            : 2D 지도 생성 (메인)
- hid_zone_csv_cre.py    : HID_Zone_Master CSV 생성기 (HID 구역 산출)
- MAP/M16A/
    BR.layout.zip        : 입력 - 레이아웃 (내부 layout/layout.xml)
    BR.station.dat       : 입력 - 포트→주소
    HID_Zone_Master_M16A_BR.csv : (생성물) HID 구역 정의
    BR.map.html          : (생성물) 2D 지도

## STEP 1) HID_Zone_Master CSV 생성  ※ 처음 1회 (이미 있으면 건너뜀)
python hid_zone_csv_cre.py --fab M16A --layout BR
  └ 또는: python hid_zone_csv_cre.py MAP/M16A/BR.layout.zip MAP/M16A/HID_Zone_Master_M16A_BR.csv
  → MAP/M16A/HID_Zone_Master_M16A_BR.csv 생성
     (CSV의 HID_ID=리프터포트, Zone_ID=HID번호)

## STEP 2) 2D 지도 생성
python make_map.py MAP/M16A/BR.layout.zip MAP/M16A/BR.map.html MAP/M16A/BR.station.dat
  → MAP/M16A/BR.map.html 생성 후 브라우저로 열기
  ※ make_map 은 station.dat 같은 폴더의 HID_Zone_Master*.csv 를 자동으로 읽어 HID 구역을 그림

## 조작
휠=확대/축소, 드래그=이동, H=좌우반전, F=상하반전, R=리셋

## 표시
●IN(노랑)  ●OUT(초록)  ●노드(회색)
▰HID구역 (M16=청록, M14=자홍) + HID번호 라벨
▭리프터범위 (M16=주황, M14=파랑) + 리프터명

## 동작 (M16A_BR 기준)
노드 1945 · 연결 2043 · 리프터포트 69 · HID구역 21
