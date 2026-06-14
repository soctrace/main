import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql:///mijas")

df = pd.read_sql("SELECT current_database() AS db, current_user AS user", engine)
print(df)


