"""CLI deliberately imports each step only when invoked."""
import argparse
import os
from dotenv import load_dotenv
import importlib
import json
from pathlib import Path
import duckdb
from .config import Config

COMMANDS = {"ingest": "ingest", "scope": "scope", "label-kw": "label_kw", "aggregate": "aggregate", "detect": "detect", "backtest": "backtest", "export": "export", "import-llm": "import_llm"}

def main(argv=None):
    load_dotenv(Config().root / ".env")
    parser = argparse.ArgumentParser(prog="earlysignal")
    parser.add_argument("--root", type=Path, default=Path(os.getenv("ES_ROOT", str(Config().root))))
    parser.add_argument("--db", type=Path, default=Path(os.environ["ES_DB"]) if os.getenv("ES_DB") else None)
    parser.add_argument("--raw-dir", type=Path, default=Path(os.environ["ES_RAW_DIR"]) if os.getenv("ES_RAW_DIR") else None)
    parser.add_argument("--cases", type=Path, default=Path(os.environ["ES_CASES"]) if os.getenv("ES_CASES") else None)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        command = sub.add_parser(name)
        if name in {"aggregate", "detect", "backtest", "export"}:
            command.add_argument("--method", choices=["kw", "llm"], default="kw")
        if name == "import-llm":
            command.add_argument("--model")
        if name == "export":
            command.add_argument("--output", type=Path)
        if name == "backtest":
            command.add_argument("--verify-lookahead", action="store_true")
        if name == "aggregate":
            command.add_argument("--as-of")
        if name == "ingest":
            command.add_argument("--download", action="store_true")
    label = sub.add_parser("label-llm")
    label.add_argument("--limit", type=int, default=50)
    label.add_argument("--concurrency", type=int, default=12)
    label.add_argument("--max-attempts", type=int, default=3)
    label.add_argument("--max-new-rows", type=int)
    label.add_argument("--quote-selection-fallback", action="store_true")
    brief = sub.add_parser("briefs")
    brief.add_argument("--console", type=Path)
    brief.add_argument("--limit", type=int, default=1)
    brief.add_argument("--model")
    sub.add_parser("download")
    args = parser.parse_args(argv)
    config = Config(root=args.root.resolve(), db_path=args.db, raw_path=args.raw_dir, cases_path=args.cases)
    config.database.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "label-llm":
        from .label_llm import run_label_llm
        result = run_label_llm(config,args.limit,args.concurrency,
            max_attempts=args.max_attempts, max_new_rows=args.max_new_rows,
            quote_selection_fallback=args.quote_selection_fallback)
        print(json.dumps(result,ensure_ascii=False,default=str,indent=2))
        return
    if args.command == "briefs":
        from .brief import run_briefs
        result = run_briefs(config, console_path=args.console, limit=args.limit, model=args.model)
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return
    if args.command == "download":
        from .ingest import download
        print(json.dumps(download(config),indent=2))
        return
    module = importlib.import_module("es." + COMMANDS[args.command])
    with duckdb.connect(str(config.database)) as con:
        result = module.run(con, config, args)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))

if __name__ == "__main__":
    main()
