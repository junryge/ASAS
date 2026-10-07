# FAB 위험 룰 v1.2

FAB별_지표와_스코어링룰_v1_2_설명.html을 브라우저로 열어 지표→파생→룰→점수 흐름을 확인하세요.

일반 Sorter만 평가하고 CU Sorter는 미평가입니다. FAB 반송위험은v1.1과 같습니다. 변경 내용은CHANGELOG.md, 정확한 설정은rule_config.json입니다.

실행: `python run_safe.py --input "원천데이터.zip" --out result_v1_2 --timeout 300`

1회 실행, 자동재시도0회, 기본300초 제한. pandas/numpy 필요. --fit은 고정 배포본에서 차단됩니다.

검증: `python verify_rules.py --input "설계용원천.zip"`

결과 일반 Sorter 컬럼은 점수.일반Sorter대기 / 등급.일반Sorter대기입니다. 이전 점수.Sorter대기/등급.Sorter대기를 참조하던 후처리를 수정하세요. HUB에는 Sorter가 없어미평가. CU는0점 정상으로 처리하지 마세요.

평가기간 실행 시 이전40분 이상 원천을 함께 넣어 초기 이력을 확보하고 통계만 평가기간으로 제한하세요. 9/12~15 독립평가는 원천 수신 전입니다. 자동 제어·배포 없음.
