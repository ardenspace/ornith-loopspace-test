# Experiment W: multi-session drift A/B (gridcalc)

written: 2026-07-11 (design; run pending) · follows subcut (X, precise-spec
delta 0), intervalset (Y, ambiguous-spec delta 0), kvtx (Z, heavy-task
delta 0 + coherence gap → loopspace 0.14 intra-phase carry, verified by
rerun)

## HYBRID RESULTS (2026-07-14, complete — 사전 등록 관측 2/2 적중, M7·M8 모두 자체 스위트가 KILL, oracle 119/134)

- **완주**: 13 태스크(재계획 포함)/4 phase, **`run complete` 정상 종료**(재런의 STUCK과 대조 — 마무리 장부 완결, 클린 트리, 최종 커밋 `82a5a07`). 전 phase 경계 완전 이행: `probes_phase_{1,2,3,4}.py` 전부 실재 + 경계당 변이 2건 red + freshness/structure-note 활용. halt 8회(전부 규정 halt, 운영자 결정으로 재개) — 인프라 2(출력 캡 절단→30000 상향, 900s 타임아웃 트레이드오프), 역량 2(2.1·4.2 → 6디스패치 소진 후 frontier 라우팅), 설계 함정 1(경계 초과 구현→failed-first 교착), 검증 마찰 3(좁은 재개로 해소). 벽시계 ~12h.
- **oracle v2: 119/134** — solo 133 > armB 126 > **hybrid 119** > 재런 107. 실패 15건 전부 R11 differential(40 중 15), **단일 근원 코드 확정**: 의존성 평가 경로로 캐시된 셀은 closure 미등록 → closure-기반 무효화가 영원히 못 닿음 → stale 값/#DIV!/#CYCLE! (재현: seed 0, op52 `set C4,2`가 캐시의 C4=-1을 못 지움; 최소 메커니즘 = `_cache` 기록은 evaluate() 내부, `_closures` 등록은 top-level get만). **신규 리터럴 오류문자열 3 테스트는 전부 통과** (armB·재런은 실패).
- **버그 소재의 아이러니 (같은-마음 테제 frontier 승격)**: stale-캐시 근원은 4.1(ornith)+4.2(GPT) 결합부인데, 4.2는 **GPT가 구현하고 GPT가 검증한 유일한 태스크 쌍** — 하이브리드 런에서 같은-마음 구현/검증 페어링이 발생한 정확히 그 지점에 출하 버그가 서식. verifier는 직접 전이 케이스(X1→Y1→A1)는 잡았으나 비대칭 변형은 통과. held-out oracle(제3의 마음)만 잡음. **같은-마음 사각지대는 모델 등급 무관 — frontier에서도 재현.**
- **4.4 differential의 새 실패 모드 — "정직하되 무딘" 레퍼런스**: ornith의 NaiveSheet는 이번엔 진짜 독립 구현(380줄, 캐시 없음, 버그 복제 없음 — 재런의 글자 복제와 대조). 그러나 주소 풀 200셀 × 시퀀스 ~50 op = 의존 충돌 희박 → 1000 시드 0 mismatch. **풀을 12셀로 좁히면 자기 하네스가 21/100 시드에서 출하 버그를 잡음** — 파라미터 하나(밀도)가 잡느냐 놓치느냐를 갈랐고, GPT verifier도 밀도 문제는 못 봄. 같은-마음 시리즈의 3형태: 글자 복제(재런) → 테스트 맹점 공유(하이브리드 3.1, 교차-마음이 차단) → **적대적 밀도 감각 부재(하이브리드 4.4)**.
- **교차 변이 (사전 등록 확인 완료)**: **M7 KILL** — 세 same-mind 스위트가 전부 SURVIVED시킨 혼합 mis-order 변이를 hybrid 스위트가 2 테스트로 죽임(3.1 halt에서 GPT verifier가 강제한 B1:A2 테스트의 직접 산물). **M8 KILL** — armB의 출하 버그 변이를 10 테스트로 죽임(SUM 경로만 변이). 자체 스위트 281개.
- **사전 등록 대비 판정**: ① 완주+전 경계 메커니즘 이행 ✓ ② oracle ≥ armB(126) ✗ (119) — 단 실패가 단일 근원이고 그 근원이 same-mind 페어링 지점이라 "파편화 해악"으로 귀속 불가 ③ **교차-마음 verifier의 M7류 적발 ✓✓** (3.1 라이브 적발 + 변이 KILL 확인) ④ 처방 확립: **"구현은 로컬이어도 되고, verifier는 다른 혈통으로" — 단 예외 없이** (frontier 태스크도 verifier와 같은 마음이면 사각지대 부활). 부가 발견: 밀도 파라미터가 differential의 생사를 가름 → oracle/레퍼런스 설계 가이드에 "밀집 소구역" 명시할 것.

## HYBRID RERUN PRE-REGISTRATION (2026-07-13, 발사 대기 — anthropic 인증만 남음)

- **셋업**: `~/code/gridcalc-hybrid` — spec+plan을 재런 시드(`gridcalc-rerun@9d48592`)에서 verbatim 복사, loopspace **0.15.2**(`64eeb45`), **tier A**(프로파일 정합 — 재런의 tier C는 ornith 오케스트레이터 한계 때문이었고 이번엔 불필요). 라우팅: 오케스트레이터+verifier = `openai/gpt-5.5`(ChatGPT OAuth — Anthropic은 opencode OAuth 미지원이라 교체; OAuth 백엔드가 gpt-5.6·codex-spark를 거부해 Codex CLI가 쓰는 gpt-5.5로 확정, 텍스트+툴 스모크 통과. 교차-마음 조건 동일 충족 — 구현자 ornith / verifier GPT / oracle 저자 Claude로 **세 마음 분리**가 오히려 깨끗해짐), implementer = ornith 35B (opencode agent 설정: `implementer`/`verifier` 서브에이전트 분리, 프로젝트 opencode.json). ornith 클라이언트 타임아웃 300s→**900s**(0.15.0 재런 사망 원인 직접 처방). 러너 `gridcalc/hybrid_supervise.sh` (supervise.sh 0.15.2 래핑: stall kill 3600s + fast-fail 3×60s 명시).
- **0.15.0 재런 대비 변수**: loopspace 버전, 오케스트레이터·verifier 모델, tier, 타임아웃 — 다변수 n=1이므로 해석은 방향만. 목적 자체가 "타임아웃 계급 제거 + 순응 좋은 오케스트레이터에서 메커니즘이 뭘 하는가"의 관측.
- **oracle v2 (2026-07-13 보강)**: 리터럴 오류문자열 3 테스트 추가(r02 roundtrip, r06 참조 시 #TYPE! 연료, r08 range 내 취급) — 총 **134**. selftest(레퍼런스, r10 제외) 122 green. **재채점 기준선: solo 133/134, armB 126/134(신규 중 r06 실패), 0.15.0 재런 107/134(r06·r08 실패)** — 신규 테스트가 기존 프로브에서 본 위반과 정확히 일치하게 변별.
- **사전 등록 기준**:
  - Primary: oracle v2 134 채점. 강한 성공 = 완주 + 전 phase 경계 프로브·변이 실행 증거(저널) + oracle ≥ armB(126); solo(133)급이면 "순응 유지 시 루프 오버헤드 ≈ 0" 실증.
  - 교차-마음 검증 관측: frontier verifier가 ornith 구현의 M7류(혼합 mis-ordered range) 계열 맹점을 독립 인스턴스화/프로브에서 도출·적발하는지 — 같은-마음 테제의 처방("verifier만 다른 모델") 검증.
  - 이행 관측: 경계 부채·stale-handoff freshness 발동 여부(세션이 안 죽으면 무발동이 정상), fast-fail 무발동 기대, tier 자가 변경·패널 생략 재발 여부.
  - 실패 모드 해석: 완주했는데 oracle이 solo에 크게 못 미치면 → "파편화 자체 해악"의 최초 직접 증거로 등록.
- **프리플라이트 (2026-07-13)**: editable-install 오염 제거(재런이 남긴 `pip install -e` → gridcalc-rerun 지향; --break-system-packages로 uninstall, 중립 cwd에서 import 실패 확인), opencode 좀비 0, ornith :18081 서빙 확인, 시드 2커밋 + `loopspace/gridcalc/run` 브랜치 체크아웃. ~~잔여 블로커: 인증~~ → OpenAI ChatGPT OAuth 등록 완료(2026-07-14), gpt-5.5 텍스트+툴 스모크 통과. **발사: 2026-07-14** (`runner-logs/hybrid_supervise.log`).
- **중간 사건 1 (발사 ~1h, task-stall halt @ 2.1)**: phase 1은 교과서 이행 — verifier(GPT)가 1.1을 3연속 FAIL(invalid-address `set` 커버리지, failed-first TDD 증거 요구) 후 burst로 통과, **phase 1 경계 완전 이행**(프로브 4 + 변이 2 "went red" + 경계 커밋 + phase-2 브랜치). task 2.1(heavy 파서)에서 **ornith 구현자 6/6 빈 보고서 사망** — armB 1차 tier A의 2.1 reasoning-드롭 서명 그대로. **오케스트레이터를 GPT로 바꿔도 재현 → ornith heavy-디스패치 사망은 모델 속성으로 변수통제 확정.** 오케스트레이터는 절차대로 halt(보고서+선택지 3). 운영 결정: **Option B(2.1을 작은 파서 서브태스크로 재계획) 채택**(사용자 AFK, 설계 보존 우선) — halt-resume 세션 + supervisor 재부착 (2026-07-14).
- **중간 사건 2 (재계획 후 2차 halt) + 근원 확정**: 재계획은 정확히 이행됐으나(2.1→tokenizer/precedence/depth 3분할) 쪼갠 tokenizer 태스크에서도 ornith 3연속 빈 보고서(누적 9연속). 세션 DB 추적으로 **근원 확정: 실패 디스패치의 최종 출력 = 정확히 8192 토큰(출력 캡)** — qwen 계열 thinking이 캡을 다 소진해 본문 0으로 절단. phase 1 태스크는 95~292 토큰으로 여유. **"ornith reasoning-드롭"(armB 1차 2.1 halt 포함)은 모델 미스터리가 아니라 출력-캡 절단이었음** — 300s 타임아웃과 같은 인프라 계열. "요구 생각량과 상관"이라는 기존 관찰과 정합(생각 많음 → 캡 도달). 처방: ornith `limit.output` 8192→30000 (`gridcalc-hybrid@b03f578`), Option C(외부 수리 후 2.1 리셋 재개)로 2차 재개 (2026-07-14).
- **중간 사건 3 (3차 halt @ 2.1, 캡 수리 검증 + 새 병목)**: 캡 상향은 **작동** — ornith가 실구현 3종 산출(recursive-descent, Pratt; pytest green). 그러나 **GPT verifier의 tier A 기준을 6시도(3+burst 3) 내 미통과**: `=²` 유니코드 digit 함정, A01 커버리지 누락, failed-first 증거 포장 반복 부재. burst 3은 **900s 타임아웃**(캡을 올리니 30000토큰 생성이 시간 벽에 걸림 — 로컬 35B의 캡↔타임아웃 구조적 트레이드오프). 2.1 failed 확정. **판독: 루프 메커니즘·오케스트레이션은 건강, 병목은 순수 구현자 역량/속도 — "ornith 구현자는 쓸만" 결산은 '관대한 같은-마음 verifier 하에서만'으로 조건 붙음(엄격한 교차-마음 verifier 기준 미달).** 운영 결정(사용자 AFK, 추천안): **2.1 한정 implementer-frontier(gpt-5.5) 라우팅**(`gridcalc-hybrid@eedc0c7`) — 오염 최소·완주 우선, M7 관측(3.x/4.x 의미론)은 ornith 구현 유지로 보존. 3차 재개 (2026-07-14, `hybrid_resume3.sh`, nohup 분리 — 백그라운드-태스크 소유 시 하네스 정리에 런이 동반 사망하는 운영 함정 2회 확인).
- **중간 사건 4 (2.1 frontier 1발 통과 → 2.2에서 4차 halt = loopspace 설계 발견)**: GPT 구현자가 2.1을 **첫 시도 통과**(커밋 `0abd329`; ornith 6실패와의 역량 격차 데이터). 그런데 GPT가 파서를 서브태스크 경계 너머까지 통째 구현(precedence·함수·range 포함) → 후속 2.2의 ornith가 **구조적으로 불가능한 TDD 게이트**에 갇힘: 동작이 이미 존재해 failed-first 증거 생산 불가, verifier는 규정대로 FAIL 반복(6시도). **설계 함정 등록: 재계획 분할 + 강한 구현자의 경계 초과 구현 → 후속 서브태스크의 failed-first 전제 붕괴.** 0.16 후보: 경계 초과 구현 감지 시 후속 태스크를 coverage-only로 강등하는 규칙의 기계화. 오케스트레이터는 이 구조를 자가 진단하고 "coverage-only 좁은 예외"를 스스로 제안(러버스탬프 시도한 attempt 3을 FAIL시키는 무결성 유지). 운영 결정: 보고서 옵션 2 채택 — 2.2 coverage-only 재개, 2.3 동일 상황 시 halt 없이 동일 예외 (4차 재개, `hybrid_resume4.sh`).
- **중간 경과 (phase 2 완주)**: 2.2 ornith 2시도(coverage-only, verifier가 나눗셈 케이스 잡음), 2.3 ornith 2시도 — **면제 없이 "경계 검사 임시 제거→red 시연→복원"으로 failed-first 증거 자가 해결** (경계-초과-구현 교착의 일반해; 0.16 처방 후보로 격상), 2.4·2.5 ornith 통과(마찰 크지만 완주). **phase 2 경계 완전 이행**: 프로브 3 + 변이 2(went red) + freshness-note("3.1·3.2 미충족 확인" — 2.1 함정의 학습 전파) + 경계 커밋 `1ec818e`.
- **★ 중간 사건 5 (5차 halt @ 3.1) = 사전 등록 핵심 관측 적중**: verifier(GPT) 최종 finding — "`B2:A1`(완전 역순) 테스트만 있고 **`B1:A2`(열 역순·행 정순) 테스트 부재**" + MAX row-major 다중오류 케이스 부재. **M7 맹점 계열(혼합 mis-ordered range — 0.15.0 재런의 출하 버그이자 세 same-mind 스위트가 전부 SURVIVED시킨 클래스)을 교차-마음 verifier가 루프 안에서 적발.** ornith는 이번에도 완전-역순만 테스트(같은 혈통 = 같은 맹점 재현), GPT가 혼합-역순을 특정해 요구. **"verifier만 다른 혈통으로" 처방의 직접 실증 — 시리즈 테제의 응용 결론 성립.** 운영 결정: 보고서 옵션 1(누락 테스트 2개 + 필요시 B1:A2 검증 수리, 현 구현 방향 수용)로 5차 재개 (`hybrid_resume5.sh`).
- **중간 경과 (3.1 종결·phase 3 완주)**: 3.1 재개 1시도 PASS — **구현은 이미 성분별 비교(`start_col>end_col or start_row>end_row`)로 정답**, 맹점은 테스트에만 존재(B2:A1만 커버 — 같은 혈통 3번째 재현), B1:A2 테스트 2건 장착 → **채점 시 M7 변이 kill 여부 확인 예정**. 3.2 heavy **패널 정식 가동**(security/test-integrity/correctness 3렌즈, correctness는 evaluator stash→red 시연) 1시도 PASS. **phase 3 경계 완전 이행**: `probes_phase_3.py`(0.15.0 재런이 타임아웃 사망으로 영영 못 만든 그 파일) + 변이 2 red + structure-note(죽은 코드 경로 → phase 4 청소 위임).
- **중간 사건 6 (6차 halt @ 4.1, R10 구간)**: verifier가 ① **뒤 태스크(4.2)와 모순되는 테스트 적발**(unrelated-set 후 비영 delta 단언 — 태스크 간 의미론 인지) ② non-formula set의 eval_count 불변 커버리지 부재 ③ **가짜 red-phase 증거 적발**("그 테스트는 구현 전에도 통과 — failed-first 증거 불성립"). 원런·재런에서 같은-마음 verifier가 세탁하던 지점이 교차-마음에선 차단됨을 반복 실증. 시도 중 빈 보고서 2건(캡↔타임아웃 잔존 비용). 운영 결정: 옵션 1(방향 유지+모순 테스트 제거+커버리지+진짜 증거)로 6차 재개 (`hybrid_resume6.sh`).
- **★ 중간 사건 7 (7차 halt @ 4.2) = 사전 등록 관측 2번째 적중**: 4.1은 재개 후 통과. 4.2에서 correctness verifier가 **전이적 무효화 버그를 구체 재현으로 적발**(`X1=Y1+1, Y1=A1+1`, A1 수정 → X1 stale) — **재런의 출하 버그 2번(사이클×캐시 stale)과 동일 클래스가 루프 안에서 차단됨.** ornith는 실접근 5종(역의존 그래프·dirty set·클로저 캐시) 시도했으나 전이 케이스 미해결, 6디스패치 소진. 운영 결정: 2.1 선례(6디스패치 실패 → 해당 태스크만 frontier) 동일 적용 — 4.2를 implementer-frontier로 (`gridcalc-hybrid` 커밋, `hybrid_resume7.sh`). 4.3·4.4(differential 관측 대상)는 ornith 유지.

## RERUN RESULTS (2026-07-13, loopspace 0.15.0 validation — 사전 등록 기준 미충족, 대신 테제의 최강 증거 획득)

- **셋업**: `~/code/gridcalc-rerun` (아카이브 `../rerun-loopspace-0.15/`), arm B와 동일 spec+plan, 유일 변수 = loopspace 0.15.0 (spec 프로브 + 변이 스팟체크 + verifier 독립 인스턴스화). tier C 시드(원런 완주 구성) — ornith가 중간에 **스스로 tier A로 승격**. 세션 6개, 벽시계 ~11h — 그중 **6.5h는 세션 3 행**(출력 없는 LLM 호출 루프, 파일 무변화; supervisor는 프로세스 생존 중엔 무진전을 못 봄 → 운영자 개입 1회: 17:48 KST hang kill). 종료도 complete가 아니라 **STUCK exit**(전 태스크 done·phase 4 verified인데 세션 5·6이 마무리 장부를 못 함; 4.2-4.4 미커밋 → grader 커밋 483184b로 보존). 런 중 `pip install -e` 오염 재발(제거 후 채점).
- **oracle: 106/131** (25 실패) — solo 130, 원런 arm B 124보다 나쁨. 근원 3개(전부 재현·코드 확정): ① R7 혼합 mis-ordered range 수용 — `evaluator.py`의 사전식 튜플 비교 `(start_col,start_row)>(end_col,end_row)`; B2:A1(완전 역순)은 잡고 A3:C1(열 정순·행 역순)은 통과→빈 range 0. 24건 중 대부분. ② 사이클×캐시 무효화 누락(stale 값, ~9셀). ③ R10 카운트 이상(사이클 첫 평가 delta 2; `=1/0+Y1` get에 delta 0).
- **백미 — 같은-마음 테제의 최순수 실증**: 4.4가 이번엔 진짜 NaiveSheet 레퍼런스(370줄, 평가 의미론 독립 구현)를 만들었는데, **① 버그의 사전식 비교가 test_differential.py:161에 글자까지 동일하게 복제**돼 1000 시퀀스 zero mismatches. 같은 마음이 쓴 "독립" 레퍼런스는 같은 오해를 공유한다 — held-out oracle(다른 마음)만 잡았다.
- **0.15.0 메커니즘 이행 스펙트럼**: phase 1·2 = 완전 이행(probes_phase_{1,2}.py 실작성·실행, 변이 스팟체크 "suite went red" — 잡을 버그가 없던 구간). phase 3 = **경계 소실 — 단 원인은 순응 실패가 아니라 백엔드 타임아웃 사망**(아래 포렌식 정정 참조; 초기 기록의 "세션 2가 턴 종료"는 부정확). phase 4 = 부분 이행(경계는 밟되 프로브·변이 생략 — 이쪽은 순응 실패 맞음). **버그들은 정확히 이행 공백(phase 3·4 의미론)에 서식** — 메커니즘 실패가 아니라 호출 실패이되, phase 3은 인프라 몫·phase 4는 순응 몫으로 갈림.
- **포렌식 정정 (2026-07-13, opencode.db 세션 저장소)**: 세션 2(`ses_0a73b3d31ffe…`, 08:58–10:22 KST)는 3.2 커밋 후 phase 3 경계를 **정확히 인지하고 Phase 3 verifier를 디스패치했다**(10:12, reasoning에 "dispatch the phase verifier" 명시). verifier(`ses_0a6f41861ffe…`, 10:16:20 시작)는 ~5분간 정상 진행(구현·테스트 독해, spec 프로브 도출)하다 10:21:39 write 툴 호출이 error, 직후 LLM 호출이 **"The operation timed out."**(300s)으로 사망 — `probes_phase_3.py`가 없는 이유. 오케스트레이터의 다음 호출(10:22:21)도 **정확히 300초 뒤 parts 0개 + 동일 타임아웃 에러**로 종료. 저널·경계 커밋·handoff 아무것도 못 남김 → 재개 세션(10:27)은 "전 태스크 done + `[phase 3] verified` 부재"에서 4.1 직행(0.15.1 이전이라 경계 부채 재도출 없음). 근원은 로컬 llama-server 지연(verifier 컨텍스트 최대 시점의 프롬프트 처리 및/또는 단일 슬롯 큐잉 — 어느 쪽인지는 미확정, 300s 클라이언트 타임아웃 2연속은 확정). **함의**: ① "ornith 오케스트레이터 순응 병목" 결산에서 phase 3 건은 제외해야 함(인프라 몫) ② 세션 3의 6.5h 행("출력 없는 LLM 호출 루프")도 같은 타임아웃 계급일 개연성 ③ 0.15.1 경계 부채는 방아쇠 불문 손실 영구화를 막으므로 오히려 더 정당화됨 ④ frontier 백엔드 하이브리드 재런은 이 실패 계급이 통째로 부재한 조건이 됨.
- **검증이 산 것(실증)**: 3.2 attempt 2에서 heavy 패널이 실버그(자기-포함-범위 사이클 #PARSE!, range 셀 평가의 사이클 감지 우회)+무테스트 기준 3개를 FAIL로 강제 → attempt 3 수리. 그 결과 **재런에는 원런의 강등 버그가 구조적으로 부재**(range 멤버가 오류-전파 경로로 통일됨).
- **품질 3자 비교** (`mutate.py`/`mutate2.py`, 사본 대상): 구현 LOC 737/763/837(solo/armB/rerun), 자체 테스트 188/161/174개. 거친 변이 6종(÷내림, 좌단락제거, range순서off, 사이클→0, 문자셀→0, 카운트off)은 **세 스위트 전부 6/6 KILL** — 빈껍데기 아님. **출하-버그 교차 변이가 변별**: M7(혼합 mis-order, 재런의 버그)은 **세 arm 스위트 전부 SURVIVED** — 같은 모델의 세 마음이 같은 맹점을 공유, held-out oracle만 잡음. M8(range 오류 강등, 원런의 버그)은 solo 스위트 5개·재런 스위트 **31개** 테스트가 KILL(armB는 출하) — 재런 스위트가 오류-전파 계열에선 최강 방패(패널 FAIL 강제 테스트+프로브의 직접 산물). 의미론 프로브 6종: solo 6/6, armB 4/6, rerun 3/6(혼합 mis-order, 리터럴 오류문자열→오류 취급, 카운터-가시 단락 위반). dead defs: solo 1(미사용 헬퍼), armB 0, rerun 2(미사용 wrapper·예외클래스). **결론: 이 규모·백엔드에선 비용이 출하 품질로 회수되지 않음. 루프가 산 것은 "발화한 지점의 테스트 방패"(M8 31 killers)와 프로세스 무결성이며, 출하 정확도는 solo 우위 지속.**
- **부수 관찰**: 저널 형식 표류(3.1 엔트리 누락, 항목 재기록·순서 뒤섞임), state.md risk 칼럼 셔플, 4.2를 heavy인데 단일 verifier로 통과(패널 생략), 4.4 acceptance "no shared code" 부분 위반(parser 공유)을 verifier가 관대 통과, 리터럴 오류문자열을 오류값 취급(spec 명시 위반 — oracle에도 이 케이스 없음: oracle 갭).
- **처방(0.15.1 후보, 태스크 등록됨)**: ① 경계 의무 상태-도출(이전 phase 전부 done + `[phase N] verified` 저널 부재 → 태스크 선택 전에 경계 먼저) ② supervise.sh liveness 타임아웃(state/journal mtime N분 무변화 → kill·재시작) ③ (검토) heavy 패널 생략 방지도 같은 계열 — 이행을 프롬프트가 아니라 기계로. [①② → 0.15.1로 출하, `loopspace@8190272`]
- **처방(0.15.2 후보, 포렌식 정정에서 파생)**: ① **stale-handoff 대응** — 세션이 handoff를 못 쓰고 죽으면 handoff.md는 이전 경계 것이 남는데, loopresume이 이를 최신으로 신뢰하면 오도됨. 재개 시 handoff.md의 신선도를 저널·state 대비 검사하고, stale이면 "저널+state+git log에서 재구성" 경로를 명시 강제 ② **로컬 백엔드 타임아웃 대응** — supervise가 타임아웃-사망(에러 종료)을 감지하면 즉시 재기동(현행도 재기동은 하나 로그에 사인 미기록), 반복 시 백오프·운영자 알림; 근본적으로는 verifier 프롬프트의 파일 독해량 절제(컨텍스트 최대 시점이 사망 시점).

## RESULTS (2026-07-12, both arms complete)

- **arm B (loopspace)**: completed 11/11 tasks, one supervised run, wall
  ~5.9h (incl. ~2h tier-A stall on 2.1 — ornith reasoning-drop on heavy
  subagent dispatches; finished under tier C role-swap). Own suite 161
  green. **Oracle 124/131.** All 7 failures share one root cause:
  `#REF!`/`#CYCLE!` degraded to `#TYPE!` when a formula references an
  error-bearing cell — latent since phase 2-3 (R11 was never fully green),
  so *not* a phase-4 regression. Trajectory (17 snapshots,
  `../armB-loopspace/trajectory.csv`): monotonic 18→124, **0 drift
  events**. Coherence findings: 4.2-4.4 finished but left uncommitted at
  `run_status: complete` (preserved via labeled grader commit
  `gridcalc-trial@93457e0`); run branch never advanced past plan-approval;
  tier-C journal entries show weak failed-first evidence (4.2 "tests
  adjusted to match actual behavior", 4.3/4.4 none).
- **arm A (solo)**: declared `<DONE>` after **one 40-minute session** —
  the multi-session boundary was never crossed. Own suite 188 green.
  **Oracle 130/131** (single failure: R10 error-result caching —
  eval_count 2 where 1 expected). Kept a 46-line structured NOTES.md
  (status / architecture / 7 design decisions / limitations) that was
  never consumed by a later session. Trajectory: seed→final, 0 drift
  events (trivially).
- **Primary criterion: oracle delta B − A = 124 − 130 = −6/131 (−4.6pp)**
  — first nonzero correctness delta of the series, **in solo's favor**.
- Measurement note: a stray `pip install -e` (arm B created setup.py and
  self-installed into site-packages) made pre-code snapshots fall back to
  the live repo on import, contaminating the first trajectory pass —
  uninstalled and regraded. Protocol addition: preflight
  `python3 -c "import <pkg>"` must FAIL before grading.

### Verdict vs pre-registration

The premise did not engage: gridcalc fits in one ornith context when
built directly, so arm A faced zero drift pressure — none of the three
pre-registered interpretations applies cleanly. What was actually
measured is **harness overhead vs direct build at one-shottable scale**:
loopspace consumed ~9x wall clock, hit a backend-specific tier-A stall,
and its per-task decomposition let a cross-phase error-propagation bug
survive every per-task verifier (each task's local tests passed; the
composed semantics were wrong). Solo held the whole error-semantics model
in one context (NOTES decision #6 is exactly the semantics arm B got
wrong) and passed R11 clean. Caveats: n=1 per arm; arm B ran tier C
(weakened verifier isolation) after the tier-A stall; the delta is one
root-cause bug, not diffuse decay. The structural drift claim remains
untested — testing it requires a task that genuinely overflows a solo
context window (a W′ would need ~3-5x this size).

## Question

Four experiments in, every correctness delta is 0 and the one axis
loopspace lost on (intra-phase coherence) has been repaired and verified.
The remaining untested claim is loopspace's *structural* core: that
fresh-agent-per-task + handoff discipline survives runs **too big for one
context window**, where a solo build must cross session boundaries and can
drift — forget early invariants, regress finished features, lose unwritten
decisions between sessions. This is the last axis on which a correctness
delta is plausible for a capable model on a well-specified task.

## Task: `gridcalc` — mini spreadsheet engine, 4 phases / 10-11 tasks

Drift pressure is built into the structure: each phase forces revisiting
the previous phases' evaluation path.

- **Phase 1 — cell store** (2 tasks): A1-style addressing, literal
  set/get, types (number / string / empty).
- **Phase 2 — formulas** (3 tasks; parser `heavy`): `=A1+B2*2` grammar
  (arithmetic, parentheses, comparison), cell references, full recompute
  on read, error values (`#REF!` etc.) with propagation.
- **Phase 3 — ranges, functions, cycles** (3 tasks; cycle detection
  `heavy`): `SUM(A1:B3)`-family over ranges, circular-reference detection
  → `#CYCLE!` (self-reference, 2-cycles, cycles through ranges).
- **Phase 4 — incremental recompute** (2-3 tasks; `heavy`): dependency
  graph + dirty propagation. An `eval_count` counter is part of the public
  API so incrementality itself is acceptance-testable ("editing a cell
  outside A's dependency closure re-evaluates nothing on read of A").

Phase 4 is the designed trap: it rewrites the phase 2-3 evaluation path
while the *results* must stay identical — drift shows up precisely as
regressions on early requirements.

Sizing: kvtx rerun did 2 tasks in ~1-1.5h on ornith (opencode, Tier A), so
10-11 tasks ≈ 6-8h ≈ one overnight per arm. Budget: one unattended night
per arm, arm B first (daytime left for debugging if the harness fails),
arm A the next night.

## Arms — the only variable is the execution machinery

Both arms receive the **identical SPEC.md + PLAN.md** (frontier-authored:
Claude Code via loopspec → loopplan, then the same content seeded to arm
A) — Experiment X/Z isolation structure. loopspace version: 0.14.0 +
`d21f392` (reuse check judges from the tree) + `0d2cd3a` (templates
dispatched verbatim).

- **Arm B (loopspace)** — `~/code/gridcalc-trial`: ornith runs looprun
  under **loopsupervise** (unattended; context-threshold handoffs happen
  without a human typing /clear). Task/phase checkpoint commits are the
  built-in snapshots.
- **Arm A (solo)** — `~/code/gridcalc-solo`: a shell loop of repeated
  `opencode run` calls; each iteration is a fresh session. Prompt: read
  SPEC.md/PLAN.md, continue the implementation from the repo state; you
  MAY keep a free-form progress-notes file if you find it useful (allowed,
  never forced — the "self-managed notes" baseline); print `<DONE>` when
  you judge the project complete. The loop commits the tree after every
  session (snapshot), runs `pkill -9 -f opencode` between iterations
  (zombie GOTCHA), and stops on `<DONE>`, 12 sessions, or 8h, whichever
  comes first.

Fairness notes: arm A's notes policy is deliberately permissive — if solo
survives *because* it kept good notes, that is an honest finding about
what the structured handoff is worth. Non-completion (stall, loop,
premature `<DONE>`) is a valid outcome, not a broken run.

## Grading: held-out oracle, authored before either arm runs

Independently authored (never shown to either arm) and committed to this
directory **before** any run starts — pre-registration. Components:

1. **Brute-force reference** (~100 lines, embedded in the oracle): no
   dependency tracking; every read naively re-evaluates recursively.
   Self-tested green before use.
2. **Named killer cases**: reference-update chains, formula cells inside
   ranges, self-reference / 2-cycle / cycle-through-range, error
   propagation, mixed types, empty-cell semantics.
3. **Randomized sequences**: 40+ random set/formula/read command
   sequences cross-checked against the reference.
4. **Incrementality checks**: `eval_count` upper bounds (phase-4 R-ids
   only).
5. **Every assertion tagged with its R-id group** — enables per-phase
   pass rates per snapshot.

## Trajectory grading — the drift signature

A grading script walks each arm's full commit history: checkout →
run oracle → emit `(snapshot, R-group, pass/fail)` CSV. **Drift event :=
an R-group that passed at snapshot t fails at some t+k.** Even a final
delta of 0 leaves a trajectory comparison (wobbled-and-recovered vs
never-wobbled), which is exactly the information the endpoint-only
experiments couldn't produce.

## Pre-registered verdict criteria

- **Primary**: final held-out oracle pass-rate delta (B − A).
- **Secondary**: drift-event count per arm; sessions consumed; completion
  (did the arm finish at all); arm A's actual notes behavior (did it keep
  notes, were they load-bearing); arm B's handoff quality (journal +
  handoff.md against what the next session actually needed).
- **Interpretations fixed in advance**:
  - Delta > 0 with arm A drift events → loopspace's structural claim
    validated on the local backend; the series ends with a demonstrated
    correctness value.
  - Delta 0 and zero drift events both arms → ornith holds even at
    multi-session scale; final series verdict: loopspace's value for a
    capable model is process/integrity insurance + unattended operation,
    not correctness. This closes the series honestly.
  - Arm A non-completion (stall/loop) with arm B completion → counts as
    a delta in kind: the harness's value is *finishing at all*.

## Operations

- Night 1 = arm B, night 2 = arm A (B first: harness failures get
  daylight).
- Pre-flight (both nights): `pkill -9 -f opencode`; confirm ornith serving
  on :18081 (`llm ornith` if not); prompt pins the project cwd and
  ".loopspace/ resolves there" (headless GOTCHA).
- During B's first task, check the opencode session store (`part` table)
  for the template A contract sentence — verifies the `0d2cd3a`
  verbatim-dispatch reinforcement on a real run.
- Locations: `~/code/gridcalc-trial` (B), `~/code/gridcalc-solo` (A),
  oracle + this design in `gridcalc/grading/` (this repo), run archives
  to `gridcalc/armB-loopspace/`, `gridcalc/armA-solo/` after grading.

## Pre-registration record (2026-07-12)

- Spec authored via loopspec: 3 panel rounds (r1: 6 blocking roots —
  function grammar missing, ref-token classing, COUNT contradiction,
  string-flow hole; r2: 3 blocking — set(X) contradiction, closure
  measurement timing, depth definition; r3: 2 blocking fixed post-panel —
  integer-magnitude bound, literal-edit carve-out). Approved
  `gridcalc-trial@f933d38`.
- Plan authored via loopplan: 4 phases / 11 tasks, heavy = 2.1 parser,
  3.2 cycles, 4.2 dirty propagation. 2 panel rounds (r1 blocking: task
  2.1's #PARSE! tests would die at phase 3 — fixed by pinning only
  forever-invalid inputs and pulling R12 sizing into 2.1/2.2). Approved
  `gridcalc-trial@1099c8a`.
- Oracle: `gridcalc_ref.py` (naive reference, ~250 LOC) +
  `gridcalc_oracle.py` — 47 test functions / 131 executed assertions,
  R-group-tagged (`test_rNN_*`); 40 seeded differential sequences vs the
  reference; R10 (12 checks) asserted against the arm only. Self-test
  (reference graded against itself via `selftest_shim/`, R10 excluded):
  **119/119 green**.
- Trajectory grader: `grade_trajectory.py` — per-commit × per-R-group
  CSV + drift-event detection; smoke-tested on the pre-code trial repo
  (3 snapshots, import-fail rows as expected).
- Neither arm has run yet as of this record.

## Order of work

1. Author SPEC.md via /loopspec, PLAN.md via /loopplan (arm B repo);
   copy both into arm A's seed. Human approves both (last touchpoints).
2. Author + self-test the oracle and the trajectory grading script;
   commit here (pre-registration).
3. Night 1: arm B under loopsupervise. Morning: sanity checks.
4. Night 2: arm A under the session loop script.
5. Trajectory-grade both, archive, write results into this file +
   EXPERIMENTS-LOG.
