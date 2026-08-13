# 결선 발표 스크립트 — Team AI Cost Radar (~2분 30초)

> 부문: 결선 "모두를 위한 서비스" · 대시보드: https://sechan9999.github.io/upstage-agent-skills/FINALS_dashboard.html
> [ ] = 화면 큐 · 굵은 문장은 꼭 살릴 핵심

---

## [0:00–0:20] 훅
[화면: 대시보드 상단, KPI 타일이 보이게]

"Andrej Karpathy가 말했습니다 — **AI 코딩 비용의 90%는 불필요한 비용이다.**
12개월 뒤, 월 200달러 쓰는 개발자와 4,000달러 쓰는 개발자의 격차는 실력이 아니라 **라우팅**입니다.
문제는 — 개인도 자기 낭비를 잘 못 보는데, **팀은 아무도 전체를 못 본다**는 겁니다."

## [0:20–0:35] 이게 뭔가
"그래서 만들었습니다. **Team AI Cost Radar** — 팀 전체의 AI 사용을 받아 낭비를 진단하고, 라우팅 정책으로 절감하는 서비스입니다. Solar Pro 4와 타임리 Agent 위에서 돌아갑니다."

## [0:35–1:40] 데모 워크스루
[화면: KPI 타일 4개 가리키며]
"먼저 5초 요약. 이 팀은 이번 달 **4,180달러**를 썼고, 그중 **추정 낭비가 2,880달러 — 지출의 69%**입니다. 라우팅 정책을 적용하면 **2,450달러를 절감**할 수 있고, 이미 3개 중 2개 정책이 채택돼 월 1,740달러를 확보했습니다."

[화면: '낭비 Top 원인' 카드]
"낭비가 어디서 나오는지, 시니어 엔지니어들의 10가지 패턴을 팀 로그에 적용해 금액순으로 보여줍니다. 1위는 **과잉 컨텍스트 로딩** — 30줄 고치는데 파일 50개가 자동 로딩되는 거죠. 다음이 기계적 작업에 최상위 모델 쓰기, 프롬프트 캐시 깨짐 순입니다."

[화면: '모델 믹스' 스택 바]
"핵심 진단은 여기입니다 — 지출의 **62%가 최상위 모델**에 몰려 있고, 그중 **약 40%는 저가 모델로도 동일 품질**이 나오는 작업입니다."

[화면: 비용 추세 그래프, 정책 적용 마커]
"6주차에 라우팅 정책을 적용하자, 주당 비용이 **약 41% 떨어졌습니다.**"

[화면: 정책 카드]
"그리고 Solar Pro 4가 팀에 맞는 **라우팅 정책을 제안**합니다 — 기계적 작업은 저가 모델로, 기본 코딩은 중가로, 어려운 것만 최상위로. 각 정책에 예상 절감액이 붙습니다."

## [1:40–2:10] 핵심 서사 — 예선 스킬의 결합
[화면: 하단 푸터]
"**이 서비스는 저희가 예선에서 만든 스킬들이 결합된 결과입니다.**
낭비를 진단하는 건 **Token Cost Optimizer**, 비용 급증을 감지하는 건 **Ops Control Center**, 그리고 대시보드 숫자를 믿어도 되는지 검증하는 건 **Data-Question Guardian**입니다.
예선의 '나를 위한 스킬'들이 결선의 '모두를 위한 서비스'의 부품이 됐습니다."

## [2:10–2:30] 마무리
[화면: 정책 카드의 승인/검토중 상태]
"마지막으로 — 정책은 **제안일 뿐, 실행은 팀 리드가 승인**합니다. AI가 남의 모델 선택을 강제하지 않습니다. 관찰 가능하고, 투명하고, 사람이 결정합니다.
Karpathy의 말대로, 격차는 실력이 아니라 라우팅입니다. **Team AI Cost Radar는 그 라우팅을 팀 전체의 기본값으로 만듭니다.** 감사합니다."

---

## 딜리버리 팁
- **훅과 마무리에 같은 문장**("격차는 실력이 아니라 라우팅") → 수미상관, 기억에 남음
- KPI **69%**와 추세 **41%↓** 두 숫자를 또렷하게 — 청중이 가져가는 건 숫자
- "예선 스킬이 결선의 부품" 서사가 심사 킬러 → 1:40 구간을 자신 있게
- 시간 넘으면 [0:35–1:40] 데모에서 모델 믹스 + 추세만 남기고 압축
- 영어 발표면: 대시보드 EN 토글 + 이 스크립트를 영어로 (요청 시 제공)

## 30초 초압축 버전 (엘리베이터)
"Karpathy는 AI 코딩 비용의 90%가 낭비라고 했습니다. Team AI Cost Radar는 팀의 AI 사용을 진단해 낭비 패턴을 찾고, Solar Pro 4가 라우팅 정책을 제안해 비용을 41% 낮춥니다. 예선에서 만든 스킬 세 개 — 진단·알림·검증 — 가 결합된 서비스이고, 모든 정책은 사람이 승인합니다. 격차는 실력이 아니라 라우팅이니까요."

---
---

# ENGLISH — Finals Pitch Script (~2:30)

> Dashboard: https://sechan9999.github.io/upstage-agent-skills/FINALS_dashboard.html (toggle to EN)
> [ ] = screen cue · **bold** = must-land lines

## [0:00–0:20] Hook
[screen: dashboard top, KPI tiles visible]

"Andrej Karpathy said it: **90% of AI coding cost is unnecessary.**
Twelve months from now, the gap between a developer spending $200 a month and one spending $4,000 isn't skill — it's **routing**.
And here's the problem: individuals can't see their own waste — and a **team can't see it at all.**"

## [0:20–0:35] What it is
"So we built **Team AI Cost Radar** — it takes a team's AI usage, diagnoses where the waste is, and cuts it with routing policies. It runs on Solar Pro 4 and the Timely Agent."

## [0:35–1:40] Demo walkthrough
[screen: the four KPI tiles]
"First, the five-second summary. This team spent **$4,180** this month — and **$2,880 of it is estimated waste, 69% of spend.** With routing policies, they could save **$2,450**, and two of three policies are already adopted, securing $1,740 a month."

[screen: 'Top waste drivers' card]
"Where does the waste come from? We apply the ten patterns senior engineers use, to the team's logs, ranked by dollars. Number one is **over-loading context** — fifty files auto-loaded to fix thirty lines. Then premium models on mechanical tasks, then prompt-cache breakage."

[screen: 'Model mix' stacked bar]
"Here's the key diagnosis — **62% of spend is on the top-tier model, and about 40% of that is work a cheaper model does at the same quality.**"

[screen: cost trend, policy marker]
"When the routing policy went live in week six, weekly cost dropped **about 41%.**"

[screen: policy cards]
"And Solar Pro 4 proposes the routing policies — mechanical work to a low tier, default coding to mid, escalate only the hard tasks — each with its expected savings."

## [1:40–2:10] The core story — skills composed
[screen: footer]
"**This service is our preliminary-round skills, combined.**
Diagnosing waste is **Token Cost Optimizer**. Catching cost spikes is **Ops Control Center**. And checking whether the dashboard numbers can be trusted is **Data-Question Guardian**.
Our 'skills for me' became the building blocks of a 'service for everyone.'"

## [2:10–2:30] Close
[screen: policy approve / pending states]
"And finally — the policies are **proposals; a team lead approves them.** The AI never forces anyone's model choice. It's observable, transparent, and the human decides.
Like Karpathy said, the gap isn't skill — it's routing. **Team AI Cost Radar makes that routing the team's default.** Thank you."

## Delivery tips (EN)
- Same line at hook and close ("the gap isn't skill — it's routing") — bookend, memorable.
- Land two numbers hard: **69%** waste, **41%** down.
- Own the 1:40 "skills composed" beat — it's the judging hook.
- Over time? In the demo, keep only model mix + trend.

## 30-sec elevator (EN)
"Karpathy said 90% of AI coding cost is waste. Team AI Cost Radar diagnoses a team's AI usage, finds the waste patterns, and Solar Pro 4 proposes routing policies that cut cost by 41%. It's three skills we built in the prelims — diagnose, alert, verify — composed into one service, and every policy is human-approved. Because the gap isn't skill — it's routing."
