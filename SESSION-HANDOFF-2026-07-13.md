# 세션 핸드오프 — 2026-07-13: 실험 W 재런(0.15.0) 채점 결과 논의용

목적: 이 파일 하나 읽으면 채점 결과 논의를 이어갈 수 있게. 원자료를 다시
파낼 필요 없도록 확정 사실과 열린 논점을 분리해 둠.

## 오늘 일어난 일 (한 단락)

실험 W(gridcalc) 실패 분석을 정밀화("acceptance에 없었다"는 오진 —
잣대는 plan에 있었고 약한 인스턴스화 + 시행 실패가 진짜 구멍) →
loopspace **0.15.0** 구현·머지·푸시 (spec 프로브 + 변이 스팟체크 +
verifier 독립 인스턴스화, `loopspace@09aba12`) → 동일 spec+plan으로
검증 재런 (`~/code/gridcalc-rerun`, ornith/opencode, tier C 시드) →
**oracle 106/131로 양 기준선(solo 130, 원런 124)보다 악화** → 품질
3자 비교(변이 테스트 포함) → 발견 3건을 **0.15.1**로 기계화
(`loopspace@8190272`, 경계 부채 + stall kill). 전부 푸시됨. 릴리즈
태그는 보류 (아래 열린 논점 1).

## 확정 사실 (재도출 금지 — 이미 코드 수준으로 검증됨)

- **재런 oracle 106/131.** 실패 25 = R11 differential 24 + R10 1.
  근원 3개:
  1. R7 혼합 mis-ordered range 수용 — `rerun-loopspace-0.15/gridcalc/evaluator.py:202`
     사전식 튜플 비교 `(start_col,start_row)>(end_col,end_row)`.
     B2:A1(완전 역순)은 잡고 A3:C1(열 정순·행 역순)은 통과 → 빈 range 0.
  2. 사이클×캐시 무효화 누락 — 사이클 생성/해소 후 stale 캐시 (~9셀).
  3. R10 카운트 이상 — 자기사이클 첫 get delta 2, `=1/0+Y1` get delta 0.
- **백미: 같은-마음 복제.** 4.4가 이번엔 진짜 NaiveSheet 레퍼런스
  (370줄, 평가 의미론 독립 구현)를 썼는데, 근원 1의 사전식 비교가
  `tests/test_differential.py:161`에 **글자까지 동일하게** 들어 있음 →
  1000 시퀀스 zero mismatches. 같은 마음의 "독립" 레퍼런스는 같은
  오해를 공유한다. held-out oracle(다른 마음)만 잡았다.
- **교차 변이 (grading/mutate.py, mutate2.py — 재실행 가능):**
  - 거친 변이 6종: solo/armB/rerun 자체 스위트 전부 6/6 KILL (빈껍데기 아님).
  - M7(혼합 mis-order = 재런의 출하 버그): **세 arm 스위트 전부 SURVIVED**
    — 같은 모델은 인스턴스가 달라도 같은 맹점.
  - M8(range 오류 강등 = 원런의 출하 버그): solo 스위트 5개 KILL,
    재런 스위트 **31개** KILL (armB는 출하). 재런 스위트가 오류-전파
    계열 방패 최강 — 3.2 패널 FAIL 강제 테스트 + 경계 프로브의 직접 산물.
  - 의미론 프로브 6종: solo 6/6, armB 4/6, rerun 3/6.
- **0.15.0 이행 스펙트럼 (핵심 해석 — 2026-07-13 포렌식으로 정정):**
  phase 1·2 = 프로브·변이 완전 이행(잡을 버그 없던 구간, "suite went
  red" 확인). phase 3 = 경계 소실이나 **원인은 순응 실패가 아니라
  백엔드 타임아웃 사망** — 세션 2는 경계를 인지하고 Phase 3 verifier를
  디스패치했고(10:12), verifier가 ~5분 진행 후 write error + LLM 호출
  "The operation timed out."(300s)로 사망, 오케스트레이터 다음 호출도
  300s 타임아웃(parts 0) → 저널·커밋·handoff 없이 턴 종료, 재개 세션이
  4.1 직행. 근원은 로컬 llama-server 지연. 증거: opencode.db 세션
  `ses_0a73b3d31ffe…`(오케스트레이터)·`ses_0a6f41861ffe…`(verifier),
  상세는 EXPERIMENT.md RERUN RESULTS 포렌식 정정 항목. phase 4 = 경계는
  밟되 프로브·변이 생략(이쪽은 순응 실패 맞음). **버그는 정확히 이행
  공백(phase 3·4 의미론)에 서식** — phase 3은 인프라 몫, phase 4는
  순응 몫. 세션 3의 6.5h 행도 같은 타임아웃 계급일 개연성. "ornith
  오케스트레이터 부적합" 결산(열린 논점 4)은 이만큼 약화해서 읽을 것.
- **검증이 산 것:** 3.2 attempt 2 heavy 패널 FAIL이 실버그 2개
  (자기-포함-범위 사이클 #PARSE!, range 평가의 사이클 감지 우회) +
  무테스트 기준 3개를 강제 수리시킴 → 원런의 강등 버그가 재런엔
  구조적으로 부재한 직접 원인.
- **운영 사건:** 세션 6개, 벽시계 ~11h 중 6.5h는 세션 3 행(파일
  무변화·LLM 호출만 반복; 운영자 kill 1회 17:48 KST). 종료는 complete
  아닌 STUCK(전 태스크 done·phase 4 verified인데 마무리 장부 실패;
  4.2-4.4 미커밋 → grader 커밋 483184b 보존). `pip install -e` 오염
  재발(제거 후 채점). tier C→A 자가 승격, 3.1 저널 누락, 4.2 heavy를
  단일 verifier로 통과(패널 생략).
- **0.15.1 (머지 8190272):** ① looprun 사이클 step 0 "경계 부채" —
  이전 phase 전부 done + `[phase N] verified` 저널 부재 → 태스크
  디스패치 전에 그 경계부터 (디스크에서 매 사이클 재도출) ②
  supervise.sh `LOOPSPACE_STALL_TIMEOUT` (기본 3600s, 0 끔) — 백그라운드
  세션 감시, state/journal 서명 무변화 타임아웃 시 프로세스 트리 kill.
  supervise 테스트 15/15 (신규 3), portability 34/34.

## 열린 논점 (다음 세션 논의 대상)

1. ~~**v0.15.1 릴리즈 태그**~~ **해소 (2026-07-13 오후 세션)**: 사용자
   결정 "지금 태그" → `v0.15.1` origin 푸시 완료. 같은 세션에서 포렌식
   정정(백엔드 타임아웃 사망) 파생으로 **0.15.2** 구현(stale-handoff
   검출 + supervise fast-fail + opencode 타임아웃 가이드) — main 로컬
   머지 `64eeb45`, **origin 푸시와 v0.15.2 태그는 사용자 확인 대기**.
2. **106 vs 124의 해석 확정.** "0.15.0이 품질을 낮췄다"는 성립 안 함
   (버그들은 0.15.0이 안 불린 구간 산물). 그러나 "ornith 런 분산이
   크다"와 "루프 파편화가 해롭다"를 분리하려면 n을 늘려야 함 —
   0.14로 같은 재런을 한 번 더 돌리면 분산 분리 가능. 비용 대비 가치 판단 필요.
3. **heavy 패널 생략 방지** — 이행 표류의 남은 한 조각(4.2가 단일
   verifier로 통과). 경계 부채와 달리 "패널이 돌았는지"는 저널
   형식만으로 기계 판정이 애매함. 설계 필요.
4. **로컬 35B 오케스트레이터 부적합 판정을 공식화할지.** 시리즈 5런
   결산: 구현자로는 쓸만, 오케스트레이터로는 이행 순응이 병목.
   harnesses/ 문서(모델 능력 가이드)에 반영할지.
5. **oracle 갭:** 리터럴 오류문자열("#REF!"를 문자열로 set) 케이스가
   oracle에 없음 — armB·rerun 둘 다 이를 오류값 취급(spec 위반)인데
   무채점. oracle 보강할지.
6. **다음 실험:** W′(솔로 컨텍스트를 실제로 넘치는 3~5x 규모 — 유일한
   미검증 주장) vs frontier-orchestrator × ornith-implementer 하이브리드
   재런 (0.15.x 메커니즘이 순응 좋은 오케스트레이터에서 뭘 잡는지).

## 원자료 위치

- 상세 데이터: `gridcalc/grading/EXPERIMENT.md` **RERUN RESULTS** 섹션
- 재런 트리+상태: `gridcalc/rerun-loopspace-0.15/` (저널·state 포함)
- 라이브 레포(grader 커밋 포함): `~/code/gridcalc-rerun`
- 러너 로그(행 증거): `gridcalc/runner-logs/rerun_supervise.log`
- 변이 하네스: `gridcalc/grading/mutate.py`, `mutate2.py`
  (스크래치 사본 대상이었으므로 재실행 시 arm 트리를 새로 복사할 것)
- loopspace 커밋: 0.15.0 `09aba12`, 0.15.1 `8190272` (둘 다 origin 푸시됨)
- 실험 로그: `EXPERIMENTS-LOG.md` UPDATE (7)·(8)
