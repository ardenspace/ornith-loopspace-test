# HANDOFF — ornith × loopspace 검증 실험

written: 2026-07-12 · 정밀·모호·**heavy 세 축 모두 완료** — correctness 델타 전부 0. loopspace 0.14 carry 재런으로 **응집성 갭 해소 확인**. 다음 = **실험 W(gridcalc, 멀티세션 드리프트) 설계 확정** — `gridcalc/grading/EXPERIMENT.md` (미니 스프레드시트 4 phase, 하룻밤 무인 × 2, solo 자율노트 baseline, 궤적 채점).

## ⏩ UPDATE 2026-07-12 (5) — arm B 완주 + 채점 완료 (oracle 124/131, 드리프트 0), arm A 야간 런 시작
- **arm B 완주**: run_status complete, 11/11 task done, 자체 테스트 161 green. tier C 전환 후에도 3.1/3.2/4.1은 저널상 `subagent (tier A)`로 성공 — heavy(2.1, 4.2)만 role-swap. 4.2(설계된 트랩)는 attempt 1 PASS (dependency-aware invalidation, `_deps`+closure).
- **oracle 채점: 124/131 (94.7%)**. 실패 7건 전부 R11 differential, 단일 실패 모드 — 오류값이 담긴 셀을 참조하는 경로에서 `#REF!`/`#CYCLE!`가 `#TYPE!`로 강등(문자열 취급). 궤적상 R11은 한 번도 full green이었던 적 없음 → **회귀가 아니라 phase 2~3부터의 잠복 버그** (3.2가 #CYCLE! 직접 전파를 고쳤지만 일부 경로만).
- **궤적 채점: 드리프트 이벤트 0** (`gridcalc/armB-loopspace/trajectory.csv`, 17 스냅샷). pass 단조 증가 18→22→67→88→115→122→124. 한 번 green이 된 R-group이 다시 깨진 사례 없음 — phase 4의 평가 경로 재작성에도 조기 요구사항 무손상.
- **응집성 발견 (arm B, 신규)**: ① **4.2~4.4 커밋 누락** — complete 선언했지만 마지막 3개 task 작업물이 working tree에만 존재(phase-4 HEAD는 4.1). 채점 전 grader 라벨 커밋으로 보존(`gridcalc-trial@93457e0`, run의 커밋 아님을 명시). ② run 브랜치 머지 전무 — `loopspace/gridcalc/run`은 plan 승인 시점에 정지. ③ 4.2 tdd-evidence "tests adjusted to match actual behavior", 4.3/4.4 failed-first 증거 부재 — tier C 구간 test-integrity 약화 신호.
- **측정 오염 발견+제거**: arm B 런 중 gridcalc가 site-packages에 **editable install**(`pip install -e`, direct_url→gridcalc-trial)로 박혀 있었음 → 코드 없는 스냅샷에서 라이브 repo로 fallback import되어 1차 궤적 채점 오염(idx 0~2가 최종값 124로 나옴). uninstall 후 재채점한 것이 위 결과. **후속 실험 프리플라이트에 `python3 -c "import <pkg>"` 실패 확인 추가할 것.**
- **arm A(solo) 야간 런 시작**: 2026-07-12 20:00:58 KST, `nohup sh solo_loop.sh`(pid 5416), 세션 1 정상 스트리밍 확인. 프리플라이트: opencode 잔존 0, ornith :18081 서빙 확인. 최대 12세션/8h → 익일 ~04:00 전 종료. 로그 `gridcalc-runner/logs/solo_loop.log`+`session_N.log`, 스냅샷은 세션마다 자동 커밋.
- **다음**: arm A 종료 확인 → oracle + 궤적 채점(`grade_trajectory.py ~/code/gridcalc-solo`) → 양 arm 아카이브(`gridcalc/arm{A,B}-*`) → EXPERIMENT.md/이 파일에 최종 판정 (사전 등록 기준: primary = 최종 oracle 델타 B−A, secondary = 드리프트 수·세션 수·완주 여부·notes 행태).

## ⏩ UPDATE 2026-07-12 (4) — 실험 W (gridcalc) 진행 중: arm B가 tier A 좌초 → tier C로 순항
- **셋업 완료 (전부 커밋됨)**: spec/plan 승인(`gridcalc-trial` f933d38/1099c8a, 패널 수렴 기록은 grading/EXPERIMENT.md), held-out oracle 사전 등록(`cfcc60c`, 131 assertion, self-test 119 green), arm A seed(`~/code/gridcalc-solo` 63938a7), 러너 `~/code/gridcalc-runner/`(armB_supervise.sh / solo_loop.sh / 로그).
- **arm B 1차 (tier A): 28분 만에 halt.** phase 1은 통과했으나 task 2.1(heavy 파서)에서 implementer 서브에이전트가 3연속 무출력 → 스톨 → halt. **원인 확정(세션 DB)**: ornith가 큰 자율 디스패치에서 reasoning 채널에만 쓰고 본문 없이 턴 종료 → 빈 task_result. 컨텍스트(n_ctx 131k)/프롬프트 크기/좀비 무관. 요구 생각량과 상관: light 통과, 1.2가 1회 반반, 파서 3/3 사망.
- **tier C(role-swap) 전환으로 해소** (halt-resume, `bc22cbb`): 전환 후 2.1이 attempt 1에 통과 — R12 조기화 덕에 iterative shunting-yard 선택. 이후 2.2→4.1까지 전부 attempt 1 PASS, phase 2·3 verified. 핸드오프 시점 기준 4.2(설계된 트랩) 진행 중, 남은 태스크 4.2/4.3/4.4. **판정 유의: arm B는 tier A가 아니라 C로 완주하게 됨 — "tier 시스템이 약한 백엔드를 흡수했다"는 관측이자, 독립 검증 격리는 약화된 상태(정직하게 보고할 것). correctness 채점은 oracle이 하므로 오염 없음.**
- **부수 발견 (loopspace/ornith 후속감)**: ① 0d2cd3a 문구 보강에도 계약 문장 디스패치 누락 여전(0건) — 문구로는 못 고침, 더 강한 처방 필요. ② PRIOR WORK 블록에 phase 경계 넘은 태스크 포함(스펙상 intra-phase 전용). ③ stubborn 분류 후 diversity burst 생략 + report trigger 불일치(journal stubborn vs report external-blocker). ④ state.md 헤더(current_phase/task) 갱신 누락 — 표/저널/커밋은 정상.
- **운영**: supervisor는 Claude 세션에 묶으면 죽는다(2회 killed) → **nohup 분리 실행**이 정답: `nohup sh ~/code/gridcalc-runner/armB_supervise.sh > ~/code/gridcalc-runner/logs/armB_supervise.log 2>&1 &`. 상태 진실은 `gridcalc-trial/.loopspace/state.md`+journal.
- **다음 순서**: ① arm B 종료 확인(complete/halt) → 저널 분석 ② oracle 채점 `PYTHONPATH=~/code/gridcalc-trial python3 -m pytest gridcalc/grading/gridcalc_oracle.py -q` ③ 밤 2 = arm A `sh ~/code/gridcalc-runner/solo_loop.sh` (사전 `pkill -9 -f opencode` + ornith 확인) ④ 양쪽 궤적 채점 `python3 gridcalc/grading/grade_trajectory.py <repo> --branch <branch>` ⑤ 아카이브 + EXPERIMENT.md/LOG 결과 기록.

## ⏩ UPDATE 2026-07-11 (3) — intra-phase carry 수리 검증 재런 (kvtx-rerun): 응집성 갭 해소 확인
- **배경**: kvtx의 코드 응집성 갭(fresh-agent 격리 → 1.2가 `Store` 존재를 모르고 `Database` 통재구현, dead `Store`+`_vk`, 135 vs 60 LOC)을 loopspace **0.14.0 "intra-phase carry"**로 수리 — implementer `exports:` 자가보고 + 디스패치마다 PRIOR WORK THIS PHASE 블록(저널에서 조립, diet 유지) + 양층 중복 강제(태스크 verifier check + phase verifier blocking check). 머지 `4f91830`, 리뷰 후속 `d21f392`(reuse 체크가 자가보고 라인이 아니라 트리를 보고 판정 — 과대보고 export의 false FAIL 경로 차단).
- **재런 설계**: 동일 spec+plan, 유일 변수 = loopspace 버전. `~/code/kvtx-rerun`에서 실행, 이 repo `kvtx/armB-loopspace-rerun/`에 아카이브.
- **결과: 실패 모드 재발 없음.** 1.2가 `Store`를 composition으로 감쌈(저널 exports에 "Store — … (unchanged)"라고 이전 작업 인지 명시), **dead code 0, 85 LOC**(구 135), **oracle 64/64 유지**, 1.2 attempt 1에 3렌즈 전부 PASS(구런은 test-integrity FAIL로 2 attempts). phase verifier가 신설 blocking check로 "no duplication between tasks" 명시 판정 + 구런에서 아무도 못 잡던 `Database.count()` O(n) vs `Store.count()` O(1) 비대칭을 spec-concern으로 표면화(check 5 프레이밍 수리의 부수 효과).
- **메커니즘 전 구간 증거** (opencode 세션 DB `part` 테이블 직접 확인): orchestrator(ornith)가 저널에서 블록 조립("1.2 needs to know Store exists"라고 자가 추론) → 1.2 디스패치에 `[1.1] files: … — exports: kvtx.database.Store …` verbatim 주입 → verifier 디스패치 4건에 Prior-work reuse 체크(d21f392 문구 포함) 실림.
- **잔여 이슈 (경미, ornith 이행 슬립)**: ① 템플릿 A 인스턴스화 때 PRIOR WORK 블록 아래 **고정 계약 문장**("never build a parallel implementation … verifier FAIL")을 누락 — placeholder 섹션 전체를 빈칸 채우기로 취급한 듯. 이번엔 정보만으로 순응해서 무해했지만 3겹 방어(정보+경고 / 태스크 verifier / phase verifier) 중 1겹이 전달에서 샘 → 템플릿/looprun에 "고정 문구 verbatim 디스패치" 명시 후보. ② 브랜치 규율 미이행(phase-1 브랜치 미생성, run 브랜치에서 전부 진행) — 같은 계열 슬립, 실험 판정 무관.
- **단서**: n=1이고 강제 경로(중복 FAIL)는 미발화 — implementer가 정보만으로 먼저 순응해서 억지력이 이빨보다 먼저 작동. 잔여 85 vs 60 LOC는 낭비가 아니라 plan이 의도한 2층 구조(base store 위 tx layer). correctness 델타는 여전히 0(예상대로 — 이 수리의 목표 아님). 다음 큰 실험 = 멀티세션 드리프트 (불변).

## ⏩ UPDATE 2026-07-11 (2) — heavy task A/B (Experiment Z, kvtx) 완료: correctness 델타 0, 단 heavy 패널 첫 실제 개입
- **과제=kvtx** (nested-transaction in-memory KV DB + `count`-by-value; 킬러=count가 중첩 롤백/오버라이트 관통 일관성 — 인간도 자주 슬립하는 고전 문제). spec+plan **정밀**(행동 열거), task 1.2 `risk:heavy`. 격리=X(양쪽 동일 spec+plan, 유일 변수=looprun heavy 루프).
- **held-out oracle 64개**(named 킬러 케이스 + 40 랜덤 vs overlay 레퍼런스, 자기검증 통과) → **둘 다 64/64, correctness 델타 0.** ornith가 heavy도 solo로 안 슬립.
- **그러나 미검증 heavy 3렌즈 패널이 처음으로 실제 개입:** task 1.2 attempt 1 = **test-integrity FAIL** (implementer가 TDD 안 하고 테스트를 구현 후 작성 → failed-first 증거 자기모순을 렌즈가 탐지) → 재시도 강제 → attempt 2 진짜 TDD로 PASS. **4개 실험 통틀어 첫 검증 개입.** 단 correctness 렌즈는 attempt 1도 PASS했음 = **프로세스 수정이지 버그 수정 아님.** 순 shipped-correctness 델타는 여전히 0.
- **코드 청결도는 solo가 오히려 나음**: Arm A 60 LOC(dead code 0) vs Arm B 135 LOC(패널이 non-blocking으로 지적한 dead `Store` 클래스 = scope creep 포함). loopspace가 재시도 1회 + 장황함을 비용으로 치름.
- **결론(4연속 델타 0):** loopspace 값어치 = 유능한 모델엔 **correctness 향상이 아니라 프로세스/무결성 보험**(TDD 실제로 했는지, test-gaming 방지). 이번엔 코드가 맞아서 그 보험이 물지 않았을 뿐. correctness 델타 뽑으려면 모델이 *실제로 틀린 답을 shipping*해야 하는데 ornith는 잘 명세된 과제(easy/hard 불문)에서 안 그럼. **남은 후보 = 긴 멀티세션(컨텍스트 드리프트·핸드오프 손실이 solo를 무너뜨리고 loopspace의 fresh-agent+handoff가 버티나).**
- 위치: `~/code/kvtx-trial`(B), `~/code/kvtx-solo`(A), `~/code/kvtx-grading/`(oracle+EXPERIMENT.md).


## 한 줄
로컬 모델 **ornith-1.0-35b-Q5_K_M**가 [loopspace] 자율 하네스의 *실행 백엔드*로 쓸만한지 검증하는 실험. 여기까지: **정밀명세·모호명세 둘 다 검증 완료(A/B 델타 전부 0)**, 남은 건 **heavy task(3렌즈 패널)로 loopspace의 진짜 값을 찾는 것**.

## ⏩ UPDATE 2026-07-11 — 모호-스펙 A/B (Experiment Y) 완료: 또 델타 0
- **과제=intervalset** (정수 폐구간 IntervalSet, 불변식 "최소 개수 구간"만 정밀 진술, 인접병합·remove-split 등 엣지 **일부러 미열거**). Arm B=loopplan이 불변식→acceptance로 엣지 도출→ornith looprun / Arm A=solo ornith가 얕은 스펙만 받고 빌드.
- **held-out oracle 56개(내가 독립 저작, brute-force 레퍼런스 내장, 자기검증 통과) → 둘 다 56/56, 델타 0.** solo가 정수 인접 off-by-one까지 불변식에서 자력 도출. 자체 테스트도 solo가 더 많이(49 vs 36).
- **결론: 모호성 축(최고 판별력 예상)마저 델타 0.** 좋은 불변식 + 유능한 모델이면 검증 루프 redundant. **델타는 모델이 *실제로 슬립*해야 나옴 → 남은 건 heavy task뿐.**
- 위치: `~/code/intervalset-trial`(Arm B, loopspace), `~/code/intervalset-solo`(Arm A), `~/code/intervalset-grading/`(EXPERIMENT.md + oracle, arm 밖 격리). 상세는 거기 EXPERIMENT.md.
- **운영 GOTCHA 추가**: raw `opencode run "Read <abs>/loopresume/SKILL.md ..."` 진입이 ornith에서 상대경로 `.loopspace/`를 SKILL 디렉토리 기준으로 resolve해 no-op 종료(exit 0, 작업 0). **프롬프트에 프로젝트 cwd 명시 + "모든 `.loopspace/...`는 거기서 resolve" 못박아야 함.**

---

## 지금까지 (요약)

1. **Path A 검증** — frontier(Claude Code)로 spec→plan 짜고, ornith가 opencode에서 `looprun`. 과제=subcut(SRT 타임코드 순수함수 lib, 4 light task). → 49/49 green(독립 실행 확인), verifier가 실전 결함(import 세팅) 잡아 재시도 강제 = 정직.
2. **verifier 트랩 실험** — 일부러 "pytest 초록불인데 코드/테스트가 criterion 위반"인 함정 심음. ornith verifier가 **FAIL로 정확히 잡음**(버그 코드 라인 + 틀린 테스트 둘 다). → verifier 정직성 = 운 아니라 실력.
3. **격리 실험 (Arm A vs B)** — 같은 frontier spec+plan을, **Arm B=loopspace로 실행 / Arm A=solo ornith(looprun 없이 그냥 빌드)**. 내가 스펙에서 독립 작성한 **held-out oracle 53개**로 양쪽 채점.
   → **결과: 둘 다 53/53. 델타 = 0.** solo ornith가 트랩 계급(독립 clamp·digit-count·transitive merge·CRLF·no-mutation·bool거부)까지 스스로 다 처리. 몇 군데는 loopspace arm보다 오히려 더 깔끔.

## 핵심 결론 (정직하게, 다음 실험의 출발점)

- **잘 명세된 작은 작업엔 loopspace 검증 루프가 redundant.** 좋은 스펙 + 유능한 모델이면 solo로 충분. loopspace 루프 값어치는 *리스크의 함수*고 subcut은 저리스크였음.
- **단, "loopspace 무용"은 아님:** (a) solo를 성공시킨 그 *정밀한 스펙 자체*를 loopspace 기획 파이프라인(loopspec→loopplan+패널)이 만듦 — 우린 *looprun*만 뺐지 기획 규율을 뺀 게 아님. (b) loopspace가 값을 해야 할 조건(모호 스펙 / 긴 세션 드리프트 / heavy task / 모델이 *실제로* 버그 내는 상황)을 하나도 안 건드림.
- **그래서 다음 물음 = "스펙을 얼마나 대충 줘도 loopspace가 건져내나" + "heavy task(3렌즈 패널)에서 solo가 무너지나".**

---

## 다음 세션 실험 설계 (heavy task) — 제안

loopspace가 이긴다고 *주장하는 조건*을 일부러 만들어야 델타가 나옴:

- **난이도↑ + heavy 태스크**: 상태·부분실패 분기·상호작용 있는 과제(예: 미니 인터프리터/파서+평가기, 동시성/락, 트랜잭션 롤백 로직). loopplan에서 `risk: heavy` 태그 → looprun이 **3렌즈 패널(correctness/security/test-integrity)** 밟음. subcut은 전부 light라 패널 자체를 시험 못 했음.
- **(강추) 모호-스펙 A/B arm**: 일부러 *덜 명세된* 스펙을 양쪽에 주고 → solo는 자기 해석으로 짜다 슬립 내나 / loopspace는 검증으로 잡나. 이게 loopspace의 *실제 claim*이라 제일 판별력 높음.
- **채점**: 여기서도 **held-out oracle** 필수(자기 테스트로 채점하면 순환논리). 예시 보존: `experiment/subcut_oracle_example.py`.

## 운영 디테일 (그대로 재사용)

- **ornith model id**: `ornith/ornith-1.0-35b-Q5_K_M`
- **⚠️ 최대 GOTCHA**: `opencode run` 백그라운드 잡이 끝나도 **프로세스가 안 죽고 남음** → 다음 run이 ornith **단일 GPU 슬롯**을 기다리며 **무한 행**(첫 모델 호출에서 멈춤, 배너·파일 0, CPU 낮음). **새 run 전에 반드시 `pkill -9 -f opencode`로 좀비 정리.** 이 증상이면 이게 원인.
- **ornith 로드**: `llm ornith`로 스왑(gemma와 배타 — 맥미니 48GB 단일 GPU offload).
- **헤드리스 실행**: `cd <repo> && opencode run --auto --print-logs --log-level INFO -m ornith/ornith-1.0-35b-Q5_K_M "<prompt>"` (`--print-logs`=진단, `--auto`=권한 자동승인, throwaway repo에서만).
- **loopspace 파이프라인**: `/loopspec` → `/loopplan` (여기 Claude Code=frontier 저작) → opencode 세션에서 실행. 헤드리스 실행 진입 = `opencode run "Read /Users/arden/code/loopspace/skills/loopresume/SKILL.md and follow it exactly."` (loopresume가 run_status 보고 looprun으로 라우팅). 상태는 `.loopspace/`.
- **opencode 셋업**: 각 repo `.opencode/command/*.md`에 loopspace 스킬 stub(`Read ~/code/loopspace/skills/<name>/SKILL.md and follow it exactly.`), `opencode.json`에 `{"model":"ornith/ornith-1.0-35b-Q5_K_M"}` 고정.
- **held-out oracle 채점**: `PYTHONPATH=<repo> python3 -m pytest <oracle-file-밖에-둔-것> -q`.

## 파일/위치

- **Arm B (loopspace)**: `~/code/subcut-trial` — `.loopspace/`(spec/plan/state/journal), 생성 코드 `subcut/`+`tests/`. GitHub `ardenspace/ornith-loopspace-test`. 브랜치 `loopspace/subcut/run`.
- **Arm A (solo)**: `~/code/subcut-solo` — `SPEC.md`+`PLAN.md` seed + ornith가 solo로 생성한 코드. (B와 동일 스펙, loopspace만 없음)
- **oracle 보존본**: `~/code/subcut-trial/experiment/subcut_oracle_example.py` (원본은 세션 scratchpad라 휘발됨 — 이게 durable 사본). Arm A 프롬프트도 `experiment/armA_solo_prompt.txt`.
- **loopspace 체크아웃**: `~/code/loopspace`. `harnesses/opencode.md`의 `verified:` 줄 = **2026-07-10로 갱신 완료(커밋 `ad50e56`)**.

## 열린 것 (미완)

- `~/code/loopspace`의 opencode.md verified 커밋 + subcut-trial 커밋 = **미푸시** (푸시는 사용자 몫).
- **텔레그램 브릿지**: 정당화됐지만 미착수 (`opencode run -s <session>` 감싸는 얇은 봇, chat_id 화이트리스트 필수, Hermes+Codex와 별 프로세스). 상세는 메모리 [[ornith-loopspace-local-backend]].
- **다음 = heavy/모호-스펙 실험** (위 설계).

## 다음 세션 시작하는 법
1. `~/code/subcut-trial/HANDOFF.md`(이 파일) 읽기.
2. `pkill -9 -f opencode`로 좀비 확인/정리, `llm ornith`로 모델 로드 확인.
3. heavy task 주제 정하고 `/loopspec`부터 (또는 모호-스펙 arm이면 스펙을 일부러 얕게).
