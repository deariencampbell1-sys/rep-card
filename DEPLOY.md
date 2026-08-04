# rep-card — sales rep card + VCF service

Live path: `/opt/rhobear/rep-card` on rhobear-vps (root user).
Serves: rep cards behind the `sales.rhobear.ai` Caddy block, on `127.0.0.1:8002`.
Unit: `rhobear-repcard.service`.
Runs: `.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8002 --workers 1`.
Env (from the unit, on the box): `REPCARD_DSN`, `REPCARD_BASE`. No secrets in source.

## Deploy
```bash
ssh rhobear-vps 'cd /opt/rhobear/rep-card && git pull && systemctl restart rhobear-repcard'
```
