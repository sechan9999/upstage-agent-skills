# Upstage Agent Skills — 나를 위한 스킬 3종

**Upstage 해커톤 예선 제출** · 타임리(Timely) Agent × Solar Pro 4 · 부문: "나를 위한 스킬"

세 개의 자연어 스킬 — 복잡하고 실수가 비싼 작업을 **사람이 안전하게 판단할 수 있게** 만듭니다.

| 스킬 | 한 줄 |
|------|-------|
| [Token Cost Optimizer](./skills/token-cost-optimizer.md) ⭐ | 토큰 낭비 진단 + 작업↔모델 라우팅으로 같은 결과를 싸게 |
| [Ops Control Center](./skills/ops-control-center.md) | 쏟아지는 알림/로그를 "뭐 바뀜·어디 집중·뭐부터"로 |
| [Human-Voice Writer](./skills/human-voice-writer.md) | 글을 AI 티 안 나게 자연스러운 사람 문체로 다시 씀 |
| [Data-Question Guardian](./skills/data-question-guardian.md) | 데이터 답 전에 소비자·신뢰성·가정을 먼저 점검 |
| [Interview Prep Coach](./skills/interview-prep-coach.md) | 3단계(스토리→질문연습→채점) 면접 준비, 누적 개선 |
| [Bilingual Explainer](./skills/bilingual-explainer.md) | 어려운 개념을 비유+쉬운 말로, 영/한 둘 다 |

> 예선 한도 = 팀 2인 × 3개 = **6개 전부 제출**. 타임리 크레딧 **8/18 배포**부터 사용.
> **결선 "모두를 위한 서비스":** [Team AI Cost Radar](./FINALS_team_cost_radar.md) — 팀 AI 비용 대시보드.
> **대시보드 목업 (EN/KO):** [`FINALS_dashboard.html`](./FINALS_dashboard.html) — 브라우저로 열기.

📄 제출 문서: [`skills_upstage.md`](./skills_upstage.md)

## 구조
```
skills_upstage.md              예선 제출 개요 (6종)
FINALS_team_cost_radar.md      결선 "모두를 위한 서비스" 설계
skills/
  token-cost-optimizer.md      스킬 1 (⭐)
  ops-control-center.md        스킬 2
  human-voice-writer.md        스킬 3
  data-question-guardian.md    스킬 4
  interview-prep-coach.md      스킬 5
  bilingual-explainer.md       스킬 6
```

각 스킬은 `Trigger · Input · Instructions · Output · Example · Guardrails` 형식의 자연어 정의로,
타임리 Agent의 스킬 등록 스키마에 맞게 매핑해 사용합니다.
