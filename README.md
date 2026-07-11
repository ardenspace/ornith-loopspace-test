# ornith × loopspace 검증 실험 모음

로컬 모델 **ornith-1.0-35b-Q5_K_M**(opencode provider `ornith/ornith-1.0-35b-Q5_K_M`)이
[loopspace](https://github.com/ardenspace/loopspace) 자율 하네스의 *실행 백엔드*로
쓸만한지 검증하는 A/B 실험 시리즈. 각 실험은 같은 스펙을 두 방식으로 빌드하고,
**독립 저작한 held-out oracle**로 채점해 델타를 잰다.

- **Arm A (solo):** ornith가 스펙(또는 스펙+플랜)만 받고 혼자 빌드.
- **Arm B (loopspace):** frontier(Claude Code)가 저작한 plan을 ornith가 looprun으로
  실행 — 태스크별 fresh implementer + verifier, heavy 태스크엔 3렌즈 패널.
- **채점:** 양쪽 다 못 보는 held-out oracle(`*/grading/`). 스펙/불변식이 *강제*하는
  것만 채점해 공정성 유지. brute-force 레퍼런스 내장.

전체 서사·운영 디테일은 [`EXPERIMENTS-LOG.md`](./EXPERIMENTS-LOG.md).

## 결과 요약

| 실험 | 축 | Arm A (solo) | Arm B (loopspace) | correctness 델타 |
|---|---|---|---|---|
| **subcut** | 정밀 스펙 (SRT 타임코드 순수함수) | 53/53 | 53/53 | **0** |
| **intervalset** | 모호 스펙 (불변식만, 엣지 미열거) | 56/56 | 56/56 | **0** |
| **kvtx** | heavy 태스크 (nested-tx KV DB) | 64/64 | 64/64 | **0** |

*(subcut은 최초 Path A 검증 + 격리 A/B를 겸함. 상세 EXPERIMENTS-LOG.md)*

## 핵심 발견

1. **4연속 correctness 델타 0.** 정밀·모호·heavy 어느 축에서도 ornith가 solo로 안 슬립.
   잘 명세된 과제(불변식이 정답을 고정)라면 유능한 모델엔 loopspace 검증 루프가 redundant.
2. **heavy 패널 첫 실제 개입 (kvtx).** task 1.2(`risk:heavy`)에서 **test-integrity 렌즈**가
   implementer의 non-TDD(테스트 후작성 → failed-first 증거 자기모순)를 잡아 재시도 강제.
   4개 실험 통틀어 첫 검증 개입. 단 correctness 렌즈는 attempt 1도 PASS = **프로세스 수정이지
   버그 수정 아님.** → loopspace 값어치 = correctness 향상이 아니라 **프로세스/무결성 보험**
   (TDD 실제로 했나·test-gaming 방지).
3. **코드 응집성 갭 (kvtx).** loopspace의 *fresh-agent-per-task* 격리가 오히려 코드를
   지저분하게 만듦: task 1.1이 `Store`를, task 1.2의 fresh agent가 별도 `Database`를 지어
   base-store 로직 중복 + 유지되지만 안 읽히는 dead index. solo는 단일 컨텍스트라
   응집적(60 vs 135 LOC, dead code 0 vs 2종). 원인 = intra-phase 태스크 간 *구조 carry가
   부재*(handoff는 phase/context 경계에서만 발화). 상세는 kvtx/grading/EXPERIMENT.md + LOG.

## 디렉토리

```
<experiment>/
  armA-solo/       ornith solo 빌드 (SPEC[+PLAN] + 코드 + 자체 테스트)
  armB-loopspace/  looprun 산출물 (.loopspace/ spec·plan·journal + 코드 + 테스트)
  grading/         held-out oracle (+ EXPERIMENT.md 설계·결과)
```

`.loopspace/journal.md`에 태스크별 PASS/FAIL·attempt·패널 verdict가 남아 있음
(atomic git 커밋 히스토리의 의미 보존본).

## 재채점

```bash
# arm 하나를 held-out oracle로 채점
PYTHONPATH=kvtx/armB-loopspace python3 -m pytest kvtx/grading/kvtx_oracle.py -q
PYTHONPATH=kvtx/armA-solo     python3 -m pytest kvtx/grading/kvtx_oracle.py -q
```

## 운영 메모

- ornith 로드: `llm ornith` (gemma와 배타 — 맥미니 단일 GPU offload). 응답 포트 18081.
- **GOTCHA 1:** `opencode run` 백그라운드 잡이 끝나도 프로세스가 남아 다음 run이 GPU 슬롯
  대기로 무한 행 → 새 run 전 `pkill -9 -f opencode`.
- **GOTCHA 2:** 헤드리스 진입 `opencode run "Read <abs>/loopresume/SKILL.md ..."`가 ornith에서
  상대경로 `.loopspace/`를 SKILL 디렉토리 기준으로 resolve해 no-op 종료 → 프롬프트에 프로젝트
  cwd를 명시하고 "모든 `.loopspace/...`는 거기서 resolve"라고 못박아야 함.
