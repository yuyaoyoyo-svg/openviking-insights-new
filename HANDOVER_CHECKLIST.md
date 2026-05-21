# Handover Checklist

This checklist is for the next owner of `openviking_insights`.

Use it in order. Do not migrate to GitHub Actions before local execution is verified.

## 1. Get The Right Files

- [ ] Get the full repository code
- [ ] Confirm these files exist:
  - `README.md`
  - `.env.example`
  - `run_daily.sh`
  - `run_github_actions.sh`
  - `.github/workflows/daily-insights.yml`
  - `src/check_snapshot_integrity.py`
  - `src/dedupe_snapshot_records.py`
  - `src/fix_star_history_from_stargazers.py`

## 2. Get Sensitive Config Securely

- [ ] Receive `.env` contents through a secure channel, not via git
- [ ] Receive or recreate `OV_GITHUB_TOKEN`
- [ ] Receive `LARK_APP_ID`
- [ ] Receive `LARK_APP_SECRET`
- [ ] Receive `LARK_BASE_TOKEN`
- [ ] Receive `LARK_TABLE_ID`
- [ ] Receive `LARK_TRENDS_TABLE_ID` if trends sync is needed
- [ ] Receive `LARK_OPENVIKING_TRAFFIC_TABLE_ID` if traffic sync is needed
- [ ] Receive `LARK_OPENVIKING_FUNNEL_TABLE_ID` if funnel sync is needed

## 3. Prepare Local Machine

- [ ] Install Python 3.11 or newer
- [ ] Install `gh`
- [ ] Install `lark-cli`
- [ ] Clone the repository locally
- [ ] Copy `.env.example` to `.env`
- [ ] Fill `.env` with the real values

## 4. Verify Local Auth

- [ ] Run `gh auth status`
- [ ] Confirm the GitHub account has access to `volcengine/OpenViking`
- [ ] Confirm the GitHub auth method can access traffic endpoints
- [ ] Run `lark-cli auth status`
- [ ] Confirm the Lark identity is valid for local runs

## 5. Verify Local Run

- [ ] Run:

```bash
pip install -r requirements.txt
./run_daily.sh
```

- [ ] Confirm a new local file appears under `data/insights_YYYY-MM-DD.json`
- [ ] Confirm the main Lark snapshot table receives new rows
- [ ] Confirm OSSInsight trends sync behaves as expected
- [ ] Confirm GitHub traffic export succeeds
- [ ] Confirm `src/check_snapshot_integrity.py` reports no high-confidence issues

## 6. Learn Recovery Tools

- [ ] Know how to re-upsert a historical day:

```bash
python3 src/backfill_snapshot_day.py data/insights_YYYY-MM-DD.json
```

- [ ] Know how to dedupe snapshot records:

```bash
python3 src/dedupe_snapshot_records.py --start YYYY-MM-DD --end YYYY-MM-DD --apply
```

- [ ] Know how to repair exact star history from GitHub stargazers:

```bash
python3 src/fix_star_history_from_stargazers.py YYYY-MM-DD YYYY-MM-DD \
  --repo volcengine/OpenViking \
  --repo NevaMind-AI/memU \
  --sync-lark \
  --dedupe
```

## 7. Before GitHub Actions Migration

- [ ] Confirm local daily run is stable for several days
- [ ] Confirm all required table IDs are correct
- [ ] Confirm the Lark app has access to the target Base and tables
- [ ] Confirm the GitHub PAT has the required scopes and repo access

## 8. Configure GitHub Actions

- [ ] Push the repository to GitHub without `.env`, logs, or local runtime data
- [ ] Open `Settings -> Secrets and variables -> Actions`
- [ ] Add these required secrets:
  - `OV_GITHUB_TOKEN`
  - `LARK_APP_ID`
  - `LARK_APP_SECRET`
  - `LARK_BASE_TOKEN`
  - `LARK_TABLE_ID`
- [ ] Add optional secrets if those sync paths are needed:
  - `LARK_TRENDS_TABLE_ID`
  - `LARK_OPENVIKING_TRAFFIC_TABLE_ID`
  - `LARK_OPENVIKING_FUNNEL_TABLE_ID`

## 9. Validate GitHub Actions

- [ ] Open the workflow:
  - `.github/workflows/daily-insights.yml`
- [ ] Trigger `workflow_dispatch` manually
- [ ] Check GitHub Actions logs for authentication failures
- [ ] Confirm artifacts are uploaded
- [ ] Confirm the main Lark table updates correctly
- [ ] Confirm trends / traffic / funnel sync only if their secrets are configured
- [ ] Confirm no duplicate snapshot rows are introduced

## 10. Final Cutover

- [ ] Decide the official runtime owner:
  - local machine
  - GitHub Actions
- [ ] If GitHub Actions is stable, stop relying on local `launchd`
- [ ] Keep local repair scripts available for backfill and incident handling
- [ ] Update the owner, handover notes, and token rotation record

## 11. Never Commit These

- [ ] `.env`
- [ ] real tokens or app secrets
- [ ] `logs/`
- [ ] `data/insights_*.json`
- [ ] `data/github-traffic/`
- [ ] local `.plist`
- [ ] temporary debug or repair files
