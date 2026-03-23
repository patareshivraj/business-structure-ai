import requests
from bs4 import BeautifulSoup


def scrape_company(company):

    try:

        url = f"https://www.google.com/search?q={company}+official+website"

        headers = {"User-Agent": "Mozilla/5.0"}

        res = requests.get(url, headers=headers)

        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text()

        return text[:5000]

    except:
        return ""