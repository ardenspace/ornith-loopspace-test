# 세션 핸드오프 — 2026-07-15b: W′ 설계 종결(3-arm 피벗), 남은 것 = 실행 (0.17 구현부터)

목적: 이 파일 하나로 다음 세션이 이어갈 수 있게. 같은 날 오전 핸드오프
(`SESSION-HANDOFF-2026-07-15.md`)를 대체함 — 그쪽의 "남은 것 = W′ spec"이
이 세션에서 종결됨. 확정 사실은 재도출하지 말 것: 시리즈 결산은
EXPERIMENTS-LOG.md 헤더+UPDATE (10)~(13), W′ 설계 전문은
`gridcalc-xl/grading/EXPERIMENT.md`.

## 이 세션에서 일어난 일 (요약)

1. **W′ 설계 종결·등록** (UPDATE 13, `gridcalc-xl/grading/EXPERIMENT.md`
   커밋 `27af232`): 원안(2-arm solo vs 0.16)이 아니라 **3-arm
   dose-response** — 사용자 문제의식("하네스가 얇아져도 되지 않나")을
   병합해 S(solo ornith) / T(**thin = loopspace 0.17 lead mode 신설**) /
   K(thick 0.16 하이브리드)를 gridcalc-XL ~4x에서 비교. 철학: *Give
   autonomy. Enforce invariants.* 갈림길 6개(방향 B → invariant 옵션 2 →
   라인업 A → thin verifier = Claude CLI → 과제 gridcalc-XL → 규모 ~4x)
   전부 TG 대화로 승인됨. risk-triggered verifier 안은 기각(같은-마음
   사각지대는 위험해 보이지 않음 — risk 분류 자체가 뚫림).
2. **아카이브 체계 확정 + ~/code 정리**: 런 저장소 5개의 git 히스토리를
   bundle로 흡수(`33573eb`, 전부 verify + HEAD 확인), 원본 6폴더
   삭제(~314M). 세션 포렌식 DB는 전역
   `~/.local/share/opencode/opencode.db`(205M)임을 확인 — 폴더별
   .opencode 61M은 node_modules 잔해였음. **이후 런도 종료 시
   스냅샷+bundle 패턴** (사용자 강승인).
3. **소통 채널**: 이 세션은 Telegram 브릿지로 진행 — 답장은 반드시 TG
   reply 도구로 (일반 출력은 터미널에만 찍힘).

## 남은 것 — W′ 실행 (Order of work, 설계 문서와 동일)

1. **loopspace 0.17 "lead mode" 구현+테스트** ← 다음 세션 시작점.
   loopspace 저장소(`~/code/loopspace`)에서. 설계 원본 =
   `gridcalc-xl/grading/EXPERIMENT.md`의 "Thin mode" 절. 핵심: looprun
   지휘 로직 제거한 lead 프롬프트 + `claude -p` 게이트 스크립트 신작 +
   supervise 확장. 게이트 스모크(claude -p 헤드리스 호출) 먼저.
2. gridcalc-XL SPEC.md — loopspec 패널. phase 1-4는 기존 gridcalc spec
   프리픽스 재사용. **acceptance R-id 그룹 경계를 명시적으로** (thin
   체크포인트 단위가 됨).
3. oracle v3 확장(+selftest, 변이 이식) → `gridcalc-xl/grading/` 커밋 =
   사전 등록.
4. 런 3박: 밤1 T(신작 하네스 = 리스크 최대, 낮에 디버깅) → 밤2 K →
   밤3 S. 프리플라이트 매밤: pkill 좀비, ornith :18081, 프로젝트
   opencode.json (캡 30000/900s).
5. trajectory 채점 + 교차 변이 + 아카이브(스냅샷+bundle) + EXPERIMENT.md
   RESULTS + EXPERIMENTS-LOG UPDATE.

## 운영 함정 (carry-over, 불변)

① 러너는 Claude Code 백그라운드 태스크 금지 — nohup 완전 분리
② 감시 스크립트 pkill은 브래킷 트릭(`openc[o]de`)
③ 채점 전 `pip install -e` 오염 제거 확인 (중립 cwd import FAIL)
④ 로컬 백엔드 캡 30000/타임아웃 900s — opencode 글로벌은 300s 유지
   중이므로 **프로젝트 opencode.json에서 상향 필수**
⑤ (신규) thin 게이트의 `claude -p`는 사용자 구독 CLI — 장시간 무인 런
   중 rate-limit/세션 만료 거동을 0.17 테스트에서 확인할 것

## 원자료 위치

- W′ 설계 전문: `gridcalc-xl/grading/EXPERIMENT.md` (설계 결정 기록 +
  Limitations 포함)
- 이 세션 상세: EXPERIMENTS-LOG.md UPDATE (13)
- 런 저장소 예정지: `~/code/gridcalc-xl-{solo,thin,thick}`
- 아카이브 bundle: `gridcalc/*/…git.bundle`, `kvtx/armB-loopspace-rerun/`
- loopspace: 0.16.0 = `7785d5f` (v0.16.0 태그, origin 반영), 0.17 미착수
- W 사전 등록 패턴: `gridcalc/grading/EXPERIMENT.md` "Pre-registered
  verdict criteria" + "Pre-registration record"
