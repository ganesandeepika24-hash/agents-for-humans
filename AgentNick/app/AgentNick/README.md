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

This is a deliberately honest section, so it's clear exactly which parts reflect real-world data access versus illustrative placeholders.

### Real, working, and tested against live data
- **Gmail read-only OAuth connection** — connects to a real Gmail account, scans recent emails, and **classifies each one into whichever real-world category it actually belongs to** (broadband, trial, card promo, insurance, membership) in a single pass, with no category specified in advance. Extracts the relevant fields per category via Claude, merges them onto the user's data, and runs a full evaluation — correctly distinguishing between categories from a single scan of real email content.
- **Recurring-subscription pattern detection** — goes beyond reading explicit renewal notices: scans historical receipt/payment-confirmation emails, groups them by sender, and asks Claude to infer the billing cycle and **predict the next charge date purely from the pattern of past charges** — even when no single email ever states a future date. Verified with real receipt data, correctly inferring provider, amount, billing frequency, and the exact next charge date. The agent applies the same judgment here as everywhere else: a detected subscription only surfaces as a card when there's genuinely something worth the user's attention, not on every detection.
- **Real per-user data isolation with no auto-seeding** — a brand-new account starts with a genuinely empty feed, not shared placeholder content. Example/mock scenarios are only ever created through an explicit user action or a real connected source (Gmail), matching how any real product with connected data sources should behave.
- **Gmail connection is structurally built toward Google's real verification requirements**: minimum-necessary scope (read-only only), a working in-app "Disconnect Gmail" control, a plain-language explanation shown before the user is sent to Google's consent screen, and encryption of both the OAuth token and all data derived from email content.
- **Document upload extraction** — upload a statement (PDF or image), and Claude extracts the relevant fields via Bedrock's `converse` API, correctly reading figures such as interest rates directly from the document.
- **Real email sending** (Resend) and **real push notifications** (Web Push/VAPID) — both fully functional, not simulated.

### Mocked for the demo, with a clear real-world path
- **Seven real-world scenario categories**: broadband/tariff, free trial, credit card promo, insurance renewal, and membership/subscription renewal, plus an intentionally-incomplete card promo variant used to test the missing-data flow. Three (tariff, card promo, membership-via-pattern-detection) are proven end-to-end with genuine extracted or inferred real data. Insurance and general membership extraction schemas share the identical mechanism and are ready for the same live-data validation.
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

In-notification action buttons — resolving a card directly from the notification, with no need to open the app — are supported on browser/OS combinations that implement the underlying web notification standard, with a graceful fallback everywhere else: tapping the notification opens directly to the correct card via deep-linking.

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

**Path to full public availability**: `gmail.readonly` is classified by Google as a restricted scope, which requires a published privacy policy and a formal third-party CASA security assessment before any application can move from testing to general availability — a standard, weeks-long process required of every application requesting this level of access, not specific to this build. The current implementation demonstrates the complete, real mechanism working end-to-end via a Google-approved test account; extending access to arbitrary public users is a well-defined next step through Google's own verification pipeline, not an architectural gap.

## Roadmap — what's next

Real, planned next steps for this project:

- **Full OAuth login** (Google/Microsoft sign-in) — the current email-based identity is a deliberate first step, with full OAuth planned as the natural next iteration of the authentication layer.
- **iOS/Safari push notification support** — enabling the "Add to Home Screen" (PWA) flow required by iOS for web push notifications, extending the notification system already proven on Android and desktop browsers.
- **Live market comparison data** — replacing illustrative reference data with a real, ongoing scraper or comparison-site data feed.
- **Live currency conversion and jurisdiction-aware cooling-off windows** — replacing the current illustrative reference tables with a real FX API and researched, per-category legal rules.
- **Broader in-notification action button support** — already implemented and working on browsers/OS combinations that support the underlying standard; expanding coverage as platform support evolves.
- **Open CORS support for arbitrary frontends** — currently scoped to this build's known origins, straightforward to broaden for a wider production deployment.
- **Google OAuth production verification** — completing the privacy policy publication and CASA security assessment needed for `gmail.readonly` to move from testing to full public availability.

---

## Tool usage disclosure

This project was built with substantial assistance from AI tools, used transparently throughout:
- **Claude** (Anthropic) — primary development assistant for backend/agent code, debugging, and architecture decisions throughout the build.
- **Lovable** — AI-assisted generation and iteration of the React frontend.
- **Replit's built-in AI agent** — used for backend deployment management, dependency installation, and operational tasks on the hosting environment.

All AI-assisted code was reviewed and tested by the developer throughout the build process.