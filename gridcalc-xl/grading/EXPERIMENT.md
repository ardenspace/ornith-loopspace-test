# Experiment W′: 3-arm structure dose-response at overflow scale (gridcalc-XL)

written: 2026-07-15 (design; runs pending) · follows W (gridcalc: solo 우위
at one-shottable scale, premise 미발동), rerun (0.15.0: 같은-마음 최순수
실증), hybrid (0.16 근원: 교차-마음 처방 실증, oracle 밀도 발견). 설계
확정 대화: 2026-07-15 Telegram (섹션별 승인 완료).

## Question — 시리즈 마지막 미검증 주장 + 새 질문 하나

1. **구조 주장 (W의 미발동 전제 재도전)**: 솔로 컨텍스트가 실제로
   넘치는 규모에서는 구조(loopspace)가 이긴다 — 현재 n=0. W에서 solo가
   40분 원샷으로 끝나 전제가 발동하지 않았다.
2. **thin-harness 질문 (신규)**: 모델이 강해진 지금, 하네스는 얼마나
   얇아도 되는가. 철학 전환 후보 — 유지: *Keep context light, verify
   heavy.* 신규: *Give autonomy. Enforce invariants.* 하네스는 과정을
   지휘하지 않고 결과의 경계(invariant)만 기계로 감시한다.

두 질문을 한 런에 합치는 설계 = **3-arm dose-response**: 구조 용량을
solo(0) → thin(invariant만) → thick(0.16 전체 지휘)으로 증가시키며
overflow 규모에서 비교.

## 설계 결정 기록 (2026-07-15, 승인 순서대로)

- 실험 방향 **B**: thin 모드(loopspace 0.17)를 먼저 만들고 3-arm으로.
  (A: 원안 2-arm은 "invariant 덕 vs 지휘 덕"을 못 가름; C: 재설계만
  먼저는 검증 없는 출하)
- thin invariant 집합 **옵션 2**: 결과 감시 + 자율 선언 체크포인트마다
  교차혈통 검증. (옵션 1 "결과만"은 늦은 적발 — W arm B의 R11이 phase
  2-3부터 잠복한 전례; 옵션 3 "0.16 뺄셈"은 dose 변별력 부족)
- 라인업 **A**: solo=ornith / thin=gpt-5.5 lead / thick=하이브리드 재사용.
  Gemini 기각(코딩 능력·CLI 부재), Claude는 opencode 미접속이나
  체크포인트 게이트는 opencode 밖 스크립트라 `claude -p`로 호출 가능.
- thin 체크포인트 verifier **A = Claude CLI**: 강함 + GPT lead와
  교차혈통. 비용 = verifier·oracle 같은-마음(아래 Limitations).
  (B ornith는 게이트가 이빨 없음 — "장식 게이트를 가진 thin"을 측정하게
  됨; C GPT 독립 인스턴스는 처방 정면 위반)
- 과제 **A = gridcalc-XL**: sizing이 측정된 유일한 선택지(1x = ornith
  원샷 40분 실측) → 전제 미발동 재발 리스크 최소 + spec·oracle·변이
  하네스 프리픽스 재사용. (B mini-DB: sizing 무측정; C 인터프리터→
  컴파일러: differential용 프로그램 생성기 신작 + oracle 기계 성분 최약)
- 규모 **b = ~4x**: 10 phase / ~28 task / ~3000 LOC 추정. 치명 리스크는
  비용이 아니라 전제 미발동 재발 — 하룻밤 더가 W 무효 재발보다 싸다.

## Thin mode — loopspace 0.17 "lead mode" (선행 구현 대상)

lead agent가 받는 것: **approved spec + acceptance criteria(R-id 그룹) +
budget**(서브에이전트 디스패치 상한, 벽시계 상한, 체크포인트 최소 수).

**lead의 자율 (하네스 불개입)**: ① 태스크 분해 — 첫 행동으로 자기
계획을 저널에 기록(인간 승인 없음, 관측용) ② 서브에이전트 사용
여부·시점(ornith 구현자를 쓸지 직접 할지 포함) ③ per-task 검증 방식
(self-check든 TDD든 자유 — 하네스는 과정에 노 코멘트).

**기계로 집행하는 invariant 5**:

1. budget 집행 + liveness/stall 감시 (supervise 계열 재사용)
2. **자율 체크포인트 게이트**: lead가 "acceptance 그룹 X 완료" 선언 시
   하네스가 `claude -p` verifier 호출 — 독립 프로브 도출·실행 + 변이
   스팟체크 + 체크포인트 커밋. FAIL → finding 반환(수리 후 재게이트),
   같은 게이트 3연속 FAIL → halt (TG 알림).
3. **체크포인트 최소 밀도**: 완주 선언까지 최소 N회(acceptance 그룹 수
   기반, W′에선 phase당 1회 상당). "게이트 없이 완주 선언"을 기계로
   차단.
4. 컨텍스트 임계 handoff + freshness 검사 (0.15.2 규율 유지 — 세션 죽음
   강건성은 thin이어도 포기하지 않음)
5. **완주 게이트**: run complete 전 최종 교차혈통 검증(acceptance 전체
   스윕) + 클린 트리·장부 완결 확인.

구현 범위: looprun의 지휘 로직(태스크 선택·디스패치 강제·TDD 안무)을
lead 프롬프트에서 제거 + 게이트 스크립트(claude -p 래핑) 신작 +
supervise 확장. loopspec·TG 알림 재사용. 구현·태스크는 loopspace 저장소
(0.17)에, 설계 원본은 이 문서.

## Arms — 공통 입력 = 동일 SPEC.md + acceptance criteria

- **S (solo)** — ornith 세션 루프(W 방식, solo_loop.sh 계열): spec만
  시드, **plan 미제공**(thin이 self-plan이므로 대칭 — plan은 thick 구조의
  일부로 간주). 계획·노트 자유(허용, 강제 없음), 세션마다 스냅샷 커밋,
  `<DONE>`/세션 상한/시간 상한에서 종료. 전제 발동(진짜 넘침) 담당.
- **T (thin)** — loopspace 0.17 lead mode: gpt-5.5 lead + Claude CLI
  체크포인트 게이트 (위 절 그대로).
- **K (thick)** — loopspace 0.16 하이브리드 구성 재사용: gpt-5.5
  오케스트레이터·verifier × ornith 구현자, heavy 태스크
  `implementer_fallback:` 선언, loopplan 인간 승인 포함.
- **oracle 저자 = Claude** (강제 확정: 세 arm의 구현 마음이
  ornith·GPT를 다 소진 — 남는 제3의 마음이 Claude뿐. oracle 저작은
  런타임이 아니라 사전 작업이라 opencode 접속 불요.)

해석 구조: **T vs K** = 구조 용량 dose-response(둘 다 frontier-led라
깨끗한 비교). **S vs T·K** = "넘치는 규모에서 완주/정확도가 나오는가"
(모델 교란은 Limitations에 명기 — solo만 로컬 모델).

## Task: `gridcalc-XL` — ~4x, 10 phases (프리픽스 4 + 신규 6) / ~28 tasks

phase 1-4 = 기존 gridcalc spec 프리픽스 재사용 (cell store / formulas /
ranges·functions·cycles / incremental recompute). 신규 6:

- **Phase 5 — 문자열 함수·타입 확장** (CONCAT/LEN/IF 계열): evaluator
  재작성 압력.
- **Phase 6 — 절대참조(`$A$1`)·named range**: 파서 재작성.
- **Phase 7 — undo/redo**: 커맨드 저널 — eval_count 의미론과 충돌하는
  설계 함정(undo가 캐시·카운터와 상호작용).
- **Phase 8 — ★multi-sheet 교차 참조**: 심어둔 abstraction trap — phase
  1의 A1 주소 모델이 단일 시트 가정이라 전 코드베이스의 주소 표현이
  개정됨. "초기 abstraction 오류의 전파" 관측 지점.
- **Phase 9 — 영속화 round-trip**: 직렬화가 수식·오류값·eval 의미론을
  보존해야.
- **Phase 10 — recalc v2**: topological + volatile 함수(NOW 류) — phase
  4 dirty propagation 재작성 (W의 phase 4 함정 확장판).

세부 태스크 분할·acceptance 문안은 loopspec 패널에서 확정.

## Grading: held-out oracle v3 (Claude 저자, 런 전 커밋 = 사전 등록)

- gridcalc oracle v2 134케이스를 phase 1-4 프리픽스로 재사용 + 신규
  R-group 확장 — 목표 ~300+ 어서션.
- brute-force 레퍼런스 확장(naive 재평가; multi-sheet·undo·persist
  포함). selftest green 후 사용.
- seeded differential: **밀집 소구역 원칙** — 좁은 주소 풀(12셀급) ×
  시트 2-3장, 시퀀스에 undo·round-trip 삽입. (하이브리드 4.4의 발견:
  풀 200셀 = 1000시드 0 적발, 12셀 = 21/100 적발 — 밀도가 differential의
  생사를 가름.)
- 변이 하네스(mutate.py 패턴) + 종료 후 교차 변이 채점(각 arm의 출하
  버그로 변이 제작 → 타 arm 스위트가 죽이는지).
- trajectory 채점: 전 커밋 × R-group CSV, drift event 정의 동일 (t에
  통과한 R-group이 t+k에 실패).

## Pre-registered verdict criteria

- **Manipulation check (판정 전 관문)**: S가 실제 4+ 세션을 소비했는가.
  미달 = 전제 미발동 분기 — 실험 무효가 아니라 "이 규모도 원샷 가능"
  데이터로 등록 (해석 ⓒ).
- **Primary**: 최종 held-out oracle 3-arm 비교 (S vs T vs K).
- **Secondary**: drift-event 수(arm별), 완주 여부, halt 수·성격, 벽시계·
  비용, thin 체크포인트 게이트의 적발 내역(살아있는 invariant인지 장식인지),
  S의 노트 행동(유지했나, load-bearing이었나).
- **해석 분기 (사전 고정)**:
  - ⓐ S 미완주/유의미 drift + T·K 완주 → 구조 주장 성립. 그 안에서
    oracle T ≥ K → **"thin으로 충분"** = 0.17 방향 확정; K > T →
    과정 지휘도 값어치 있음(0.16 유지 근거).
  - ⓑ S 완주 + oracle S ≥ T·K → 4x에서도 solo 우위. 구조 주장 기각
    방향 — 하네스의 가치는 통합성 보험·무인 운영으로 재정의하고 시리즈
    종결.
  - ⓒ 전제 미발동(S가 1-3세션 완주) → 규모 데이터로 등록. 판정은
    "one-shottable 경계가 4x 이상"으로 한정, 구조 주장은 미검증 유지.

## Limitations (사전 명기)

- **thin의 게이트 verifier와 oracle이 같은 마음(Claude)**: Claude가
  놓치는 클래스는 oracle도 놓칠 수 있음 → thin에 유리한 방향의 편향이라
  더 위험. 완충: oracle의 기계 성분(brute-force differential·변이·밀집
  풀) 비중 최대화 + 교차 변이 채점. Gemini 확보 시 W″에서 해소 가능.
- **S만 로컬 모델**: S vs T·K 델타는 구조+모델 합산 — "로컬 모델이
  자기 컨텍스트보다 큰 일을 구조로 완주하는가"라는 질문으로 읽어야
  하고, 순수 구조 효과는 T vs K에서만 깨끗.
- n=1 per arm. 해석은 방향까지만.

## Operations

- **함정 선반영 (carry-over 4종 + 0.16 신기능)**: ornith `limit.output`
  30000·클라이언트 타임아웃 900s(프로젝트 opencode.json — 글로벌 300s
  유지 중이므로 반드시 프로젝트에서 상향), 러너는 nohup 완전 분리(Claude
  Code 백그라운드 태스크 금지), 감시 스크립트 pkill은 브래킷 트릭
  (`openc[o]de`), 채점 전 `pip install -e` 오염 확인(`python3 -c
  "import <pkg>"`가 중립 cwd에서 FAIL해야). `LOOPSPACE_TG_BOT_TOKEN`/
  `CHAT_ID`로 halt를 폰에서 결정.
- **런 순서**: 밤1 = T(신작 0.17 하네스라 리스크 최대 — 낮에 디버깅
  여지), 밤2 = K, 밤3 = S. thick은 1-2박 연장 가능성 예산에 포함.
- **아카이브 패턴 (확정 관례)**: 각 런 종료 후 트리 스냅샷 + `git
  bundle`을 이 저장소 아카이브 디렉토리로 흡수 (2026-07-15 폴더 정리에서
  확립 — 세션 포렌식 DB는 전역 `~/.local/share/opencode/opencode.db`).
- 위치: 런 저장소는 `~/code/gridcalc-xl-{solo,thin,thick}`, oracle·설계는
  `gridcalc-xl/grading/`(이 디렉토리), 아카이브는 `gridcalc-xl/` 하위.

## Order of work

1. **loopspace 0.17 lead mode 구현 + 테스트** (loopspace 저장소; 게이트
   스크립트 `claude -p` 스모크 포함).
2. gridcalc-XL SPEC.md — loopspec 패널 (phase 1-4 프리픽스 재사용 + 신규
   6 phase; acceptance R-id 그룹핑이 thin 체크포인트 단위가 되므로 그룹
   경계를 명시적으로).
3. oracle v3 확장 + selftest + 변이 하네스 이식; **이 디렉토리에 커밋 =
   사전 등록** (성공/실패 기준 이 문서에 이미 고정).
4. 런 3박 (T → K → S), 각 런 프리플라이트: pkill·ornith :18081·프로젝트
   opencode.json 확인.
5. trajectory 채점 + 교차 변이 + 아카이브(스냅샷+bundle) + 이 문서에
   RESULTS 절 추가 + EXPERIMENTS-LOG UPDATE.
