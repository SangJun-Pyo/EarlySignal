from dataclasses import dataclass
from pathlib import Path

CATEGORIES = ("fire_thermal", "electrical_failure", "loss_of_power", "engine_stall", "engine_failure", "airbag", "brakes", "steering", "seat_belt", "fuel_leak", "transmission", "lighting", "suspension", "structure_body", "tires_wheels", "other")
CONSUMER_TYPES = ("IVOQ", "VOQ", "EVOQ", "MIVQ", "MAVQ", "MVOQ", "SVOQ", "LETR", "CAG", "CON", "INS")
DEMO_GROUPS = ("HYUNDAI|SANTA FE", "HYUNDAI|SANTA FE SPORT", "HYUNDAI|SONATA", "HYUNDAI|SONATA HYBRID", "KIA|OPTIMA", "KIA|OPTIMA HYBRID", "KIA|SORENTO", "KIA|SOUL", "KIA|SOUL EV")

@dataclass(frozen=True)
class Config:
    root: Path = Path(__file__).resolve().parents[2]
    db_path: Path | None = None
    cases_path: Path | None = None
    raw_path: Path | None = None
    baseline_months: int = 12
    minimum_history: int = 6
    baseline_floor: float = 0.5
    alpha: float = 0.001
    minimum_count: int = 3

    @property
    def database(self):
        return self.db_path or self.root / "data" / "earlysignal.duckdb"

    @property
    def cases(self):
        return self.cases_path or self.root / "data" / "cases_pool.yaml"

    @property
    def raw(self):
        return self.raw_path or self.root / "data" / "raw"
