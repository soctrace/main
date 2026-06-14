from pathlib import Path
import pandas as pd


def read_csv_safe(path: str | Path, **kwargs) -> pd.DataFrame:
    path = Path(path)

    encodings_to_try = ["utf-8", "latin-1", "cp1252"]
    separators_to_try = [";", ","]

    last_error = None

    for enc in encodings_to_try:
        for sep in separators_to_try:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, **kwargs)

                # Si solo detecta una columna, probablemente el separador no era correcto
                if df.shape[1] == 1:
                    continue

                return df
            except Exception as e:
                last_error = e

    raise last_error