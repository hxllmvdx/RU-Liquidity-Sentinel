from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
reserves_path = (BASE_DIR/ "../../../data/raw/cbr/reserves/required_reserves_table.xlsx").resolve()
ruonia_path = (BASE_DIR/ "../../../data/raw/cbr/ruonia/ruonia.xlsx").resolve()
output_path = (BASE_DIR/ "../../../data/processed/M1_dataset.csv").resolve()
df1 = pd.read_excel(reserves_path)
df1.drop(0, inplace=True)
df1.columns = df1.iloc[1]
df1 = df1.iloc[1:]
df1.reset_index(drop=True, inplace=True)
df1.rename(columns={
    df1.columns[0]: 'Период усреднения',
    df1.columns[1]: 'Фактические среднедневные остатки средств на корсчетах',
    df1.columns[2]: 'Обязательные резервы, подлежащие усреднению на корсчетах',
    df1.columns[3]: 'Обязательные резервы на счетах для их учета',
    df1.columns[4]: 'Количество кредитных организаций пользующихся правом усреднения обязательных резервов',
    df1.columns[5]: 'Количество действующих кредитных организаций',
    df1.columns[6]: 'Период усреднения обязательных резервов',
    df1.columns[7]: 'Число календарных дней в периоде усреднения обязательных резервов',
    df1.columns[8]: 'Отчетный период',
    df1.columns[9]: 'Период регулирования обязательных резервов'
}, inplace=True)
df1 = df1[~df1.iloc[:, 0].astype(str).str.match(r'^\d+\s')]
df1.reset_index(drop=True, inplace=True)
df2 = pd.read_excel(ruonia_path)
df = pd.concat([df1, df2], axis=1)
output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)
