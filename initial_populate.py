import os
import pandas as pd

# Check if motos_data.json exists, remove it if it does, then run the olxSpider crawler
if os.path.exists('motos_data_raw.json'):
    os.remove('motos_data_raw.json')
os.system('scrapy runspider OlxSpider.py -o motos_data_raw.json')


df = pd.read_json('motos_data_raw.json')
df = df[df['status_financeiro'] != 'Financiado']
df['listId'] = df['listId'].astype(str)
df['listId'] = df['listId'].str[:-2]
df['quilometragem'] = df['quilometragem'].apply(lambda x: str(x) if isinstance(x, float) else x).astype(str).str[:-2]
df['ano'] = df['ano'].astype(str).str[:-2]
df.drop_duplicates(subset=['listId'], inplace=True)
df = df[df['listId'] != 'n']
df.reset_index(drop=True, inplace=True)
df.to_json('motos_data.json', orient='records')