"""
Step 7 - Load our Kansas data into a Tiger Cloud database (Tiger Data / TimescaleDB).
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Cite in References: Tiger Data (Tiger Cloud, TimescaleDB) and this AI-generated script.

Why a time-series database: every dataset here is "a value per place per day".
TimescaleDB stores that as a hypertable (a Postgres table split by time), so the
app team can ask things like "latest dryness for each district" with plain SQL.

Tables created (all safe to re-run; existing rows are updated, not duplicated):
  weather_daily     hypertable  - cleaned NASA POWER data   (data/power_daily_clean.csv)
  daily_anomalies   hypertable  - z-scores + percentiles    (data/power_anomalies.csv)
  climate_normals   table       - each district's normal    (data/power_normals.csv)
  latest_status     view        - newest day per district, for the app

SETUP (Varun does this once - Claude never sees the password):
  1. Sign up at Tiger Data / Tiger Cloud and create a free service.
  2. Copy the service's connection string (starts with postgres://...).
  3. Save it as the only line of C:\\SpaceApps2026\\.tiger_db_url  (Notepad,
     Save as type "All files", same as the token file).
  4. In WSL:  python3 -m pip install --user "psycopg[binary]"
Run in WSL:  cd /mnt/c/SpaceApps2026 && python3 scripts/07_load_tiger_cloud.py
"""
import csv, os, sys
try:
    import psycopg
except ImportError:
    sys.exit('Install the driver first:  python3 -m pip install --user "psycopg[binary]"')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def find_url():
    """Connection string from (1) TIGER_DB_URL env var, (2) .tiger_db_url file, or
    (3) the tiger-cloud-*-credentials.env file downloaded from the Tiger console.
    The password is read only inside this script; it is never printed."""
    if os.environ.get("TIGER_DB_URL"):
        return os.environ["TIGER_DB_URL"]
    p = os.path.join(ROOT, ".tiger_db_url")
    if os.path.exists(p):
        return open(p, encoding="utf-8-sig").read().strip()
    envs = sorted(f for f in os.listdir(ROOT) if f.startswith("tiger-cloud") and f.endswith(".env"))
    if envs:
        kv = {}
        for line in open(os.path.join(ROOT, envs[-1]), encoding="utf-8-sig"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                kv[k.strip().upper()] = v.strip().strip('"').strip("'")
        for v in kv.values():                       # a full URL, if the file has one
            if v.startswith(("postgres://", "postgresql://")):
                return v
        need = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
        if all(k in kv for k in need):
            return (f"host={kv['PGHOST']} port={kv['PGPORT']} dbname={kv['PGDATABASE']} "
                    f"user={kv['PGUSER']} password={kv['PGPASSWORD']} sslmode=require")
        sys.exit(f"Found {envs[-1]} but could not read it. Its variable NAMES are: "
                 + ", ".join(sorted(kv)) + "  (send Claude these names only, not the values)")
    sys.exit("No connection info: put tiger-cloud-...-credentials.env in C:\\SpaceApps2026")

url = find_url()

TEXT_COLS = {"region", "district", "county", "model_used", "variable", "crop", "fao_need_mm", "alert", "basis", "rotation", "k_state_region", "note", "double_crop_ok"}
INT_COLS = {"point", "doy", "n", "fips", "gwetroot_flag"}
DATE_COLS = {"week", "issued", "forecast_for_week"}

def coltype(c, timecol=None):
    if c == timecol: return ("timestamptz" if c == "time" else "date") + " NOT NULL"
    if c in TEXT_COLS: return "text"
    if c in INT_COLS: return "integer"
    if c in DATE_COLS: return "date"
    if c == "time": return "timestamptz"
    return "double precision"

def load(cur, csv_name, table, key, hyper, timecol="time", replace=False):
    path = os.path.join(ROOT, "data", csv_name)
    with open(path) as f:
        reader = csv.reader(f)
        header = [h.lower() for h in next(reader)]
        header = ["time" if h == "date" else h for h in header]
        rows = list(reader)
    if replace:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    cols = ", ".join(f'"{c}" {coltype(c, timecol)}' for c in header)
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table} ({cols}, UNIQUE ({", ".join(key)}))')
    for c in header:   # columns added to the CSV after the table was first created
        cur.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{c}" {coltype(c, timecol).replace(" NOT NULL","")}')
    if hyper:
        cur.execute(f"SELECT create_hypertable('{table}', '{timecol}', if_not_exists => TRUE, migrate_data => TRUE)")
    cur.execute(f"CREATE TEMP TABLE stage (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
    qcols = ", ".join(f'"{c}"' for c in header)
    with cur.copy(f"COPY stage ({qcols}) FROM STDIN") as cp:
        for r in rows:
            cp.write_row([None if v in ("", "nan", "NaN") else
                          (str(int(float(v))) if c in INT_COLS else v) for c, v in zip(header, r)])
    upd = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in header if c not in key)
    cur.execute(f"INSERT INTO {table} ({qcols}) SELECT {qcols} FROM stage "
                f"ON CONFLICT ({', '.join(key)}) DO UPDATE SET {upd}")
    cur.execute(f"SELECT count(*) FROM {table}")
    print(f"{table}: {len(rows):,} rows in file, {cur.fetchone()[0]:,} rows in database")

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        load(cur, "power_daily_clean.csv", "weather_daily", ["region", "time"], True)
        conn.commit()
        load(cur, "power_anomalies.csv", "daily_anomalies", ["region", "time"], True)
        conn.commit()
        load(cur, "power_normals.csv", "climate_normals", ["region", "doy", "variable"], False)
        conn.commit()
        load(cur, "usdm_district_weekly.csv", "usdm_district_weekly", ["district", "week"], True, timecol="week")
        conn.commit()
        load(cur, "model_predictions.csv", "model_backtest", ["region", "week"], True, timecol="week", replace=True)
        conn.commit()
        load(cur, "county_district_map.csv", "county_district_map", ["fips"], False, replace=True)
        conn.commit()
        load(cur, "live_forecast.csv", "live_forecast", ["region"], False, replace=True)
        conn.commit()
        load(cur, "crop_ranking.csv", "crop_ranking", ["region", "crop"], False, replace=True)
        conn.commit()
        load(cur, "rotation_ranking.csv", "rotation_ranking", ["region", "rotation"], False, replace=True)
        conn.commit()
        cur.execute("DROP VIEW IF EXISTS app_rotation_advice")
        cur.execute("DROP VIEW IF EXISTS app_crop_advice")
        cur.execute("DROP VIEW IF EXISTS app_drought_risk")
        cur.execute("""
            CREATE VIEW app_drought_risk AS          -- what the app reads: one row per county
            SELECT c.fips, c.county, c.district, c.lat, c.lon,
                   f.issued       AS data_through,
                   f.forecast_for_week AS forecast_date,
                   round(f.p_logistic::numeric, 3) AS drought_probability,
                   CASE WHEN f.p_logistic >= 0.5 THEN 'warning'
                        WHEN f.p_logistic >= 0.3 THEN 'watch'
                        ELSE 'normal' END AS alert_level,
                   f.usdm_now     AS district_pct_in_drought_now,
                   f.model_used
            FROM county_district_map c JOIN live_forecast f ON f.region = c.district""")
        conn.commit()
        cur.execute("""
            CREATE VIEW app_crop_advice AS           -- what the app reads: crop order per county
            SELECT c.fips, c.county, c.district, k.crop,
                   k.recommended_rank::int AS rank, k.basis,
                   k.yield_index_normal, k.yield_index_dry_year,
                   k.season_rain_normal_mm, k.season_rain_dry_year_mm, k.fao_need_mm, k.ky,
                   k.alert, k.drought_probability_now
            FROM county_district_map c JOIN crop_ranking k ON k.region = c.district
            WHERE k.crop <> 'winter wheat'""")
        conn.commit()
        cur.execute("""
            CREATE VIEW app_rotation_advice AS       -- what the app reads: top 3 rotations per county
            SELECT c.fips, c.county, c.district, k.k_state_region,
                   k.recommended_rank::int AS rank, k.rotation, k.weight_pct, k.crops_per_year,
                   k.score_normal, k.score_dry_year, k.basis, k.note,
                   k.alert, k.drought_probability_now, k.rootzone_pct_now,
                   c.lat, c.lon, f.issued AS data_through
            FROM county_district_map c JOIN rotation_ranking k ON k.region = c.district
            JOIN live_forecast f ON f.region = c.district
            WHERE k.recommended_rank <= 3""")
        # Re-grant the app's read-only login (recreating the view drops old grants).
        cur.execute("""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_reader') THEN
                GRANT SELECT ON app_rotation_advice TO app_reader;
            END IF; END $$;""")
        conn.commit()
        cur.execute("DROP VIEW IF EXISTS latest_status")   # columns changed -> recreate
        cur.execute("""
            CREATE VIEW latest_status AS
            SELECT DISTINCT ON (region)
                   region, lat, lon, time AS as_of,
                   gwetroot, gwetroot_pct, gwetroot_flag, rain_30d, rain_30d_pct, rain_90d, rain_90d_pct, t2m_max_z
            FROM daily_anomalies
            ORDER BY region, time DESC""")
        conn.commit()
        cur.execute("SELECT region, as_of::date, round(gwetroot_pct::numeric,0), "
                    "gwetroot_flag::int, round(rain_90d_pct::numeric,0) FROM latest_status ORDER BY region")
        print("\nlatest_status (region, date, root-zone wetness pct, suspect flag, 90-day rain pct):")
        for r in cur.fetchall():
            print("  ", *r)
    with conn.cursor() as cur:
        cur.execute("SELECT alert_level, count(*) FROM app_drought_risk GROUP BY 1 ORDER BY 1")
        print("\napp_drought_risk (counties per alert level):", dict(cur.fetchall()))
        cur.execute("SELECT count(*), count(DISTINCT fips) FROM app_crop_advice")
        print("app_crop_advice (rows, counties):", cur.fetchone())
        cur.execute("SELECT count(*), count(DISTINCT fips) FROM app_rotation_advice")
        print("app_rotation_advice (rows, counties):", cur.fetchone())
print("\nDone.")
