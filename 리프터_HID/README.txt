# M16_BR 2D 맵 생성 (리프터 + 근방 HID)

## 구성 파일 (전부 같은 폴더에 두기)
- make_map.py            : 2D 지도 생성 (메인)
- hid_zone_csv_cre.py    : HID_Zone_Master CSV 생성기 (make_map이 자동 호출)
- HID_Zone_Master_M16A_BR.csv : (자동생성됨) 리프터-HID 매핑 소스
- MAP/M16A/
    BR.layout.zip        : 입력 - 레이아웃
    BR.station.dat       : 입력 - 포트→주소

## 실행 (출력 html 은 make_map.py 폴더에 생김)
python make_map.py MAP\M16A\BR.layout.zip BR.map.html MAP\M16A\BR.station.dat
   ※ 2번째 인자(BR.map.html)가 출력 경로. 그냥 'BR.map.html' 로 주면
     make_map.py 와 같은 폴더에 생성됨. (MAP\... 붙이면 거기에 생김)
   → 콘솔에 '생성 완료: <절대경로>' 가 찍힘. 그 파일을 브라우저로 열기.
   → HID_Zone_Master_M16A_BR.csv 없으면 자동 생성 (make_map.py 폴더에)

## 조작
휠=확대/축소, 드래그=이동, H=좌우반전, F=상하반전, R=리셋

## 표시
●IN(노랑)  ●OUT(초록)  ●노드(회색)
▭리프터범위 (M16=주황, M14=파랑) + 리프터명
HID n (청록) = 각 리프터 박스 아래 '근방 HID 번호'

## 동작 (M16A_BR): 노드 1945 · 연결 2043 · 리프터 17기 · 근방HID 매핑
