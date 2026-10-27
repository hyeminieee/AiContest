# REFLEX · 초파리 신경망을 활용한 대화형 펫의 학습 변화 연구

2026학년도 2학기 한세대학교 AI Contest · 연구 분야 · IT학부(컴퓨터공학·융합보안)
팀: 전혜민(팀장) · 강민혁 · 김현정 / 지도교수: 방제완

초파리 뇌 지도(FlyWire v783)에서 버섯체 학습 회로를 골라 컴퓨터 모델로 만들고, 억제 뉴런 APL의 작용을 약하게 했을 때 정답이 바뀐 뒤 다시 배우는 속도가 어떻게 달라지는지 실험합니다. 결과는 대화형 펫 화면(PoC)으로 보여줍니다.

**처음이면 [가이드라인/REFLEX_팀_진행가이드.docx](가이드라인/REFLEX_팀_진행가이드.docx)부터 읽으세요.**

## 폴더

| 폴더/파일 | 내용 |
|---|---|
| `가이드라인/` | 팀 진행 가이드(Word), 상세 일정(md), 초기 스타터 코드 |
| `poc/` | 현재 PoC 시연 프로그램 (느낌 확인용 시제품, 가짜 연결) |
| `src/download_data.py` | FlyWire 원본 3개 내려받기 |
| `src/extract_circuit.py` | 원본 → 버섯체 회로 추출 |
| `data/processed/` | 가공본: 추출 결과 (`mb_neurons.csv`, `mb_edges.csv`, `circuit_check.txt`) |
| `data/raw/` | 원본 데이터 (저장소에 없음, `download_data.py`로 받기) |
| `ai_log/` | AI 사용 기록 (협업 보드섹션 근거) |
| `NOTICE.md` | 외부 데이터·코드 출처와 라이선스 |

## 처음 실행

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```
```bash
python poc/server.py
```

브라우저에서 http://localhost:8765 → **다음 ▶** 버튼으로 7단계 진행. 종료는 터미널에서 Ctrl + C.

## 데이터

- **가공본** `data/processed/`(약 11MB): 버섯체 회로만 골라낸 결과. 저장소에 포함되어 있어 바로 사용할 수 있습니다.
- **원본** `data/raw/`(약 136MB): 초파리 뇌 전체. 용량 때문에 저장소에 없으니 각자 받습니다.

```bash
python src/download_data.py
```
```bash
python src/extract_circuit.py
```

첫 줄은 원본 3개를 받고, 둘째 줄은 원본에서 회로를 다시 추출합니다(가이드 4·6장).

## 규칙

- API 키, 비밀번호, 개인정보, `data/raw/` 원본은 올리지 않습니다.
- 작업은 브랜치에서 하고 Pull Request로 올립니다. 만든 사람과 다른 사람이 검토합니다.
- AI를 쓴 날은 `ai_log/`에 기록합니다.
- 이 저장소의 코드·문서 일부는 AI(Claude Code, OpenAI Codex 등)의 도움으로 작성되었으며, 그 내역은 `ai_log/`에 남깁니다.
