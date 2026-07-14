# 세션 핸드오프 — 2026-07-15: 열린 논점 5건 전부 종결, 남은 것 = W′

목적: 이 파일 하나로 다음 세션이 이어갈 수 있게. 2026-07-14 핸드오프를
대체함(그쪽 열린 논점 5건은 이 세션에서 전부 종결). 확정 사실(교차-마음
처방 실증, 같은-마음 3형태, 인프라 정정 등)은 재도출하지 말고 이전
핸드오프의 "확정 사실" 절 + `gridcalc/grading/EXPERIMENT.md` HYBRID
RESULTS를 볼 것.

## 이 세션에서 일어난 일 (요약)

1. **논점 ④·⑤ 종결** (UPDATE 11): harnesses 모델 능력 가이드를 loopspace
   문서에 반영(구현자 유효/오케스트레이터 미검증 완화/verifier 다른 혈통
   필수, OpenCode 매트릭스 verified). oracle R11은 이미 12셀 밀집 —
   변경 불필요 확인.
2. **논점 ①·② 종결 = loopspace 0.16.0** (UPDATE 12): 하이브리드 halt
   8건 중 기계적 6건을 근원 제거 — ⓐ pre-existing 경로(경계-초과 교착의
   표준 failed-first 루트 + verifier stash 짝 분기) ⓑ stall relief 게이트
   3단(좁은 재개→burst→에스컬레이션 사다리 `implementer_fallback:`, 각
   태스크당 1회, 저널 가드) ⓒ panel debt ⓓ loopplan 밀도 규칙
   ⓔ supervise halt 알림에 report의 trigger+Blocker+Options 탑재(폰으로
   결정 가능). "LLM 결정 대행자 훅"은 기각(거버넌스 러버스탬프 위험).
   supervise 테스트 22/22, portability 34/34.
3. **loopspace v0.16.0 태그·푸시 완료** (`7785d5f`, origin 반영).

## 남은 것 — W′ (시리즈 유일 미검증 핵심 주장)

"솔로 컨텍스트가 실제로 넘치는 규모에서는 구조(loopspace)가 이긴다"의
검증. 이번 시리즈 정직 결산: 원샷 가능 규모에선 solo 우위 확정, 초과
규모는 n=0.

- **규모**: gridcalc의 3~5x. solo arm이 단일 컨텍스트로 정말 못 담는지가
  설계의 성패 — 과제가 작으면 W의 재판이 될 뿐.
- **구성 기본 후보**: frontier 오케스트레이터·verifier × ornith 구현자
  (하이브리드 구성 재사용). verifier는 반드시 구현자와 다른 혈통.
- **0.16 신기능 활용**: `implementer_fallback:` 선언(heavy 태스크 ornith
  좌초 대비), `LOOPSPACE_TG_BOT_TOKEN`/`CHAT_ID`로 halt를 폰에서 결정.
- **비용**: 과제·oracle 설계가 실험 한 사이클급 — spec부터. oracle은
  이번처럼 held-out(제3의 마음) + 밀집 소구역 + 변이(mutate.py 패턴).
- **사전 등록**을 잊지 말 것: 성공/실패 기준과 해석 3분기(EXPERIMENT.md
  의 W 패턴 재사용).

## 운영 함정 (재발 방지, carry-over)

① 러너는 Claude Code 백그라운드 태스크 금지 — nohup 완전 분리 필수
② 감시 스크립트의 pkill 대상 문자열은 브래킷 트릭(`openc[o]de`)
③ `pip install -e` 오염 채점 전 제거 확인
④ 로컬 백엔드: 캡 30000/타임아웃 900s (opencode 글로벌은 300s 유지 중 —
   새 프로젝트는 프로젝트 opencode.json에서 상향).

## 원자료 위치

- 이 세션 상세: EXPERIMENTS-LOG.md UPDATE (11)·(12), loopspace
  CHANGELOG 0.16.0 항목 (halt 8건 분류 포함)
- 하이브리드 상세: `gridcalc/grading/EXPERIMENT.md` HYBRID RESULTS +
  중간 사건 1~8; 아카이브 `gridcalc/hybrid-loopspace-0.15.2/`
- W 사전 등록 패턴: EXPERIMENT.md "Pre-registered verdict criteria" +
  "Pre-registration record"
- loopspace: 0.16.0 = `7785d5f` (태그 v0.16.0, origin 푸시됨)
- 변이 하네스: `grading/mutate.py`, `mutate2.py`
