# 세션 핸드오프 — 2026-07-28: Experiment L 완주 (계통 vs 급) — **결론이 뒤집혔다. 축은 계통이 아니라 역할이었다**

목적: 이 파일 하나로 다음 세션이 이어갈 수 있게. **`SESSION-HANDOFF-2026-07-16.md`를
대체하지 않는다** — 그쪽은 gridcalc-XL(W′) 갈래이고 ⑤가 아직 열려 있다(아래 "열린 것" 참조).
이 세션은 별개 갈래인 **Experiment L**을 1단계부터 5단계까지 하루에 완주했다.

설계·판정 기준·결과 전문: `gridcalc/grading/EXPERIMENT.md`
(`:8` 사전 등록 / `:162` UPDATE L-1 / `:242` RESULTS)

## 한 줄

전용 적대적 verifier 자리에 앉히면 **같은 모델도 자기 맹점을 잡는다.** 시리즈가 "다른 계통이
필요하다"고 읽었던 증거는 계통과 역할이 함께 움직인 교란이었다.

## 이 세션에서 일어난 일

1. **시드 + 프리플라이트** (`6e8940f`). `/Users/arden/code/gridcalc-sonnet` 생성 —
   armA-solo의 SPEC/PLAN verbatim(md5 `498ff1f6`/`2e5ea9ee`, 바이트 동일), `.gitignore`
   동반(러너가 `git add -A`라 pycache 혼입 방지), 코드·테스트 0.
   프리플라이트 green: 중립 cwd `import gridcalc` FAIL ✓ / opencode 좀비 0 ✓ /
   sonnet-5·opus-5 스모크 OK ✓ / opencode OpenAI OAuth 생존 ✓.
2. **armSN 빌드** (`38e02b8`). `CLAUDE_FLAGS='--dangerously-skip-permissions'`
   `MAX_SESSIONS=3 MAX_HOURS=3`. **1세션 ~13분에 `<DONE>`**, 자체 스위트 107 green.
   (armA는 ornith 35B로 1세션 ~40분이었다 — 캡 12/8h는 두 arm 다 근처도 안 갔다.)
3. **변이 매트릭스 → 게이트 실패 → 눈금 이동** (`3210a52`, UPDATE L-1).
   **M7 KILLED = 실패 모드 1 발동.** 눈금을 M15로 이동, 프로브 **이전에** 새 판정 기준 확정.
4. **verifier 프로브 3셀** (`9deb8f0`, RESULTS). 격리 클론 3개(전부 `38e02b8`)에서 병렬·독립,
   블라인드 프롬프트 무수정, 자율 등급 동일. 실행 후 세 클론 전부 `git status` clean.
5. **아카이브 + Secondary** (`973c527`). `gridcalc/armSN-sonnet/`에 스냅샷 + bundle
   (complete history 검증) + trajectory.csv + 런 로그. 관례대로 별도 레포 만들지 않음.

전부 `origin/main` 푸시됨 (`https://github.com/ardenspace/ornith-loopspace-test`).

## 결과 (요지 — 전문은 EXPERIMENT.md `:242`)

**① Primary(M15): 미답변.** 세 셀 전부 미적발. Opus만이 아니라 **필수 대조군 GPT도** 못 잡아
계통을 분리해 내지 못했다. 예측("Opus는 못 잡을 것")은 형식상 적중했으나 증거로 쓰지 않았다.
자기 비판 등록: M15는 변이 16개 중 **유일 생존이라는 이유로** 뽑혔고, 그건 곧 "아무도 못
잡는" 쪽으로 편향된 선택이다.

**② 실제 결과: M7 계열을 세 셀이 전부 적발. 하한(Sonnet) 셀 포함.**
각 셀의 리터럴 쌍이 단일축 변이 2종을 완전히 덮음을 실측 확인(기존 arm의 `B2:A1`은 셋 다
못 죽인다). 등록 M7 변이까지 죽이는 `B1:A2`는 Sonnet과 GPT가 명시.
→ **테제 정정.** 옛 증거의 "같은-마음" 조건은 *구현자가 자기 스위트를 쓴 상태*, "다른 계통"
조건은 *전용 verifier가 루프에 있던 상태*였다. 세 지점 전부에 같은 verifier를 붙이니 셋 다
적발했다. 갈랐던 변수는 계통이 아니라 **역할**이다.

**③ 급 차이는 깊이로 나타났다.** 세 셀이 "구현이 틀렸다"고 주장한 항목을 저자가 전부 재현 —
**셋 다 사실**. 실제 결함 적발 수 **Sonnet 0 / GPT 1 / Opus 3**
(비-ASCII 숫자 INT 수용 `=١٢`→`12`, `set`이 `ValueError`를 밖으로 던짐, R12 범위 내
`RecursionError`).

**④ 수렴 발견 — armSN의 differential "독립 레퍼런스"가 자기 파서의 줄 단위 복제.**
세 셀이 독립적으로 지적했고 확인됨(같은 `isdigit()`, 같은 `len(letters) != 1`). 문법 계층
결함은 1000시드가 구조적으로 못 본다. **한 arm의 스위트 *내부*에서 같은-마음 실패가 재현된
첫 사례** — 시리즈의 4번째 형태로 등록.

**⑤ Secondary: oracle v2 134/134 만점** (solo 133 > armB 126 > 하이브리드 119 > 재런 107),
drift 0. **단 ③의 실제 결함 3건이 전부 살아 있는 채로 만점이다** — oracle에 유니코드·위첨자·
재귀 케이스가 0건. oracle 저자도 Claude, Opus도 Claude인데 **oracle은 놓쳤고 Opus는 잡았다.**
②를 한 번 더 지지한다.

**⑥ 용어 처분 (블로그 2편).** `계통`도 `혈통`도 **쓰지 말 것.** 어색해서가 아니라 데이터가
그 축을 지지하지 않아서다 — 혈연 은유는 "갈래마다 갈린다"를 전제하는데 세 갈래가 같은 행동을
했다. 데이터가 가리키는 축은 **"자기 작업을 이어서 보는가, 처음 보는가"** = 자리/역할의 언어.
편 제목 "같은 마음(same-mind)"은 살아남되 뜻이 좁아진다: "같은 **모델**"이 아니라
**"같은 자리에 앉은 마음"**. 원고: `~/code/ardenspace-portfolio/src/content/ko/blog/same-mind-blind-spots.mdx`

## 열린 것

### Experiment L (이 갈래)

- **Opus 출력의 OTHER FINDINGS 뒷부분 미검증.** 저자가 확인한 건 "구현이 틀렸다" 3건 +
  중복 테스트 1쌍 + 빈 단언 테스트 1건까지. 나머지는 미확인.
- **프로브는 셀당 1회씩.** 재현 실행 안 했다. 적발/미적발 이진 판정은 셋 다 여유 있게
  갈렸으나 항목 구성의 안정성은 미측정.
- **M15는 여전히 미측정.** 아무도 못 잡았으므로 "잡을 수 있는 빈자리인지"가 미지.
  잡히는지 보려면 힌트 있는 프로브를 별도로 돌려야 하는데, 그건 블라인드 조건을 깨므로
  **별도 셀로 설계해 사전 등록할 것**(이번 결과에 섞지 말 것).
- 세 프로브 출력의 항목 교집합 미집계(저자는 두 축만 봤다).
- EXPERIMENTS-LOG.md UPDATE 미작성 — 이 갈래는 EXPERIMENT.md에만 기록돼 있다.

### gridcalc-XL / W′ (07-16 갈래 — 이 세션에서 건드리지 않음)

- `gridcalc-xl/grading/mutate_xl.py`의 `SPECS`가 **여전히 비어 있다**(교차 변이 미실행).
- `gridcalc-xl/grading/EXPERIMENT.md`에 **RESULTS 절 없음.** W′ 결산 수치
  (S 308 / T 932 / K 1324, 1330케이스)는 현재 `DECISION-per-phase-implementer.md`의
  **미커밋 41줄**에만 있다.
- → 07-16 핸드오프의 ⑤가 그대로 열려 있다.

### 저장소 위생

- `DECISION-per-phase-implementer.md` 미커밋 41줄(07-26 W′ 결산 반영). 이 세션 시작
  전부터 있던 작업이라 손대지 않았다. **L과 무관하므로 별도로 커밋할 것.**

## 운영 함정

### 신규 (이 세션에서 실제로 당함) — ⑥ stale `__pycache__`

**변이 전후 소스의 바이트 길이가 같으면** CPython의 `(mtime 초, size)` pyc 무효화를 통과해,
소스를 복원해도 **변이 바이트코드가 계속 실행된다.** `git status`는 clean인데 실행되는 건 딴
코드다. 첫 스윕에서 M09(`for r … for c` ↔ `for c … for r`, 길이 동일) 이후 5건이 오염된
트리에서 채점됐고, 재실행에서 M15·M18이 KILLED→SURVIVED로 뒤집혔다 — **오염이 거짓 KILL
방향**이라 그냥 넘어갔으면 눈금을 못 찾았을 것이다. editable-install 사건과 같은 계열.

처방(두 하네스에 적용 완료): `PYTHONDONTWRITEBYTECODE=1` + 매 pytest 전 `__pycache__` 제거
+ **복원 후 베이스라인 재확인, green 아니면 즉시 abort.**
**크기 보존 변이를 쓰는 모든 후속 변이 작업에 이 가드를 요구한다.**
(`mutate_lineage.py`·`sweep_lineage.py`에는 들어 있음. **`mutate_xl.py`에는 아직 없다** —
XL 교차 변이 돌리기 전에 이식할 것.)

### carry-over (불변)

① 러너는 Claude Code 백그라운드 태스크 금지 — nohup/별도 터미널 완전 분리
  (이 세션도 `nohup` + PPID=1 확인 후 진행)
② 감시 스크립트 pkill은 브래킷 트릭(`openc[o]de`)
③ 채점 전 `pip install -e` 오염 제거 확인 (중립 cwd import FAIL — 이 세션 확인됨)
④ 로컬 백엔드 캡 30000 / 타임아웃 900s
⑤ 구독 claude CLI 장시간 무인 거동 — L은 13분이라 관측 불가. XL 밤런이 여전히 첫 관측
⑦ **프로브/무인 러너의 자율 플래그는 사람이 정한다** — 스캐폴드는 비워 두고 env로 덮는다.
  L에서 쓴 값: `CLAUDE_FLAGS='--dangerously-skip-permissions'`(armA `opencode run --auto`
  대응, arm 패리티), 프로브는 세 셀 동일 등급(opencode는 `--auto`)
⑧ **프로브는 격리 클론에서 돌린다** — "읽기 전용"은 프롬프트의 말일 뿐 강제되지 않는다.
  L에서는 셀마다 클론을 떠서 서로·원본을 오염시킬 수 없게 했고, 실행 후 셋 다 clean 확인

## 원자료 위치

| 무엇 | 어디 |
|---|---|
| L 설계·판정·결과 전문 | `gridcalc/grading/EXPERIMENT.md` (`:8` / `:162` / `:242`) |
| armSN 라이브 레포 | `/Users/arden/code/gridcalc-sonnet` (`6e8940f` → `38e02b8`, clean) |
| armSN 아카이브 | `gridcalc/armSN-sonnet/` — 스냅샷 + `gridcalc-sonnet.git.bundle` + trajectory.csv |
| **검토자 3인 원본 출력** | `gridcalc/runner-logs/verifier-probe/*.md` (gpt 파일은 ANSI 포함 — `sed 's/\x1b\[[0-9;]*m//g'`) |
| 블라인드 프롬프트 (수정 금지) | `gridcalc/verifier_probe_prompt.txt` |
| 빌드 세션 로그 | `gridcalc/runner-logs/sonnet-solo/session_1.log` |
| 변이 하네스 (자) | `gridcalc/grading/mutate_lineage.py` (M7·M8·M15) |
| 변이 쓸이 (자를 찾은 도구) | `gridcalc/grading/sweep_lineage.py` (16종, VALUE/BLIND 축) |
| held-out oracle v2 | `gridcalc/grading/gridcalc_oracle.py` (134) |
| 러너 | `gridcalc/sonnet_solo_loop.sh`, `gridcalc/verifier_probe.sh` |
| 블로그 원고 | `~/code/ardenspace-portfolio/src/content/ko/blog/same-mind-blind-spots.mdx` |
| 이전 핸드오프 (XL 갈래, 유효) | `SESSION-HANDOFF-2026-07-16.md` |

### 재현 명령

```bash
cd /tmp && python3 -c "import gridcalc"        # 반드시 실패해야 정상 (오염 검사)

cd /Users/arden/code/gridcalc-sonnet && python3 -m pytest -q          # 107 passed

cd gridcalc/grading && PYTHONPATH=/Users/arden/code/gridcalc-sonnet \
  python3 -m pytest gridcalc_oracle.py -q                             # 134 passed

python3 gridcalc/grading/mutate_lineage.py run /Users/arden/code/gridcalc-sonnet
#   M7 KILLED / M8 KILLED / M15 SURVIVED

# 아카이브 bundle만으로 어디서든 복원
git clone gridcalc/armSN-sonnet/gridcalc-sonnet.git.bundle <어디든>
```
