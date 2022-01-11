import requests
import re
import json
from os import mkdir
from os.path import dirname, exists, join
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/96.0.4664.45 Safari/537.36 '
}


class PizzburgParser:
    """
    Парсер для сайта Пермской пиццерии pizzapizzburg.ru
    """

    MENU_URL = 'https://pizzapizzburg.ru/pitstsa/'
    DATA_PATH = join(dirname(__file__), 'data', 'pizzapizzburg')
    MENU_PATH = join(DATA_PATH, 'menu.json')
    HTML_PATH = join(DATA_PATH, 'menu_page.html')

    def __init__(self, reload_from_site=True):
        self._menu = PizzburgParser._reload_menu(reload_from_site)

    @property
    def menu(self):
        return self._menu

    @staticmethod
    def _reload_menu(need_load=False):
        if need_load or not exists(PizzburgParser.MENU_PATH):
            r = requests.get(PizzburgParser.MENU_URL, headers=headers)
            with open(PizzburgParser.HTML_PATH, 'w', encoding='utf-8') as menu_file:
                menu_page = r.text
                menu_file.write(r.text)
        else:
            with open(PizzburgParser.HTML_PATH, 'r', encoding='utf-8') as menu_file:
                menu_page = menu_file.read()
        soup = BeautifulSoup(menu_page, 'lxml')
        week_pizza = None
        week_pizza_prices = None
        pizzas = []
        items = soup.find_all('div', class_='shk-item')
        for x in items:
            title = x.find('div', class_='product-unit__title').text.strip()
            info = x.find('div', class_='product-unit__info').text.strip()
            variants = x.find_all('div', class_='radio_param')
            dia_pattern = re.compile(r'(\d+)\s+см')
            h_pattern = re.compile(r'(пышное|тонкое)\s+тесто')
            prices = []
            for y in variants:
                v_name = y.find('input', {'name': 'name'}).get('value')
                prices.append({
                    'dia': int(re.search(dia_pattern, v_name).groups()[0]),
                    'h': re.search(h_pattern, v_name).groups()[0],
                    'price': float(y.find('input', {'name': 'price'}).get('value'))
                })
            if title.lower() == 'пицца недели':
                week_pizza_prices = prices
                continue
            hot_level = 0
            hot_unit = x.find('div', class_='product-unit__hot')
            if hot_unit is not None:
                hot_classes = hot_unit.attrs.get('class')
                hot_classes.remove('product-unit__hot')
                hot_level = int(hot_classes[0].replace('product-unit__hot_', ''))
            hot_suffix = '\U0001F336' * hot_level
            title = (title.replace('Пицца', ' ').strip() + ' ' + hot_suffix).strip()
            pizza_item = {'title': title, 'info': info, 'hot': hot_level, 'variants': prices}
            if x.find('div', class_='product-unit__status_sale') is not None:
                week_pizza = pizza_item
            pizzas.append(pizza_item)
        # обрабатываем пиццу недели >>>
        if week_pizza is not None and week_pizza_prices is not None:
            prices = week_pizza.get('variants')
            for wpp in week_pizza_prices:
                for p in prices:
                    if wpp.get('dia') == p.get('dia') and wpp.get('h') == p.get('h'):
                        p['price'] = wpp.get('price')
        # обрабатываем пиццу недели <<<
        if not exists(PizzburgParser.DATA_PATH):
            mkdir(PizzburgParser.DATA_PATH)
        with open(PizzburgParser.MENU_PATH, 'w', encoding='utf-8') as menu_file:
            json.dump(pizzas, menu_file, indent=4, ensure_ascii=False)
        return pizzas


if __name__ == '__main__':
    pp = PizzburgParser(reload_from_site=True)
    print(pp.menu)
