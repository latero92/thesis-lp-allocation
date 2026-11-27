# 선형계획모형을 활용한 유·무인 지뢰탐지 작업의 면적배분 최적화

석사학위논문에 사용한 실행 코드, 입력값, 594개 시나리오의 결과 및 실행기록을 보존한 **v1.0** 자료집이다. 2026년 10월 30일의 실험은 66개 면적 구성과 9개 계수 수준을 조합하였다. 논문의 숫자를 확인하려면 아래 CSV를 바로 열 수 있다.

## 논문에서 자료 찾기

| 논문 항목 | 찾아볼 자료 |
|---|---|
| 부록 A의 코드 A-2와 A-6 | [원실행 코드](executed/run_experiment.py) 44–61행, 170–171행 및 175–178행 |
| 표 4-2·표 B-1의 시나리오별 완료시간 | [시나리오 결과](results/scenario_results.csv). `T_equal_h`, `T_proportional_h`, `T_optimal_h`가 각각 균등·능력비례·최적배분의 전체 완료시간이다. |
| 표 4-9·표 B-2·표 B-3의 수단별 배분 | [수단별 결과](results/unit_results.csv). 표 B-2와 B-3의 시나리오 번호는 각각 `P11_k0.1`과 `P07_k0.9`이며, 해당 표에서 사용한 배분방식은 `optimal`이다. |
| 표 C-1의 실행환경 및 실행 횟수 | [실행 명세](logs/run_manifest.public.json), [계산기 호출기록](logs/solver_calls.csv) |
| 표 C-2의 수치 점검 | [요약기록](results/summary.json)의 `max_residuals`에 표의 최대 잔차가 저장되어 있다. [개별 점검기록](results/numerical_checks.csv)은 시나리오와 배분방식별 값을 담는다. |

`scenario`는 논문과 결과 파일을 연결하는 시나리오 식별자이며, `solver_call_id`는 원실행 호출기록에 대응한다. 면적의 단위는 m², 시간은 h, 단축률은 %이다. 결과 파일에는 저장 당시 정밀도의 값이 들어 있다.

## 파일별 용도

| 파일 | 내용 |
|---|---|
| [executed/run_experiment.py](executed/run_experiment.py) | 2026년 10월 30일 실행한 Python 원본. 입력 읽기, 선형계획모형 구성, 세 배분방식 비교 및 결과 저장을 포함한다. |
| [executed/config_594.json](executed/config_594.json) | 원실행 때 읽은 입력 파일. 면적 구성 간격, 수단별 계수와 계산기 설정을 담는다. |
| [reader/run_experiment.py](reader/run_experiment.py) · [reader/config_594.json](reader/config_594.json) | 원실행 코드와 입력값을 논문 표기로 읽는 열람용 사본. `executed/`와 같은 행에서 수단 표기 및 열 이름만 바뀐다. |
| [archive/scenario_results.original.csv](archive/scenario_results.original.csv) | 원실행 당시 식별자를 사용한 594행 결과 원본. |
| [results/scenario_results.csv](results/scenario_results.csv) · [JSON](results/scenario_results.json) | 594개 시나리오별 완료시간, 단축시간, 단축률 및 수단별 집계. |
| [results/area_compositions.csv](results/area_compositions.csv) | 면적 구성 66개의 번호와 지형별 비율·면적. |
| [results/unit_results.csv](results/unit_results.csv) | 시나리오·배분방식·수단별 담당면적과 누적 작업시간. |
| [results/allocations_all_methods.csv](results/allocations_all_methods.csv) | 세 배분방식의 수단별·지형별 담당면적과 작업시간. |
| [results/allocations_primary.csv](results/allocations_primary.csv) · [results/primary_solutions.json](results/primary_solutions.json) | 각각 최적배분의 수단·지형별 결과와 시나리오별 계산기 해 벡터. |
| [results/representative_eight_scenarios.csv](results/representative_eight_scenarios.csv) | 선정 목적을 표시한 대표 시나리오 8건. |
| [results/marginal_changes.csv](results/marginal_changes.csv) · [results/endpoint_summary.csv](results/endpoint_summary.csv) | 각각 인접 계수 수준 간 변화와 양 끝 수준의 비교 결과. |
| [results/plateau_segments.csv](results/plateau_segments.csv) · [results/primary_structure_transitions.csv](results/primary_structure_transitions.csv) | 각각 완료시간이 일정한 구간과 저장된 최적배분 구조가 달라지는 구간. |
| [results/terrain_count_summary.csv](results/terrain_count_summary.csv) | 시나리오를 지형 종류 수에 따라 구분한 요약. |
| [results/numerical_checks.csv](results/numerical_checks.csv) · [results/summary.json](results/summary.json) | 각각 개별 점검값과 당시 저장한 결과·점검값 요약. |
| [logs/solver_calls.csv](logs/solver_calls.csv) · [JSON Lines](logs/solver_calls.jsonl) | 호출 594건의 식별자, 시각, 계산 상태, 목적값 및 모형 해시. JSON Lines는 한 줄당 한 건이다. |
| [logs/run_20261030.txt](logs/run_20261030.txt) · [logs/summary_20261030.txt](logs/summary_20261030.txt) | 당시 프로그램의 진행 출력과 결과 요약 출력. |
| [logs/run_manifest.public.json](logs/run_manifest.public.json) | 원실행의 환경, 시각, 버전, 횟수와 해시. 공개본에서는 실행 컴퓨터의 절대경로를 대체하였다. |
| [provenance/files.tsv](provenance/files.tsv) | 공개 파일별 자료 출처, 원자료와 공개 파일의 SHA-256. |
| [provenance/identifiers.tsv](provenance/identifiers.tsv) | 원실행본과 논문 열람본의 식별자·열 이름 대조표. |
| [SHA256SUMS.txt](SHA256SUMS.txt) | 릴리스 파일의 바이트 단위 동일성을 확인하는 SHA-256 목록. |

## 실행 당시 표기와 논문 표기

무인지상체계의 영문 약어는 **UGV**이며, 논문 모형과 결과 파일의 수단값은 **`U`**이다. 원실행 코드·입력 및 `archive/`의 CSV에서는 동일 수단을 `R`로 표시하였다. `results/`는 2026년 11월 18일 수단 식별자를 `U`로 맞춰 보관한 결과에서, 설명형 열 이름을 `ugv_` 표기로 통일한 열람본이다. 예를 들어 원본의 `robot_q1_m2_h`는 `ugv_q1_m2_h`에 대응한다. 두 자료에서 같은 `scenario`와 `solver_call_id`가 같은 시나리오와 계산기 호출을 가리킨다. `reader/`는 이 표기를 사용한 코드·입력의 열람용 사본이다. 원실행과 공개본에 대응하는 해시를 파일별로 기록하였다.

원실행기록의 환경은 Python 3.12.14, NumPy 2.2.6, SciPy 1.16.3이며, 계산기는 SciPy의 HiGHS이다. 소스는 당시 작업 디렉터리 구조와 `results/`, `logs/`, `input_snapshot/` 경로를 사용한다. 이 릴리스에는 당시 기록된 결과를 담았으며, 릴리스 제작 과정에서 다시 계산한 값은 없다.
