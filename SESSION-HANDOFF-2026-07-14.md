# 세션 핸드오프 — 2026-07-14: 하이브리드 재런 종결 후

목적: 이 파일 하나로 다음 세션이 이어갈 수 있게. 2026-07-13 핸드오프를
대체함(그쪽 열린 논점은 아래에 흡수·갱신). 상세 데이터는 재도출하지 말고
`gridcalc/grading/EXPERIMENT.md`의 HYBRID RESULTS + 중간 사건 1~8을 볼 것.

## 이 세션에서 일어난 일 (요약)

1. **포렌식 정정**: 0.15.0 재런의 "phase 3 경계 스킵"은 순응 실패가 아니라
   **백엔드 300s 타임아웃 사망**(opencode.db로 확정). armB 1차의
   "reasoning-드롭"도 나중에 **출력 캡 8192 절단**으로 확정 — "로컬 35B
   순응 병목" 결산 대폭 완화.
2. **loopspace 0.15.1 태그 푸시, 0.15.2 구현·머지·태그**(stale-handoff
   검출 `position:` 필드 + supervise fast-fail + opencode 타임아웃 가이드,
   `loopspace@64eeb45`). 사용자가 직접 푸시·태그 완료.
3. **oracle v2**: 리터럴 오류문자열 3 테스트 추가(총 134). 재채점:
   solo 133 / armB 126 / 재런 107.
4. **하이브리드 재런 완주** (`~/code/gridcalc-hybrid`, loopspace 0.15.2,
   오케스트레이터·verifier = openai/gpt-5.5(ChatGPT OAuth), 구현자 =
   ornith 35B): **oracle 119/134**, halt 8회(전부 규정 halt, 운영자 대행
   결정 8건), 벽시계 ~12h. 아카이브 `gridcalc/hybrid-loopspace-0.15.2/`.

## 확정 사실 (재도출 금지)

- **처방 실증**: 교차-마음 verifier(GPT)가 M7(혼합 역순 range)을 3.1에서
  라이브 적발 + stale-캐시 클래스를 4.2에서 차단. **hybrid 자체 스위트가
  M7·M8 변이 모두 KILL — 시리즈 최초**(세 same-mind 스위트는 M7 전부
  SURVIVED). 신규 리터럴 오류문자열 3건도 hybrid만 전부 통과.
- **유일 출하 버그의 소재 = 같은-마음 페어링 지점**: 실패 15건 전부 R11,
  단일 근원(의존성-평가 경로 캐시가 closure 미등록 → 무효화 불가 →
  stale). 그 버그가 사는 4.2는 GPT-구현+GPT-검증(런에서 유일한 같은-마음
  쌍). **같은-마음 사각지대는 frontier에서도 재현** — oracle(제3의
  마음)만 적발.
- **같은-마음 3형태 완성**: 글자 복제(재런 4.4) → 테스트 맹점 공유
  (하이브리드 3.1, 교차-마음이 차단) → 적대적 밀도 감각 부재(하이브리드
  4.4: 정직한 380줄 레퍼런스가 주소 풀 200셀 탓에 0 mismatch; 12셀로
  좁히면 21/100 시드 적발 — `tests/test_differential.py`의
  `_ADDR_POOL_SMALL` 패치로 재현 가능).
- **119 < 126(armB) 해석**: 단일 깊은 버그가 R11 40개 중 15개를 무너뜨린
  것. 귀속이 same-mind 페어링이라 "파편화 해악" 증거로 못 씀.
  파편화-vs-순응 분리는 여전히 미결 → W′만 남음.
- **운영 함정 (재발 방지)**: ① Claude Code 백그라운드 태스크로 러너를
  돌리면 하네스 태스크 정리에 런이 동반 사망 — **nohup 완전 분리 필수**
  ② supervise의 `pkill -9 -f opencode`가 argv에 "opencode" 문자열을 가진
  모니터/체인 스크립트까지 죽임 — 감시 스크립트는 브래킷 트릭
  (`openc[o]de`) 필수 ③ `pip install -e` 오염 이번에도 재발(채점 전 제거).

## 열린 논점 (다음 세션 논의 대상)

1. **loopspace 0.16 후보 3건** — ① 경계-초과 구현 → 후속 태스크
   failed-first 교착: "임시 제거→red 시연" 경로를 기본 처방으로 기계화
   ② differential/레퍼런스에 밀집 소구역(주소 풀 밀도) 요구를 템플릿에
   명시 ③ heavy 패널 생략 방지(0.15.0 재런 잔여, 이번 런은 패널 정상).
2. **halt 결정의 자동화/위임** — 무인 런의 실질 병목은 halt 8회마다 사람
   결정이 필요했다는 것(이번엔 Claude가 대행). loopsupervise에
   "결정 대행자" 훅을 넣을지, halt 옵션에 기계 판정 가능한 기본값을
   달지 설계 논의.
3. **다음 실험 W′** — 솔로 컨텍스트를 실제로 넘치는 3~5x 규모, 시리즈의
   유일한 미검증 핵심 주장. 하이브리드 구성(frontier 오케스트레이터 ×
   ornith 구현자 + 교차-마음 verifier)이 기본 후보. 과제·oracle 설계
   비용이 실험 한 사이클급이므로 spec부터.
4. **harnesses/ 모델 능력 가이드 갱신** — "로컬 35B: 구현자 유효(작은
   브리프+캡 30000+타임아웃 900s), 오케스트레이터 부적합 판정은 인프라
   정정으로 완화, verifier는 반드시 다른 혈통" 반영.
5. **oracle 갭 재확인** — v2로 리터럴 오류문자열은 해소. R11 밀도 교훈을
   oracle 자체에도 역적용할지(현 12셀 유지가 정답으로 보임).

## 원자료 위치

- 하이브리드 상세: `gridcalc/grading/EXPERIMENT.md` **HYBRID RESULTS** +
  중간 사건 1~8 (사건별 커밋: `9861f5f`~`5f7ecc9`)
- 하이브리드 아카이브: `gridcalc/hybrid-loopspace-0.15.2/` (트리+.loopspace)
- 라이브 레포: `~/code/gridcalc-hybrid` (opencode.json에 하이브리드 라우팅)
- 러너 로그: `gridcalc/runner-logs/hybrid_supervise.log`,
  재개 스크립트 `gridcalc/hybrid_resume{3..8}.sh`
- 변이 하네스: `grading/mutate.py`, `mutate2.py` (하이브리드용 M7/M8은
  이 세션에서 수동 적용 — SPECS에 hybrid 항목 추가하면 재실행 가능)
- loopspace: 0.15.2 = `64eeb45` (태그 v0.15.2, origin 푸시됨)
- opencode: OpenAI ChatGPT OAuth 등록됨, ornith는 `:18081`
  (글로벌 300s 타임아웃 유지 — 하이브리드 프로젝트만 900s/캡 30000)
- 실험 로그: `EXPERIMENTS-LOG.md` UPDATE (9)·(10)
