# Security Protocol: Kansas Crop Rotation Advice

Owner: Varun Pisharody (data analysis). Written by Claude (Anthropic AI) on 2026-11-15 and checked against this repo.
This repo is **public**. Anything committed here can be seen by anyone, forever, even after it's deleted.

## 1. What is public and what is secret

| Item | Class | Where it lives |
|---|---|---|
| Code, data, reports, AI record (this repo) | Public | GitHub, Google Drive folder, soilsense copy |
| App advice file `app_rotation_advice.json` | Public, read-only | Cloudflare R2 public link (r2.dev) |
| Cloudflare R2 upload keys (`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`) | **Secret** | GitHub Actions secrets; Varun's laptop `.r2.env` |
| NASA Earthdata token | **Secret** | Varun's laptop `.edl_token` |
| USDA NASS API key | **Secret** | Varun's laptop `.nass_key` |
| Earthdata username/password (SMAP download) | **Secret** | Typed into a hidden prompt only; never stored |
| Tiger Cloud database credentials (retired) | **Secret** | Varun's laptop `tiger-cloud-db-28639-credentials.env` |

The data holds no personal information. It comes from public NASA, USDA and Drought Monitor sources and is summarised to county level.

## 2. Rules for everyone on the team

1. Never commit, paste, email, screenshot or send a key, token or password in chat. That includes AI chats.
2. Secrets go only in GitHub Actions secrets or in the gitignored files listed above. `.gitignore` blocks `*.env`, `*credentials*`, `.edl_token*`, `.nass_key*`, `*.pem`, `*.key`, `*.token` and screenshots.
3. The app needs **no credentials**. It only reads the public JSON link, so never put keys in app code.
4. Give each key the least power it needs. The R2 token is "Object Read & Write" on this one bucket only, with no account-wide access.
5. If a secret was ever pasted somewhere visible, treat it as leaked and replace it (section 6).
6. Only trusted teammates get write access to the repo. Turn on 2-factor authentication for GitHub and Cloudflare.

## 3. How the automation is protected

- **Least-privilege job token.** The weekly workflow can only push commits to this repo (`permissions: contents: write`).
- **Keys reach one step only.** `run_weekly.py` strips every `R2_*` variable before running the download and analysis steps, and passes the keys only to the upload step (`19_upload_cloudflare_r2.py`). Tested: the analysis steps see no R2 variables.
- **Pinned code.** `actions/checkout` is pinned to an exact commit, `uv` to 0.13.8, and every Python library to an exact version (pandas, numpy, scikit-learn, scipy, matplotlib, zipcodes, boto3, botocore). An upstream change can't silently alter what runs.
- **Safety checks before publishing.** If the data is stale, a district is missing, a district lacks exactly 3 rotations, weights don't total 100, the current-crop table is incomplete or the factor file is missing, nothing is uploaded and the app keeps the previous advice.
- **No accidental secret commits.** The workflow commits only `data/` and `reports/`, and refuses if a staged file name looks like a secret.
- **Safe triggers.** The workflow runs only on its weekly schedule or a manual click by someone with write access. It never runs code from pull requests or forks.
- **Encrypted downloads.** All downloads use HTTPS.
- **Secret handling in scripts.** Secrets are never printed. The SMAP script asks for the Earthdata password with a hidden prompt and never saves it.

## 4. Cloudflare R2 (the published file)

- The bucket `kansas-crop-advice` serves one public file through the r2.dev development link. The upload overwrites only that one key.
- CORS allows only GET and HEAD, from any site. That is fine for public read-only data.
- r2.dev links are rate-limited. A real launch should use a custom domain and Cloudflare's caching.

## 5. GitHub repo settings

Already on (checked 2026-11-15):
- Secret scanning.
- Push protection: GitHub blocks pushes that contain known key formats.

Recommended. Turn these on in Settings; only the owner can:
- **Dependabot alerts and security updates:** Settings → Code security.
- **Ruleset on `main`:** block force-pushes and branch deletion (Settings → Rules → Rulesets). Do not require pull requests, or the weekly bot can't push.

## 6. If a secret leaks (incident steps)

1. **Revoke it right away** where it was issued:
   - R2 token: Cloudflare → R2 → Manage API tokens.
   - NASA token: Earthdata Login → Generate Token.
   - NASS key: request a new key from the NASS Quick Stats API page.
2. Create a new one with the same minimal scope.
3. Update it in GitHub Actions secrets and/or the laptop file.
4. Run the workflow once to confirm it works.
5. Check the bucket and the live file for anything unexpected.
6. If it was committed to git, deleting the file is not enough, because it stays in history. Revoking the key is what makes it safe.

## 7. Checklist (before handoff, before the demo, then monthly)

- [ ] `git ls-files` shows no `.env`, token, key or credential files.
- [ ] The latest weekly workflow run succeeded, and the live link loads with recent `data_through`.
- [ ] Repo collaborators and Cloudflare/GitHub access are still only the people who need them.
- [ ] Retired services are shut down: delete the Tiger Cloud service, or at least run `DROP ROLE app_reader;`.
- [ ] No screenshots of consoles or keys are in shared folders.

## 8. Audit record

2026-11-15, by Claude (Anthropic AI):
- Full git history scanned for key, token, password and private-key patterns, and for secret file names: none found. The public r2.dev link is intentionally public.
- Changes made:
  - R2 keys isolated to the upload step.
  - `actions/checkout`, `uv`, boto3 and botocore pinned.
  - Unused `psycopg` dependency removed from the weekly run.
  - Workflow guard added against committing secret files.
  - Extra `.gitignore` patterns added.
  - Stale "database" wording fixed.
- Re-tested:
  - full offline run plus upload to a local fake S3: results identical, upload verified
  - analysis steps see no R2 variables
  - a missing key stops the upload with a clear message
- Laptop folder: the secret files are present locally only. The folder is not a git repo, and none of them are in GitHub. Two screenshots from setup (14:14 and 17:48) were not opened. If they show any console or key, move them out of the project folder.
