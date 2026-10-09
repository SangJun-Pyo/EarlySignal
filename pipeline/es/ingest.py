"""Load NHTSA headerless TSVs without interpreting narrative quote marks."""
from pathlib import Path
from urllib.request import urlretrieve
import zipfile
from .config import CONSUMER_TYPES

COMPLAINT_ZIPS = tuple(f"COMPLAINTS_RECEIVED_{period}.zip" for period in ("2010-2014", "2015-2019", "2020-2024"))
INV_ZIP = "FLAT_INV.zip"

def extract(zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        members = [m for m in archive.infolist() if m.filename.lower().endswith(".txt")]
        if len(members) != 1:
            raise ValueError(f"Expected one TSV in {zip_path.name}")
        member = members[0]
        destination = zip_path.parent / Path(member.filename).name
        if not destination.exists() or destination.stat().st_size != member.file_size:
            with archive.open(member) as src, destination.open("wb") as dst:
                import shutil
                shutil.copyfileobj(src, dst)
        return destination

def load_tsv(con, paths, table, count):
    columns = ",".join(f"'c{i:02d}':'VARCHAR'" for i in range(1, count + 1))
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv(?, delim='\\t', header=false, quote='', escape='', columns={{{columns}}}, ignore_errors=true, null_padding=false, max_line_size=10000000)", [[str(p) for p in paths]])

def normalize_complaints(con):
    allowed = ",".join(f"'{value}'" for value in CONSUMER_TYPES)
    # Only these explicit fields can enter downstream complaint tables.
    con.execute(f"""CREATE OR REPLACE TABLE complaints AS
    WITH filtered AS (
        SELECT *, row_number() OVER(PARTITION BY trim(c02) ORDER BY c01) AS rn,
            list(DISTINCT c12) OVER(PARTITION BY trim(c02)) AS compdesc_list
        FROM complaints_raw
        WHERE upper(trim(c21)) IN ({allowed}) AND upper(trim(c46))='V'
            AND nullif(trim(c02),'') IS NOT NULL
    ), normalized AS (
        SELECT trim(c02) AS odino, upper(trim(c04)) AS make, upper(trim(c05)) AS model,
            upper(trim(c06)) AS year,
            try_strptime(trim(c17), '%Y%m%d')::DATE AS ldate,
            try_strptime(trim(c16), '%Y%m%d')::DATE AS datea,
            upper(trim(c07))='Y' AS crash, upper(trim(c09))='Y' AS fire,
            coalesce(try_cast(c10 AS INTEGER),0) AS injured,
            coalesce(try_cast(c11 AS INTEGER),0) AS deaths,
            coalesce(c20,'') AS text, upper(trim(c21)) AS cmpl_type, compdesc_list
        FROM filtered WHERE rn=1
    ) SELECT *, make || '|' || model AS grp, date_trunc('month',ldate)::DATE AS month FROM normalized""")

def download(config):
    config.raw.mkdir(parents=True, exist_ok=True)
    downloaded=[]
    for name in (*COMPLAINT_ZIPS,INV_ZIP):
        path=config.raw/name
        if not path.exists():
            folder="inv" if name==INV_ZIP else "cmpl"
            temporary=path.with_suffix(".zip.part")
            urlretrieve(f"https://static.nhtsa.gov/odi/ffdd/{folder}/{name}",temporary)
            temporary.replace(path)
            downloaded.append(name)
    return {"downloaded":downloaded,"present":list((*COMPLAINT_ZIPS,INV_ZIP))}

def run(con, config, args=None):
    config.raw.mkdir(parents=True, exist_ok=True)
    for name in (*COMPLAINT_ZIPS, INV_ZIP):
        path = config.raw / name
        if not path.exists():
            if not getattr(args, "download", False):
                raise FileNotFoundError(f"Missing {name}; use ingest --download")
            folder = "inv" if name == INV_ZIP else "cmpl"
            urlretrieve(f"https://static.nhtsa.gov/odi/ffdd/{folder}/{name}", path)
    load_tsv(con, [extract(config.raw / p) for p in COMPLAINT_ZIPS], "complaints_raw", 51)
    normalize_complaints(con)
    load_tsv(con, [extract(config.raw / INV_ZIP)], "investigations_raw", 11)
    con.execute("""CREATE OR REPLACE TABLE investigations AS SELECT
        upper(trim(c01)) AS action_no, upper(trim(c02)) AS make,
        upper(trim(c03)) AS model, trim(c04) AS year, c05 AS compname,
        c06 AS mfr_name, try_strptime(c07,'%Y%m%d')::DATE AS odate,
        try_strptime(c08,'%Y%m%d')::DATE AS cdate,
        c09 AS campno, c10 AS subject, c11 AS summary FROM investigations_raw""")
    raw = con.execute("SELECT count(*) FROM complaints_raw").fetchone()[0]
    count, failures = con.execute("SELECT count(*), count(*) FILTER(WHERE ldate IS NULL) FROM complaints").fetchone()
    inv, unique_inv = con.execute("SELECT count(*),count(DISTINCT action_no) FROM investigations").fetchone()
    samples = con.execute("SELECT odino,grp,ldate FROM complaints ORDER BY odino LIMIT 5").fetchall()
    return {"raw_rows": raw, "consumer_unique": count, "ldate_failures": failures,
            "investigation_rows": inv, "investigation_unique": unique_inv,
            "safe_samples": samples}
