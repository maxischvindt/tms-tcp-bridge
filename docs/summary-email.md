# Summary email to the prospect

Following up on our conversation about inbound carrier calls. We built a working
version against your actual load data, and it's live — happy to have your team
call in and try it.

**What it does today.** A carrier dials in and speaks to the agent. The agent
verifies the carrier, asks what lane and equipment they're running, and searches
your TMS in real time. It pitches matching loads, handles the rate conversation
over 2 rounds within the guardrails we set, and books the load back into the
TMS when they agree. Anything outside those bounds transfers to a live rep with
the context already gathered. Every call is classified by outcome and sentiment
and lands on a dashboard (TODO).

**What we had to solve.** Your TMS speaks a raw TCP line protocol, not HTTP, so
there was no way for a voice agent to reach it directly. We built a small bridge
service that translates between the two, with retries and timeouts so a slow or
flaky TMS response doesn't become dead air on a live call. It's read-mostly:
three endpoints — search, look up, book — and nothing else is exposed.

**Links**

- Live agent: https://platform.happyrobot.ai/deployments/development/zx82rxch5182
- Build description for your IT and business teams: GitHub repository - docs/build-description.md
- Code: https://github.com/maxischvindt/tms-tcp-bridge — private, reviewers invited
- Walkthrough videos: https://drive.google.com/drive/folders/1k0H2W9eVdKnqXBWqQiL7lAHTeEdKdm_Y?usp=sharing

**Next steps.** I'd suggest 30 minutes with whoever owns the TMS on your side to
walk through the integration and the security questions in the attached doc. From
there the open items are: which lanes and equipment types to enable first, what
rate authority the agent should have without a human, and where the calls should
transfer when it hands off.

Best,
Maxi Schvindt

---

