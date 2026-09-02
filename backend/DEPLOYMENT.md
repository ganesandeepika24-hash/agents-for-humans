# AgentNick Backend — Deployment Record

## Status
Migrated from GitHub Codespaces to Replit for a stable, permanent URL,
after Codespaces' own port-forwarding tunnel proved unreliable
(repeated stuck sessions, 504 gateway timeouts on longer requests).

## Live URL
https://f917a6d1-f299-444c-96af-61b8209cfd8c-00-339l9ymu91s2a.archer.replit.dev

## Secrets configured on Replit
- AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION (eu-central-1)
- RESEND_API_KEY (regenerated fresh for this migration)
- VAPID_PUBLIC_KEY / VAPID_CLAIM_EMAIL (VAPID keypair regenerated fresh
  directly on Replit — private key never left the Replit environment)
- DEMO_RECIPIENT_EMAIL
- SESSION_SECRET

## Verified working
- GET / -> 200, real status response
- POST /login -> real session token issued
- POST /check -> async job pattern, returns job_id immediately
- GET /check-status/{job_id} -> polled successfully, real agent
  evaluation completed in ~55s, correct signal_id, correct card data
