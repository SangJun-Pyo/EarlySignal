import duckdb
from es.ingest import load_tsv, normalize_complaints

def row(odino, kind="VOQ", product="V", comp="ENGINE", date="20180131"):
    fields = [""] * 51
    for i, value in {1:odino+comp,2:odino,4:" hyundai ",5:" sonata ",6:"2011",7:"N",9:"Y",10:"0",11:"0",12:comp,16:"20170101",17:date,20:'SMOKE "appeared"',21:kind,46:product}.items():
        fields[i-1] = value
    return "\t".join(fields)

def test_deduplicates_consumer_vehicle_rows_and_preserves_quotes(tmp_path):
    path = tmp_path / "rows.txt"
    path.write_text("\n".join([row("1"),row("1",comp="FUEL"),row("2",kind="DP"),row("3",product="T"),row("4",date="invalid")]))
    con = duckdb.connect()
    load_tsv(con,[path],"complaints_raw",51)
    normalize_complaints(con)
    values = con.execute("SELECT odino,grp,ldate,text,array_length(compdesc_list) FROM complaints ORDER BY odino").fetchall()
    assert len(values) == 2
    assert values[0][1] == "HYUNDAI|SONATA"
    assert str(values[0][2]) == "2018-01-31"
    assert values[0][3] == 'SMOKE "appeared"'
    assert values[0][4] == 2
    assert values[1][2] is None
    assert "vin" not in [x[0] for x in con.execute("DESCRIBE complaints").fetchall()]
