# 세션 핸드오프 — 2026-07-15c: 0.17 lead mode 출하 완료, 다음 = gridcalc-XL SPEC (문제지)

목적: 이 파일 하나로 다음 세션이 이어갈 수 있게. `SESSION-HANDOFF-2026-07-15b.md`를
대체함 — 그쪽 Order of work의 ①(0.17 구현+테스트)이 이 세션에서 종결됨.
W′ 설계 전문은 여전히 `gridcalc-xl/grading/EXPERIMENT.md` (변경 없음).

## 이 세션에서 일어난 일 (요약)

1. **loopspace 0.17.0 "lead mode" 구현·리뷰·머지·릴리즈 완료.**
   loopspace 저장소 main 머지커밋 `752d0b6`, 태그 `v0.17.0`, GitHub Release
   자동 발행 확인. 구현 플랜(코드 전문 포함)은 loopspace 저장소
   `docs/superpowers/plans/2026-07-15-lead-mode.md`.
   - 구성: `scripts/gate.sh`(체크포인트/완주 게이트 — `claude -p` 교차혈통
     verifier 래핑, `.loopspace/gates.md` 원장의 유일 작성자,
     `run_status: complete`의 유일 경로, candidate 커밋 보호, 게이트당
     3연속 FAIL → halt, 워치독) + `skills/looplead/`(lead 스킬 + 게이트
     verifier 프롬프트) + supervise 확장(벽시계 예산 `LOOPSPACE_WALL_BUDGET`
     /`budget_wall_hours`, final-PASS 없는 complete 적발, gates.md 진행신호)
     + loopresume/loopspec 라우팅 + state-format 계약(`## Acceptance Groups`,
     `mode: lead`, budget 필드, gates.md 포맷). **thick 경로(looprun) 무변경.**
   - 테스트: gate 57 / supervise 30 / portability 34 전부 green.
     **라이브 스모크: 실제 `claude -p` 게이트가 장난감 프로젝트에서 75초
     PASS** — 스펙에서 프로브 5개 자가 도출·실행, 심은 변이 적발, 커밋 체인
     정상. 리뷰 루프가 잡은 Critical 1건(워치독 킬 시 verifier 변이가
     재시도 candidate 커밋에 lead 작업으로 섞임 — 재현→수정→재현 재실행으로
     종결) 포함 결함 8건 수정됨.

2. **위치 관례 변경 (사용자 지시, 2026-07-15).** 앞으로 W′의 모든 산출물은
   `~/code/ornith-loopspace-experiments` **안에** 둔다. `~/code`에 새 폴더를
   만들지 말 것 (15b의 "`~/code/gridcalc-xl-{solo,thin,thick}`" 계획은 폐기).
   커밋은 이 저장소의 origin
   (github.com/ardenspace/ornith-loopspace-test)으로 푸시. 런 저장소는 자체
   git이 필요하므로 `gridcalc-xl/runs/{solo,thin,thick}/` 하위에 만들고
   **부모 .gitignore에 `gridcalc-xl/runs/` 등록**(live 트리는 부모가 추적하지
   않음), 각 런 종료 시 기존 관례대로 스냅샷+`git bundle`로 흡수.

## 다음 세션 시작점 — ② gridcalc-XL SPEC.md (문제지)

- **산출물**: `gridcalc-xl/SPEC.md` (세 arm 공용 입력). 커밋 = 사전 등록의
  일부. oracle(③)보다 먼저.
- **절차**: loopspec 패널 방식 — 인터뷰는 짧게(과제 정의가 EXPERIMENT.md에
  이미 있음), 6-리뷰어 패널 검증은 그대로. 사람 승인 필요 (Arden 인터랙티브).
- **내용**: phase 1–4 = 기존 gridcalc spec 프리픽스 재사용 — 원문은
  `gridcalc/hybrid-loopspace-0.15.2/.loopspace/spec.md` (최신 런 기준;
  armA-solo/SPEC.md도 동일 계열). 신규 phase 5–10은 EXPERIMENT.md "Task:
  gridcalc-XL" 절 (문자열함수 / 절대참조·named range / undo-redo /
  ★multi-sheet 함정 / 영속화 / recalc v2).
- **필수**: `## Acceptance Groups` 섹션 — R-id 전부를 정확히 하나의 그룹에,
  W′에선 phase당 1그룹 상당. 이게 thin(T) arm의 체크포인트 단위이자 최소
  밀도 기준. 포맷은 loopspace `docs/state-format.md`(0.17) 참조.

이후: ③ oracle v3 (`gridcalc/grading/gridcalc_oracle.py` 134케이스 + ref +
mutate.py 이식·확장, 밀집 소구역 differential — 12셀급 풀 × 시트 2-3장,
selftest green 후 커밋 = 사전 등록) → ④ 런 3박 (밤1 T → 밤2 K → 밤3 S) →
⑤ trajectory 채점 + 교차 변이 + 아카이브 + EXPERIMENT.md RESULTS.

## T 런(밤1) 운영 메모 — 0.17 첫 실전

- 파이프라인: loopspec(그룹 포함 spec 승인) → `/looplead` 아밍(예산 두 개를
  사람이 답: 디스패치 캡·벽시계 캡) → loopsupervise. lead = gpt-5.5
  (opencode 스텁 커맨드로 SKILL.md 읽는 방식, `LOOPSPACE_RESUME_CMD` =
  opencode 헤드리스 loopresume — harnesses/opencode.md 참조). 게이트
  verifier = 사용자 구독 `claude` CLI (기본값 그대로).
- env 주의: `LOOPSPACE_GATE_TIMEOUT`(기본 2400s)은
  `LOOPSPACE_STALL_TIMEOUT`(기본 3600s)보다 반드시 작게 유지. TG 알림 =
  `LOOPSPACE_TG_BOT_TOKEN`/`CHAT_ID` (halt를 폰에서 결정).
- **함정 ⑤ 미해소**: 구독 CLI의 장시간 무인 rate-limit/세션 만료 거동은
  75초 스모크로만 확인됨 — 밤1이 첫 관측. 게이트 exit 3(오류)은 FAIL로
  안 세니 예산은 안 타지만, 연속 exit 3이 이어지면 lead가 저널에 남기고
  턴을 끝내게 되어 있음(supervise가 재시작/알림).

## 운영 함정 (carry-over, 불변)

① 러너는 Claude Code 백그라운드 태스크 금지 — nohup 완전 분리
② 감시 스크립트 pkill은 브래킷 트릭(`openc[o]de`)
③ 채점 전 `pip install -e` 오염 제거 확인 (중립 cwd import FAIL)
④ 로컬 백엔드 캡 30000/타임아웃 900s — 프로젝트 opencode.json에서 상향 필수
⑤ (위 T 런 메모 참조) claude -p 장시간 거동 관측 필요

## 원자료 위치

- W′ 설계 전문: `gridcalc-xl/grading/EXPERIMENT.md`
- 0.17 구현 플랜·코드: loopspace 저장소 (`~/code/loopspace`, v0.17.0)
- 기존 gridcalc spec/oracle: `gridcalc/hybrid-loopspace-0.15.2/.loopspace/spec.md`,
  `gridcalc/grading/`
- 이 세션 전 핸드오프: `SESSION-HANDOFF-2026-07-15b.md` (①만 종결, 나머지 유효)
