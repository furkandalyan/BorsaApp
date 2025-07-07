# analiz/utils/update_hisse_listesi.py

import requests
from bs4 import BeautifulSoup
import json
import os

def hisse_listesini_cek():
    url = "https://borsa.doviz.com/hisseler"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    hisseler = []

    rows = soup.select('table tbody tr')
    for row in rows:
        kod = row.select_one('a').text.strip()
        ad = row.select_one('td:nth-child(2)').text.strip()

        hisseler.append({
            "short": kod,
            "full": f"{kod}.IS",
            "name": ad
        })

    path = os.path.join(os.path.dirname(__file__), 'hisseler.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(hisseler, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(hisseler)} hisse başarıyla kaydedildi → hisseler.json")

if __name__ == "__main__":
    hisse_listesini_cek()
