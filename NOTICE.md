# 출처와 라이선스

## 데이터

| 자료 | 출처 | 라이선스 | 받은 날짜 |
|---|---|---|---|
| FlyWire 뉴런 주석 `Supplemental_file1_neuron_annotations.tsv` | https://github.com/flyconnectome/flywire_annotations | 저장소에 별도 표기 없음. 아래 논문 인용 | 2026-10-27 |
| FlyWire v783 연결 데이터 `Connectivity_783.parquet`, `Completeness_783.csv` | https://github.com/philshiu/Drosophila_brain_model (원 데이터: FlyWire Consortium, Zenodo DOI 10.5281/zenodo.10676866) | 코드 저장소 MIT, FlyWire 데이터 CC BY 4.0(Zenodo 표기) / CC BY-NC 4.0(FlyWire Principles 표기) | 2026-10-27 |

- 표기가 다른 FlyWire 라이선스는 더 엄격한 **CC BY-NC 4.0(비상업)** 기준을 따릅니다.
- `data/processed/`의 파일은 위 데이터에서 팀이 버섯체 회로(우반구 PN·KC·APL·MBON·DAN)만 골라낸 **변경된 자료**입니다(`src/extract_circuit.py`).
- 인용: Dorkenwald, S., et al. (2024). Neuronal wiring diagram of an adult brain. *Nature*, 634, 124–138. / Schlegel, P., et al. (2024). Whole-brain annotation and multi-connectome cell typing of Drosophila. *Nature*, 634, 139–152.

## 코드

| 코드 | 출처 | 라이선스 | 사용 방식 |
|---|---|---|---|
| Drosophila_brain_model (Shiu et al.) | https://github.com/philshiu/Drosophila_brain_model | MIT | 데이터 파일 사용, 코드 참고 |
| fly-brain (Eon Systems) | https://github.com/eonsystemspbc/fly-brain | GPL-2.0-or-later | 참고만, 코드 복사하지 않음 |

## 그림·폰트·음원

현재 PoC의 펫·미로 그림은 팀이 직접 만든 SVG입니다. 외부 소재를 추가하면 여기에 출처와 라이선스를 적습니다.

## AI 사용

이 저장소의 일부 코드와 문서는 AI의 도움으로 작성했습니다. 도구와 내역은 `ai_log/`에 기록합니다.
