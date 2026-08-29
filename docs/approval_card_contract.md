# Approval Card Contract

This is the shared JSON shape between the AgentNick backend and the frontend dashboard.
Every approval card returned by `stage_approval_card` follows this structure.

## Schema

```json
{
  "card_id": "string, unique per card",
  "scenario_type": "trial_cancellation | broadband_tariff | card_promo | hobby_registration",
  "title": "string, short human-readable headline",
  "summary": "string, 1-2 sentence explanation of what triggered this card",
  "computed_savings_gbp": "number or null, if applicable",
  "threshold_met": "boolean, true if savings exceed the £30 alert threshold",
  "action": {
    "type": "email | action_url",
    "email_payload": {
      "to": "string",
      "subject": "string",
      "body": "string"
    },
    "action_url": "string or null"
  },
  "status": "pending | approved | rejected"
}
```

## Example — Trial cancellation (email action)

```json
{
  "card_id": "card_001",
  "scenario_type": "trial_cancellation",
  "title": "Cancel ExampleStreaming before you're billed",
  "summary": "Your free trial ends 2026-09-02. Cancel now to avoid a £12.99 charge.",
  "computed_savings_gbp": 12.99,
  "threshold_met": false,
  "action": {
    "type": "email",
    "email_payload": {
      "to": "support@examplestreaming.com",
      "subject": "Cancel my subscription",
      "body": "Please cancel my ExampleStreaming trial effective immediately."
    },
    "action_url": null
  },
  "status": "pending"
}
```

## Example — Broadband tariff (link-out action)

```json
{
  "card_id": "card_002",
  "scenario_type": "broadband_tariff",
  "title": "Your ExampleISP contract is ending — switch and save",
  "summary": "Renewal price rises to £65/mo. RivalISP offers the same 150Mbps for £38/mo.",
  "computed_savings_gbp": 304.00,
  "threshold_met": true,
  "action": {
    "type": "action_url",
    "email_payload": null,
    "action_url": "https://example-isp-retention-portal.test/account"
  },
  "status": "pending"
}
```

## Action tier rule

- `email`: used when the action can be completed without login (cancellations, notifications).
- `action_url`: used when the action requires account authentication (switching provider, balance transfer, portal-based enrollment). The agent has already done the noticing, comparing, and deciding — the user's remaining step is one click to the correct destination.
