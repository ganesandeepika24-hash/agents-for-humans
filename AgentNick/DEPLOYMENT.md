# AgentNick — Deployment Record

## Status
Deployed and verified working on Amazon Bedrock AgentCore.

## Details
- **Runtime ARN**: `arn:aws:bedrock-agentcore:eu-central-1:299276269111:runtime/AgentNick_AgentNick-a4vHUs5YeY`
- **Region**: eu-central-1 (Frankfurt)
- **Model**: Claude Sonnet 4.5 via EU cross-region inference profile (`eu.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Status**: READY (confirmed via `agentcore status`)

## Verification performed
- `agentcore invoke "Say hello and confirm you are working"` — returned correct AgentNick identity and tagline
- `agentcore invoke` with real tariff scenario data — full pipeline (parse → compare_costs → check_savings_threshold → stage_financial_card) executed correctly on live infrastructure, produced correct £466 savings figure and staged card matching local test results

## Notable deployment issues resolved
- IAM user required explicit CloudFormation, SSM, ECR, and broader permissions beyond initial Bedrock-only scope — resolved via AdministratorAccess policy attachment (appropriate for this disposable hackathon account only)
- CDK bootstrap initially failed (`CloudFormationStack object does not hold a stack`) due to a stuck `CDKToolkit` stack in `ROLLBACK_FAILED`/`DELETE_FAILED` state from an earlier permission-blocked attempt — resolved by deleting the stack and re-bootstrapping via direct `cdk bootstrap` command
