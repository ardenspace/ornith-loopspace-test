# DECISION — per-phase 구현자: W′ 게이트에 보류 (2026-07-22)

> **2026-07-26 갱신 — K 종료·W′ 결산 반영. 아래 원본(07-22)은 이력으로 보존.**
>
> **한 줄(갱신): per-phase conducted(K′)를 1순위 후속으로 올리지 말 것 — 후속의
> 무게중심은 lead mode 발전으로 옮긴다. per-task fresh는 "잘못된 설계"가 아니라
> loopspace 정체성과 묶인 의도적 트레이드오프이고, 그 비용(책임 단절)의 진짜
> 구조적 해법은 이미 lead mode다.**
>
> **W′ 결과 (oracle v3, 1330케이스):** S 308(23%) < T 932(70%) < K 1324(99.5%).
> dose-response 단조 성립, 사전 등록 분기 ⓐ 충족.
>
> **07-22 게이트 재해석 — "K>T → K′ 후속"을 문자 그대로 발동하면 오독이다.**
> K의 우위는 thick *지휘 구조*가 값어치를 했다는 증거가 아니라, escalation 사다리가
> **29 태스크 중 18개(62%)에서 ornith 구현자를 gpt-5.5로 자동 승격**시킨 교란의
> 산물이다(종반엔 usage-limit로 로컬 백엔드를 회수해 10.2·10.3은 gpt-5.5 단독). 즉
> K는 "conducted thick"이 아니라 사실상 "gpt-5.5 구현 arm"으로 변질됐다. 구현자를
> 고정한 순수 구조 효과는 **S vs T**(둘 다 ornith)가 격리하며, 거기서도 T≫S로
> 하네스 효과 자체는 독립적으로 성립한다 → "구조가 값어치"는 K가 아니라 S/T가 증명.
>
> **arden의 질문("설계가 잘못된 것 아닌가, 후속으로 갈까 그냥 고칠까")에 대한 판단:**
> - **"per-task fresh = 잘못된 설계"는 과한 진술.** 그것은 loopspace의 토대(디스크
>   기반 재구성·크래시 복구·loopresume·one-shot 헤드리스 하네스 호환)를 위해 책임
>   단절을 감수한 *의도적 트레이드오프*다. per-phase로 전면 교체하면 이 토대가
>   약해진다(원본 리스크 4 참조). "그냥 고친다"는 검증 없이 토대를 무는 것이라 성급.
> - **책임 단절 자체는 실재하고 재확인됐다.** gridcalc W의 `#TYPE!` 강등에 이어,
>   gridcalc-XL에서도 phase 8 경계 검증이 8.3을 재오픈했다 — 앞 태스크가 만든
>   single-sheet closure를 8.3의 cross-sheet 작업이 치우지 않고 죽은 채 병렬로 방치
>   ("죽은 closure scaffolding"). 그 코드를 짠 구현자는 이미 사라졌고 8.3 구현자는
>   담당이 아니었다 — 책임 단절의 교과서 사례.
> - **그러나 loopspace엔 그걸 사후 포착하는 장치가 이미 있고 작동했다 = phase 경계
>   verifier.** 8.3 재오픈이 바로 그 실증. 남는 비용은 "사후라 재작업이 든다"는 것.
> - **그리고 이 문제의 진짜 구조적 답은 이미 lead mode(thin)다.** lead가 phase
>   이상을 통째로 드는 순간 응집성·책임 단절이 *애초에 생기지 않는다*(원본 게이트
>   30–32행이 예견). per-phase conducted(K′)는 conducted 모드를 고집할 때의
>   미봉책이고, 데이터(T 70%)는 lead 방향이 낫다고 가리킨다.
> - **결론(추천, 최종 판단은 arden 몫):** ① per-task fresh 유지(토대 보존) ②
>   후속 무게중심 = lead mode 발전 — "lead가 책임 단절을 구조적으로 해소하는가"를
>   측정(변이 버그 재발 0 여부, cross-cutting 클래스)하는 실험으로 재설계 ③
>   conducted를 계속 쓸 상황을 위해선 phase verifier의 책임-단절 탐지 강화 또는
>   cross-cutting 규칙을 스펙 레벨의 명시적 정리 task로 분리(설계 개선이지 새 arm이
>   아님) ④ K′(per-phase conducted)는 폐기가 아니라 **우선순위 하락**으로 표기.

한 줄: **looprun 디스패치 단위(task별 fresh → phase별 fresh) 변경은 K 런 종료까지
동결하고, W′ 해석 분기(T vs K)가 우선순위를 정한다.** 이 파일은 그날 브레인스토밍을
다시 하지 않기 위한 결정 기록이다.

## 배경 — 착각의 발견과 감사 결과

- 블로그 1편 집필 중 발견: 사용자는 looprun의 구현자 디스패치를 **phase별**로
  알고 있었으나, 실제(그리고 문서화된) 설계는 **task별 fresh**다 —
  `loopspace/skills/looprun/SKILL.md` Orchestrator Contract 1조 "Fresh agent per
  task, never reused", `harnesses/claude-code.md` "Never reuse an agent".
- **감사 결과: 착각은 산출물에 스며들지 않았다.** W′ 사전 등록
  (`gridcalc-xl/grading/EXPERIMENT.md`)은 K를 "0.16 하이브리드 구성 재사용"으로만
  기술하고 해석 분기 ⓐⓑⓒ는 구조 용량 축이라 디스패치 단위와 무관. SPEC·oracle
  v3·블로그 1편(정확히 "태스크마다"로 기술)·2편 초안(혈통 축, 직교) 전부 클린.
  → **전면 재진행 불필요 판정.** 모든 런은 코드에 적힌 대로(task별) 돌았고 oracle은
  그 실제 시스템을 채점했다.
- W′ 현황 (2026-07-22 디스크 확인): **T 완주**(7/16 20:32 final gate PASS,
  budget 60d/10h) / **S 세션 5개 소비**(7/21 — manipulation check 4+ 충족 추정,
  전제 발동 유력) / **K 진행 중**(`run_status: executing`, phase 6/10, task 6.3).

## 동결

**K 종료까지 looprun 디스패치 설계 변경 금지.** K는 "출하된 conducted 모드"를
측정하는 arm이므로 mid-run 설계 변경이야말로 실험 오염이다.

## 게이트 — W′ 해석 분기에 종속

- **T ≥ K ("thin으로 충분")** → per-phase conducted **우선순위 하락**. lead가
  phase(이상)를 통째로 드는 순간 응집성 문제 자체가 소멸 — conducted 수리보다
  lead 모드 방향이 답.
- **K > T (지휘가 값어치)** → **K′ 후속 실험 사전 등록**: thick + per-phase
  구현자, 같은 SPEC + oracle v3 재사용. 블로그 1편이 예고한 "'태스크마다 새
  구현자' 재검토" 편의 소재.

## 근거 요약 (재논의 방지)

- **per-task의 실증된 비용 두 종류.** ① 정보 단절(kvtx 1.2 `Store` 통재구현,
  135→85 LOC) — 0.14 intra-phase carry(exports/PRIOR WORK)로 **이미 해소**.
  ② **책임 단절**(gridcalc W: `#REF!`/`#CYCLE!`→`#TYPE!` 강등이 range 경로에만 —
  cross-cutting 규칙을 맡은 task의 사정거리가 task 경계까지라, 앞선 task의 코드는
  누구의 책임도 아니었음) — **정보 전달로는 못 고치는 구조적 문제.** per-phase
  논의의 실질 동기.
- **그러나 W에서 이긴 건 per-phase가 아니라 solo 단일 컨텍스트**(130/131, 40분
  vs 124/131, ~240분). 도출 원칙: **"응집성은 컨텍스트 안에서만 산다 — 디스패치
  단위는 컨텍스트에 담기는 최대의 응집 단위."** phase는 loopspace의 기존 응집
  경계(phase 브랜치·phase verifier·PRIOR WORK 조립 범위)와 정렬되는 자연 후보.
  per-phase의 효용은 이음새 제거가 아니라 **이음새를 결합 최저점(phase 경계)으로
  배치**하는 것.
- **per-phase의 미검증 리스크 4:** ① 토큰이 오히려 증가 가능 — 살아있는
  에이전트는 히스토리 누적으로 ~O(N²), task 사이 verifier 대기 동안 프롬프트
  캐시 냉각; fresh 재탐색은 O(N×탐색) ② 맥락 비대 + 자기 코드 앵커링(verifier
  교착) ③ 하네스 계약(PROFILE-SPEC)에 continuation 능력 항목 자체가 부재 —
  one-shot exec 하네스(codex/opencode 헤드리스)는 불가 ④ 디스크-재구성
  가능성(크래시 안전·loopresume·supervise의 토대) 약화.

## K′ 설계 스케치 (2026-07-22 논의분)

- 원칙 교체: "Fresh agent per task" → **"Fresh agent per phase, fresh verifier
  per task."** phase 경계 = 무조건 교체. verify heavy(task별 검증·heavy 패널·
  다른-혈통 verifier)는 불변.
- FAIL 재시도: 1차 = 같은 구현자가 findings로 수리(맥락 보존이 목적이므로),
  같은 task 2차 FAIL = 구현자 교체(앵커링 의심 시점에만 새 눈). **[미확정 —
  대안: 항상 같은 구현자 / FAIL마다 교체]**
- 구현자 리포트에 컨텍스트 잔량 신호 한 줄 → 오케스트레이터 선제 교체. 교체·
  크래시 투입 = 기존 fresh 디스패치와 동일(PRIOR WORK 블록은 verifier·교체·복구용
  으로 **유지**, 폐기 아님).
- 하네스: PROFILE-SPEC에 선택 능력 `## Continuation` 신설("디스패치한 에이전트에
  후속 메시지로 다음 리포트를 받을 수 있는가"). 미지원/핸들 소실 → task별 fresh
  **폴백**(Tier B의 병렬→순차 폴백과 같은 패턴 — 의미론 동일, 토큰만 추가).
  에이전트 핸들은 state.md에 기록하지 않음(세션 리셋 = 자연 폴백, 자기치유).
- **[미확정 2]** `risk: heavy` task도 살아있는 구현자에게 이어 맡길지 — 잠정:
  동일 취급(위험 관리는 패널 몫, 구현 맥락은 heavy일수록 가치).
- 측정 항목(K′ 사전 등록 후보): cross-cutting 버그 클래스 재발 0 여부 / 토큰·
  벽시계 vs K / FAIL 재시도 앵커링 교착 여부.

## 블로그 처분 (확정)

- **1·2·3편 그대로 진행.** 1편(branch `blog/my-harness-lost`)은 per-task를
  정확히 기술 + "재검토는 나중에" 예고 보유. 2편(`blog/same-mind-blind-spots`)은
  혈통 축이라 직교 — 결말 티저 "3-arm 돌아가는 중"도 현재 사실과 일치. 3편
  (포렌식)은 무관하며, 이번 착각을 "자기 결론을 뒤집는 정정" 사례로 각주 후보.
- 4편 = W′ 결과. per-phase 재검토 편은 K′ 결과 후(게이트 발화 시).

## quarantine-armT-contamination 포렌식 (2026-07-22 해소)

**결론: K(thick)의 구현자 세션들이 cwd를 `runs/thick/`가 아니라 아카이브
`armT-thin/`으로 resolve해 그 안에 작업물을 쓴 wrong-cwd 유출. T 결과는 무결,
K는 correctness 무결·secondary 지표(재시도·벽시계)에 노이즈.**

증거 체인:
- 격리 파일 mtime 7/18 20:38–20:58(formula.py·test_formula_parser.py —
  thick 1.1 burst~2.1 파서 작업대, 2.1 커밋 21:37) + 7/19 19:53–20:46
  (reference_model.py·test_differential.py — thick 4.2 작업대, 4.2 커밋 22:40).
- **스모킹 건 = thick journal 409-412행**: `[4.2] attempt 1 — FAIL`, 구현자
  "naive reference model + 1000-seed differential 구현" 보고 vs verifier
  "`pytest -q` passes, but the Task 4.2 implementation files and tests are
  **absent**". 작업은 했는데 thick 트리에 없음 = 아카이브에 씀. verifier가
  트리를 기계로 확인하는 덕에 적발·재시도(올바른 트리에서 재구현 후 커밋).
- 오염 장소는 runs/thin이 아니라 **아카이브 armT-thin/**: 그 gridcalc/·tests/
  mtime = 격리 시각(7/21 13:17:56)과 일치, .pytest_cache 7/18 20:48 생성(오염
  세션이 아카이브에서 pytest 실행). `__init__.py.bak`은 thin 원본과 **동일**
  (오염 세션이 백업 후 자기 모듈을 씀; 원본 복원 확인). 이후 아카이브 퍼미션
  read-only 전환됨.
- **T 무결 근거 (전부 오염 이전)**: T 완주+final gate 7/16 20:32–20:40, git
  bundle 7/17 05:27, trajectory.csv 채점 7/16 20:43. runs/thin git 히스토리·
  번들 무접촉, 트리 클린.
- **K 영향**: correctness 채점은 최종 thick 트리 기준이라 무오염. 단 wrong-cwd
  실패가 재시도·burst·벽시계에 섞임(1.1 attempt 3+burst 3, 4.2 attempt 1 등) —
  **사전 등록 secondary 지표(halt·벽시계·비용) 해석 시 명기 필수.** 4.2 burst
  candidate 1 "empty response"는 별건(ornith reasoning-drop 계급).
- 사용자 초기 가설 "codex 토큰 소진" 기각 — 증거는 wrong-cwd 유출. 기존
  GOTCHA("raw opencode run이 상대경로를 SKILL 디렉토리 기준 resolve") 계급의
  재발. 방어: 아카이브 read-only(적용됨) + 디스패치 프롬프트에 절대경로 cwd
  명시(기존 처방 재확인).

## 미결

- 7/16 이후 런 기록(T 완주·S 5세션·K 진행·이 포렌식) EXPERIMENTS-LOG 미기재
  부채 — K 종료 후 결산 UPDATE에서 함께 정리 권장.
