# 세션 핸드오프 — 2026-07-16: oracle v3 사전 등록 + T 런 준비 완료, 다음 = ④ 런 3박 실행

목적: 이 파일 하나로 다음 세션이 이어갈 수 있게. `SESSION-HANDOFF-2026-07-15c.md`를
대체함 — 그쪽 순서의 ②(SPEC)와 ③(oracle v3)이 종결됨. W′ 설계 전문은 여전히
`gridcalc-xl/grading/EXPERIMENT.md` (변경 없음).

## 이 세션에서 일어난 일 (요약)

1. **oracle v3 사전 등록 완료** (커밋 `d7cdb52`, main 푸시됨). 전부
   `gridcalc-xl/grading/`:
   - `gridcalc_xl_ref.py` — naive `RefWorkbook`, SPEC 전체 의미론의 독립
     2차 구현 (typed 평가 / copy 텍스트 재작성 / per-sheet name /
     undo·redo 저널 / multi-sheet / 영속화 / clock). eval_count 비모델.
   - `gridcalc_xl_oracle.py` — **450케이스**: v2 134 이식(델타 4 적용) +
     R13–R28 직접 어서션 + 밀집 소구역 differential(12셀 = A1·A2·B1·B2 ×
     시트 3장, undo·copy·name·clock·round-trip 인터리브, ValueError
     패리티). 기본 120시드, 딥 채점은 `GRIDCALC_XL_DIFF_SEEDS=1000`.
     카운터 패턴 30개는 `counters` 마커(selftest 제외; arm에는 실행).
   - selftest: `PYTHONPATH=.:selftest_shim pytest gridcalc_xl_oracle.py
     -m "not counters"` → 420 passed; 딥 1000시드 1.3s green.
   - `grade_trajectory.py` 이식 + 가짜 arm(레퍼런스 백킹) 2커밋 워크로
     엔드투엔드 검증(non-counter 320/320 pass, counter 18 실패 = 설계상
     예상). `mutate_xl.py`는 드라이버+프로토콜만 사전 등록(SPECS 사이트는
     arm 소스 종속이라 런 후 채움 — docstring에 후보 변이 클래스 11종).
   - 해석 결정 1건: Engineer Lens 보안 스모크의 `compile(` 금지는 **bare
     호출만** (dotted `re.compile(` 허용) — oracle 테스트 docstring에 명기.
2. **밤1 T 런 스캐폴드 + 프리플라이트 green.**
   `gridcalc-xl/runs/thin/` (자체 git, 부모 .gitignore에 `gridcalc-xl/runs/`
   등록됨) — post-loopspec-approval 상태 재현: `.loopspace/spec.md` =
   사전 등록 SPEC 사본, `.loopspace/state.md` (`run_status: spec`,
   `harness: opencode`, 브랜치 필드 3종), 브랜치
   `loopspace/gridcalc-xl/run` 체크아웃 상태, `.opencode/command/` 스텁
   5종(looplead/loopresume/loopnext/loopspec/loopupdate — looprun은 thick
   전용이라 의도적 제외), `opencode.json`(기본 gpt-5.5 + ornith 구현자
   서브에이전트, :18081, 캡 30000/타임아웃 900s).
   프리플라이트: ornith :18081 LISTEN ✓ / opencode 1.17.15 ✓ / claude
   2.1.199 ✓ / 중립 cwd `import gridcalc` FAIL ✓ / R-id↔그룹 커버리지
   28/28 (아밍 1단계의 기계 체크 조건) ✓.

## 다음 세션 시작점 — ④ 런 3박 (밤1 T → 밤2 K → 밤3 S)

### 밤1 T 런치 (아직 미실행이면 — 사람 인터랙티브 2단계)

1. 아밍: `cd ~/code/ornith-loopspace-experiments/gridcalc-xl/runs/thin &&
   opencode` → `/looplead`. lead가 예산 두 개를 질문 — 권고: **디스패치
   캡 60 / 벽시계 10h** (체크포인트 최소 밀도는 그룹 수 10 기반 기계
   강제, 별도 답 불요). 아밍 커밋 확인 후 세션 종료.
2. 슈퍼바이저 (별도 터미널, Claude Code 밖):
   ```
   LOOPSPACE_TG_BOT_TOKEN=<토큰> LOOPSPACE_TG_CHAT_ID=<챗ID> \
   LOOPSPACE_RESUME_CMD='opencode run "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly."' \
   sh /Users/arden/code/loopspace/scripts/supervise.sh ~/code/ornith-loopspace-experiments/gridcalc-xl/runs/thin
   ```
   게이트 verifier는 기본값(claude -p) 그대로. 함정 ⑤(구독 CLI 장시간
   거동)의 첫 관측이 이 밤.

### 밤1 종료 후 (아침)

- 확인 순서: TG 알림 → `runs/thin/.loopspace/gates.md`(체크포인트 원장,
  final PASS 여부) → `journal.md`의 `## [dispatch]` 카운트(예산 대비).
- 아카이브(관례): 트리 스냅샷 + `git bundle` → `gridcalc-xl/` 하위 흡수.
- 채점(중립 cwd 확인 후):
  `PYTHONPATH=gridcalc-xl/runs/thin GRIDCALC_XL_DIFF_SEEDS=1000 python3 -m
  pytest gridcalc-xl/grading/gridcalc_xl_oracle.py -q` +
  `python3 gridcalc-xl/grading/grade_trajectory.py gridcalc-xl/runs/thin`.

### 밤2 K (thick) 준비 — 스캐폴드는 thin과 유사, 차이만:

- `runs/thick/` 신규. 0.16 하이브리드 구성 재사용: **looprun 스텁 포함**,
  파이프라인 = loopplan(인간 승인) → looprun → supervise. state.md에
  `implementer_fallback: openai/gpt-5.5` 추가(heavy 태스크 에스컬레이션),
  opencode.json은 hybrid 것 재사용(implementer-frontier 서브에이전트는
  런 중 halt 결정 시에만 추가하던 관례 유지 — 초기엔 빼기).
- 밤3 S (solo): `runs/solo/` — spec만 시드(plan 미제공, 대칭성), W 방식
  solo_loop.sh 계열 세션 루프, 스냅샷 커밋, `<DONE>`/상한 종료.
  Manipulation check: **S가 실제 4+ 세션을 소비했는가** (미달 = 해석 ⓒ).

### 그 후 ⑤

trajectory 채점(전 커밋 × R-group CSV) + 교차 변이(`mutate_xl.py` SPECS
채움: 각 arm 출하 버그 → 타 arm 스위트) + 아카이브 + EXPERIMENT.md에
RESULTS 절 + EXPERIMENTS-LOG UPDATE. 판정 기준은 EXPERIMENT.md에 사전
고정(해석 ⓐ/ⓑ/ⓒ 분기 포함) — 그대로 적용.

## 운영 함정 (carry-over, 불변)

① 러너는 Claude Code 백그라운드 태스크 금지 — nohup/별도 터미널 완전 분리
② 감시 스크립트 pkill은 브래킷 트릭(`openc[o]de`)
③ 채점 전 `pip install -e` 오염 제거 확인 (중립 cwd import FAIL — 이
   세션에서 확인됨, 런 후 재확인)
④ 로컬 백엔드 캡 30000/타임아웃 900s — runs/thin/opencode.json 반영됨;
   thick/solo 스캐폴드에도 동일 반영할 것
⑤ 구독 claude CLI 장시간 무인 거동 — 밤1이 첫 관측. 게이트 exit 3은
   FAIL로 안 세니 예산 안전; 연속 exit 3 → lead 저널 + supervise 재시작

## 원자료 위치

- W′ 설계 전문·판정 기준: `gridcalc-xl/grading/EXPERIMENT.md`
- 문제지: `gridcalc-xl/SPEC.md` (= runs/thin/.loopspace/spec.md)
- oracle v3: `gridcalc-xl/grading/` (`d7cdb52`)
- loopspace 0.17: `~/code/loopspace` (v0.17.0, `752d0b6`)
- 이전 핸드오프: `SESSION-HANDOFF-2026-07-15c.md` (②③ 종결로 대체됨)
