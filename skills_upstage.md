# Upstage 해커톤 제출 — 나를 위한 스킬 (6종)

> **환경:** 타임리(Timely) Agent × Solar Pro 4
> **부문:** 예선 — "나를 위한 스킬" (내 일상·업무의 문제 해결)
> **크레딧:** 타임리 크레딧은 **8/18 배포** → 그때부터 실사용 가능 (예선 8/18~8/31)
> **한도:** 팀 2인 × 3개 = **최대 6개** → 아래 6개 전부 제출
> **제작자:** hkchun (+ 팀)

---

## 제출 개요

여섯 스킬은 하나의 철학을 공유합니다 — **복잡하고 실수가 비싼 작업을, 사람이 안전하게 판단할 수 있게(그리고 낭비 없이) 만든다.** 완전 자동화로 없애는 게 아니라, 관찰 가능하고 정직하게. 제가 매일 부딪히는 문제들을 각각 하나의 스킬로 만들었습니다.

| # | 스킬 | 해결하는 문제 |
|---|------|---------------|
| 1 | **Token Cost Optimizer** (토큰 비용 라우터) ⭐ | AI 코딩/에이전트 비용의 90%가 낭비 |
| 2 | **Ops Control Center** (운영 관제) | 알림·로그가 쏟아지면 뭐부터 볼지 모름 |
| 3 | **Human-Voice Writer** (탈-AI 문체) | 자소서·포스트·이메일이 "AI가 쓴 티" |
| 4 | **Data-Question Guardian** (쿼리 전에 생각) | 데이터 숫자를 성급히 믿었다가 틀림 |
| 5 | **Interview Prep Coach** (면접 코치) | 면접 준비가 매번 처음부터, 흩어짐 |
| 6 | **Bilingual Explainer** (쉬운 설명 EN/KO) | 어려운 걸 비전문가에게 전달하기 |

각 스킬 상세: [`skills/`](./skills/) 폴더

---

## 스킬 요약

**1. Token Cost Optimizer ⭐** — 토큰 낭비 10패턴 진단 + 작업↔모델 라우팅으로 같은 결과를 싸게. *"AI 코딩 비용의 90%는 불필요"(Karpathy, 인용 @DeRonin_) — 격차는 실력이 아니라 라우팅."* → [파일](./skills/token-cost-optimizer.md)

**2. Ops Control Center** — 알림·로그·지표를 "뭐 바뀜/어디 집중/뭐부터"의 우선순위 브리핑으로, 사람 승인용 조치안. → [파일](./skills/ops-control-center.md)

**3. Human-Voice Writer** — 글을 AI 지문 없이 자연스러운 사람 문체로. 사실·숫자 100% 보존. → [파일](./skills/human-voice-writer.md)

**4. Data-Question Guardian** — 데이터 답 전에 소비자·신뢰성·가정을 먼저 점검. 못 믿으면 정직하게 말함. → [파일](./skills/data-question-guardian.md)

**5. Interview Prep Coach** — 3단계(스토리→질문연습→채점)로 면접 준비, 누적 개선. → [파일](./skills/interview-prep-coach.md)

**6. Bilingual Explainer** — 어려운 개념을 비유 하나 + 쉬운 말로, 영/한 둘 다. → [파일](./skills/bilingual-explainer.md)

---

## 사용법 (How to use)
각 파일은 타임리 Agent에 등록할 **자연어 스킬 정의**입니다. 형식: `Trigger · Input · Instructions · Output · Example · Guardrails`. 타임리 스킬 등록 스키마에 매핑해 붙여넣으세요.

---

## 결선 — "모두를 위한 서비스" 확장안
예선의 개인용 스킬을 팀/조직용 서비스로 확장합니다. 대표작:
**Team AI Cost Radar** — Token Cost Optimizer(개인 진단)를 **팀 전체 AI 비용 대시보드**로.
상세 설계: [`FINALS_team_cost_radar.md`](./FINALS_team_cost_radar.md)
