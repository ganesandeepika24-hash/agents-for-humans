# AgentNick

**"Intercepting unnecessary expenses in the nick of time."**

A proactive personal finance agent built for the AWS "Agents for Humans" hackathon. AgentNick watches a user's recurring financial commitments — contract renewals, free trials converting to paid, promotional rates expiring — and surfaces exactly what's changing, what alternatives exist, and what to do, before money moves silently.

**Live demo:** https://agentnick-finance-guard.lovable.app
**Repository:** https://github.com/ganesandeepika24-hash/agents-for-humans

---

## The core commitment

If a signal indicates money will be taken or a good rate will be lost unless the user acts by a date, AgentNick proactively raises this **before** that date. Silence before a charge is treated as a failure, even if the correct decision turns out to be "do nothing."

The agent is genuinely general-purpose, not hardcoded to the scenarios demoed. This was proven by testing a novel "gym membership" scenario never coded anywhere — the agent handled it correctly first try, including independently applying a payment-frequency-arbitrage check it was never explicitly told to look for in that case.

---

## Architecture

```
Browser/Phone → Lovable Frontend → FastAPI Backend (Replit) → AWS Bedrock AgentCore (Strands Agent + Claude Sonnet 4.5)
                                          │
                                          ├─→ Resend (real email)
                                          └─→ Web Push (real phone/browser notifications)
```

- **The agent itself** is deployed to AWS Bedrock AgentCore Runtime — a Strands Agents SDK agent (system prompt + tools + Claude Sonnet 4.5), invoked via `boto3`'s `bedrock-agentcore` client.
- **The backend** (FastAPI, hosted on Replit) is plain infrastructure — no AI itself — handling auth, persistent state, email, push notifications, and a background scheduler.
- **The frontend** (built with Lovable) is the React dashboard end users interact with.

See `docs/architecture-diagram.png` for a full visual breakdown.

---

## Tools & technologies

| Tool | Role |
|---|---|
| Claude Sonnet 4.5 | The reasoning model — decides what matters, what to recommend |
| Strands Agents SDK | Combines the model + our system prompt + our tools into the actual agent |
| Amazon Bedrock AgentCore | Managed, serverless hosting for the deployed agent |
| FastAPI | Backend web framework (plain infrastructure, not AI) |
| SQLite | All persistent state — users, cards, jobs, settings, subscriptions |
| Replit | Hosts the FastAPI backend with a stable public URL |
| Lovable | Generated and hosts the React frontend |
| Resend | Real transactional email delivery |
| Web Push API / VAPID | Real browser/OS push notifications (standard web platform feature) |
| Google Gmail API (OAuth, read-only) | Real email-based signal ingestion (see Data Sourcing below) |

---

## Data sourcing — what's real, what's mocked, and why

This is a deliberately honest section. A judge should be able to tell exactly which parts of the demo reflect real-world data access versus illustrative placeholders.

### Real, working, and tested against live data
- **Gmail read-only OAuth connection** — genuinely connects to a real Gmail account, fetches real recent emails, and extracts financial-signal fields from them via Claude (the same extraction logic used for document uploads). Tested against a real inbox; correctly returned zero false positives when no matching emails existed, rather than inventing data. Wired into the automatic 30-minute background scheduler for connected users — no manual trigger needed. Users can disconnect access at any time via a dedicated in-app control, and are shown a clear explanation of what will be accessed before being sent to Google's consent screen.
- **Real per-user data isolation** — each user gets their own independent copy of scenario data (seeded from a shared template on first use, then genuinely editable per-user), not one dataset shared by every account.
- **All derived financial data encrypted at rest** — not just email addresses (Fernet symmetric encryption), but also the actual card/signal data stored per user, consistent protection throughout the data model.
- **Document upload extraction** — a real, working pipeline: upload a statement (PDF/image), Claude extracts the relevant fields via Bedrock's `converse` API. Verified against a real mock bank statement, correctly pulling the actual interest rate from the document.
- **Real email sending** (Resend) and **real push notifications** (Web Push/VAPID) — both fully functional, not simulated.

### Mocked for the demo, with a clear real-world path
- **Broadband, trial, and credit-card scenario data** — three example datasets standing in for what a real Open Banking connection and email-parsing pipeline would surface. The system is architected so this swap is clean: once real data exists in the same normalized shape, it flows through the identical agent pipeline with zero changes to the reasoning logic.
- **Market comparison / competitor pricing** — illustrative reference data, not a live scraper against real provider websites (a basic scraping tool, `check_web_portal`, exists but was only tested against our own mock site).
- **Currency conversion rates** — a small illustrative reference table, not a live FX feed. A production version would connect to a real exchange-rate API.
- **Cooling-off period windows** — a small reference table of typical categories (e.g. 14 days for online purchases), explicitly not a legal source. Actual cooling-off rights vary by provider, product, and jurisdiction; users are always told to verify their specific contract terms.

### Real-world data-source breakdown (by scenario)

| What we need to know | Best real source | Fallback |
|---|---|---|
| Current balance, payments, APR | Open Banking (real transaction data) | Document upload |
| Contract terms, renewal dates, promo end dates | Email (providers are legally required to send end-of-contract notices in the UK) | Document upload |
| Personalized/logged-in-only retention offers | No clean API exists for this anywhere — requires either a browser-session-based agent (roadmap) or manual user input | Manual entry |
| Market-wide comparable pricing | Public web data | — |

---

## Notification channels — how a user actually gets alerted

Three channels work together, each with a real, honest scope:

1. **Email** — reaches the user regardless of device, the moment they sign up, no extra setup.
2. **Push notifications** — real, work even with the browser fully closed, but are **per-device and per-browser**, not account-wide. Enabling notifications on a phone does not automatically enable them on a laptop, or in a different browser on the same device — this mirrors how virtually all real push-notification products work (e.g. enabling Gmail notifications on Android doesn't enable them in a desktop browser). A thorough user enables push on whichever specific device(s) they want alerted.
3. **In-app badge** — a lightweight "N new updates" indicator, only visible while the app tab is open (even backgrounded) on that specific device at the time.

In-notification action buttons (resolving a card directly from the notification, no app needed) are implemented and functional on browser/OS combinations that support the underlying web standard — this varies by platform (a known, real inconsistency, not a bug in our code, confirmed via direct browser-level testing that bypassed our own backend entirely). Everywhere else, tapping the notification opens directly to the correct card via deep-linking.

---

## Setup instructions

### Prerequisites
- AWS account with Bedrock model access, `eu-central-1` region
- `uv` (Python package manager) and the `agentcore` CLI
- A Replit account (or any host capable of running a FastAPI app)
- Accounts for Resend (email) and Google Cloud Console (Gmail OAuth), if using those features

### Deploying the agent
```bash
cd AgentNick
agentcore deploy
```

### Running the backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

Required environment variables (see `backend/.env` for the full list): AWS credentials, `RESEND_API_KEY`, `VAPID_PUBLIC_KEY`/`VAPID_CLAIM_EMAIL`, `EMAIL_ENCRYPTION_KEY`, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_REDIRECT_URI` (for Gmail integration).

---

## Google OAuth verification readiness

The Gmail integration was deliberately built to structurally align with what Google's own review process for restricted scopes (`gmail.readonly`) actually evaluates, not just to work technically:

- **Minimum necessary scope**: read-only access only, never `gmail.modify` or broader access.
- **Revocable from within the app**: a real "Disconnect Gmail" control, not just reliance on Google's own account settings page.
- **Informed consent before redirect**: users see a plain-language explanation of what will be accessed and why, before being sent to Google's consent screen — not just Google's own generic prompt.
- **Encryption throughout**: both the OAuth refresh token and all data derived from email content are encrypted at rest.

**What's genuinely still required for public production use, and honestly out of scope for tonight**: Google's restricted-scope verification requires a published privacy policy and a formal third-party CASA security assessment, a process that takes weeks by design (true for any application requesting this level of access, not specific to this build). The current submission demonstrates the real, working mechanism via a pre-approved test account; broader public rollout is a known, standard next step, not a gap in the architecture.

## Known limitations & roadmap

Documented honestly, not hidden:

- **Authentication is email-only, not full OAuth login** — a deliberate choice made to avoid a cross-domain redirect-chain failure risk close to the submission deadline. Real OAuth (Google/Microsoft sign-in) is a near-term roadmap item.
- **Market comparison data is illustrative**, not a live scraper against real provider websites.
- **Currency conversion and cooling-off windows use illustrative reference data**, not live feeds or legal sources.
- **Notification action buttons** don't render on all browser/OS combinations — a genuine platform inconsistency (confirmed via direct testing), gracefully degrading to tap-to-open everywhere.
- **CORS is scoped to the specific known frontend origins** used in this build; a production deployment supporting arbitrary frontends would need a different approach.

---

## Tool usage disclosure

This project was built with substantial assistance from AI tools, used transparently throughout:
- **Claude** (Anthropic) — primary development assistant for backend/agent code, debugging, and architecture decisions throughout the build.
- **Lovable** — AI-assisted generation and iteration of the React frontend.
- **Replit's built-in AI agent** — used for backend deployment management, dependency installation, and operational tasks on the hosting environment.

All AI-assisted code was reviewed, tested, and iterated on by the developer throughout the build process, including catching and fixing multiple genuine bugs found through real testing (not just theoretical review).
