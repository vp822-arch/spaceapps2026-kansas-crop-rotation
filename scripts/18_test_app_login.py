"""
18_test_app_login.py - prove the app developer's read-only login works, exactly as he will use it.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Logs in as app_reader (password typed at the prompt, hidden, never saved or printed) to the
same Tiger Cloud host/port/database as the admin .env file, then checks:
  1. app_rotation_advice: 315 rows, 105 counties, 3 rotations each, weights total 100, has data_through
  2. app_reader can NOT read the raw tables (weather_daily) - read-only really means read-only
Run in WSL:  cd /mnt/c/SpaceApps2026 && uv run --with "psycopg[binary]" python scripts/18_test_app_login.py
"""
import getpass, glob, os, sys
import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = {}
envs = sorted(glob.glob(os.path.join(ROOT, "tiger-cloud-*.env")))
if envs:                                    # host/port/db only; the admin user and password are ignored
    for line in open(envs[0], encoding="utf-8-sig"):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
host = os.environ.get("PGHOST") or cfg.get("PGHOST")
port = os.environ.get("PGPORT") or cfg.get("PGPORT", "5432")
db = os.environ.get("PGDATABASE") or cfg.get("PGDATABASE", "tsdb")
if not host:
    sys.exit("Could not find the database host (tiger-cloud-*.env file or PGHOST).")
sslmode = os.environ.get("PGSSLMODE", "require")
pw = getpass.getpass("app_reader password (hidden): ")

ok = True
with psycopg.connect(host=host, port=port, dbname=db, user="app_reader", password=pw,
                     sslmode=sslmode, connect_timeout=15) as conn:
    print("1) logged in as app_reader: OK")
    rows, counties, bad3, bad100, dt = conn.execute("""
        WITH c AS (SELECT fips, count(*) n, sum(weight_pct) w FROM app_rotation_advice GROUP BY fips)
        SELECT (SELECT count(*) FROM app_rotation_advice), (SELECT count(*) FROM c),
               (SELECT count(*) FROM c WHERE n <> 3), (SELECT count(*) FROM c WHERE round(w) <> 100),
               (SELECT max(data_through) FROM app_rotation_advice)""").fetchone()
    good = rows == 315 and counties == 105 and bad3 == 0 and bad100 == 0 and dt is not None
    ok &= good
    print(f"2) app_rotation_advice: {rows} rows, {counties} counties, data through {dt}, "
          f"counties without 3 rotations: {bad3}, weights not 100: {bad100} -> {'OK' if good else 'PROBLEM'}")
    sample = conn.execute("SELECT rank, rotation, weight_pct FROM app_rotation_advice "
                          "WHERE fips = 20173 ORDER BY rank").fetchall()
    print("   Sedgwick County:", [(r, n, float(w)) for r, n, w in sample])
    try:
        conn.execute("SELECT 1 FROM weather_daily LIMIT 1")
        ok = False
        print("3) app_reader CAN read raw tables -> PROBLEM (should be read-only to the advice view)")
    except psycopg.errors.InsufficientPrivilege:
        conn.rollback()
        print("3) app_reader cannot read raw tables: OK")
print("\nALL CHECKS PASSED - the developer's login works." if ok else "\nSOME CHECKS FAILED - see above.")
sys.exit(0 if ok else 1)
