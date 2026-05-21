# GitHub Actions Setup

This repository is now structured so that local secrets and runtime outputs do not need to be committed.

## Required GitHub Secrets

### GitHub

- `OV_GITHUB_TOKEN`
  - Personal access token used by `main.py` and `gh api`
  - Must be able to read the configured repositories
  - Must also be able to access `repos/volcengine/OpenViking/traffic/*`

### Lark / Feishu

- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`

## Optional GitHub Secrets

- `LARK_TRENDS_TABLE_ID`
  - Enables OSSInsight trends sync
- `LARK_OPENVIKING_TRAFFIC_TABLE_ID`
  - Enables daily traffic table sync
- `LARK_OPENVIKING_FUNNEL_TABLE_ID`
  - Enables daily funnel table sync

If optional table IDs are not provided, the workflow still runs collection and uploads artifacts, but skips the missing sync step.

## One-Time Preparation

1. Create or verify the target Lark Base and tables.
2. Add the Lark app to the target Base with sufficient permissions.
3. Store the Base token and table IDs in GitHub Secrets.
4. Add `OV_GITHUB_TOKEN` to GitHub Secrets.

## Local vs CI

- Local development reads `.env`
- GitHub Actions reads repository secrets
- CI sets:
  - `LARK_IDENTITY=bot`
  - `OV_GH_PREFER_ENV=1`
  - `WRITE_ENV_UPDATES=0`

This means CI will not try to rewrite `.env`, and `gh api` will use the token from secrets instead of a local keyring session.

## Triggering

- Scheduled workflow: `.github/workflows/daily-insights.yml`
- Manual trigger: `workflow_dispatch`

## Notes

- Runtime data files under `data/insights_*.json`, `data/github-traffic/`, and `logs/` are ignored by git.
- If you need to repair historical star deltas after a missed run, use:

```bash
python3 src/fix_star_history_from_stargazers.py 2026-05-10 2026-05-12 \
  --repo volcengine/OpenViking \
  --repo NevaMind-AI/memU \
  --sync-lark \
  --dedupe
```
