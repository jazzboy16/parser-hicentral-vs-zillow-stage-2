# -*- coding: utf-8 -*-
import json
import random
import time

import requests
from bs4 import BeautifulSoup, Tag


# Режим отладки.
# Если включен (True), то будет собираться только одна страница результатов и одно объявление.
# Если выключен (False), то будет собираться вся информация.
DEBUG = True


def make_delay(a=1.0, b=3.0):
    """
    Функция задержки, для снижения нагрузки на обрабатываемый сайт.
    Выполнение программы задерживается на случайное значение от a до b.

    :param a:       левое граничное значение.
    :param b:       правое граничное значение.
    :return:
    """
    delay = random.uniform(a, b)
    print('Задержка: {:.2f} сек.'.format(delay))
    time.sleep(delay)


def parse_hicentral(dump_filename='dump_hicentral_ads.json'):
    """
    Парсер сайта propertysearch.hicentral.com
    Обходит все страницы по очереди с объявлениями,
    затем обходит все объявления и забирает с каждого следующие значения (в скобках указан соответствующий ключ):

    - адрес (address);
    - цена (price);
    - тип недвижимости (property_type);
    - ссылка на объявление (url);
    - List Date (list_date).

    :param dump_filename:       имя файла, куда сохранятся словари объявлений.
    :return:                    список всех объявлений, каждое объявление - словарь.
    """
    domain = 'https://propertysearch.hicentral.com'
    ad_urls = []
    ads = []

    url = '{}/HBR/ForSale/?/Results/HotSheet//1//'.format(domain)

    page_n = 1
    while True:
        make_delay()
        print('Парсинг страницы: {}'.format(page_n))

        html = requests.get(url).text
        soup = BeautifulSoup(html, features='html.parser')

        # Собираем ссылки на объявления.
        anchors = soup.select('div.P-Results1 > span > a')
        ad_urls.extend(
            ['{}/HBR/ForSale/{}'.format(domain, a.attrs['href']) for a in anchors]
        )

        if DEBUG:
            break

        # Если есть кнопка «next», то переходим к следующей странице.
        next_btn = soup.find('a', {'id': 'ctl00_main_ctl00_haNextTop'})
        if next_btn:
            url = '{}{}'.format(domain, next_btn.attrs['href'])
            page_n += 1
        # Если нет, то завершаем цикл.
        else:
            break

    print('Парсинг страниц с объявлениями завершен, всего ссылок: {}'.format(len(ad_urls)))

    print('Начинаем парсинг объявлений.')
    for url in ad_urls:
        make_delay()
        print('Парсинг объявления: {}'.format(url))

        # Получаем HTML страницы объявления и...
        html = requests.get(url).content
        # подготавливаем его к парсингу с помощью библиотеки beautifulsoup4
        soup = BeautifulSoup(html, features='html.parser')

        # Адрес.
        address = soup.h2.encode_contents().decode('utf-8').replace('<br/>', ' ')

        # Цена.
        price = soup.select('div.price > span.P-Active')
        price = price[0].text if len(price) else None

        # Ищем тип недвижимости и List Date среди всех строк всех блоков div.column-block > div.column2.
        # Это значение будет хранить левую колонку в таблице значений. Например:
        # "Property Type:", "Bedrooms:" или "Parking Stalls:".
        # Чтобы понять очередное значение из правой колонки к чему относится. Нам тут нужно два значения:
        # Тип недвижимости и List Date.
        # Соответственно, эта переменная «Тип недвижимости»
        property_type = None
        # А эта переменная «List Date»
        list_date = None
        previous_header = None
        # Собираем все таблицы/блоки (их несколько)
        for elm in soup.select('div#content > div.column-block > div.column2 > dl'):
            # В них собираем только теги dt, dd. Порядок сохраняется.
            # dt - это название, dd - само значение.
            tags = [t for t in elm if type(t) is Tag and t.name in ('dt', 'dd',)]
            # Проходим по очереди по ячейкам: заголовок, значение, заголовок, значение и тд.
            for tag in tags:
                # Заголовок - тег dt.
                if tag.name == 'dt':
                    previous_header = tag.text
                # Если это тег dd (значение).
                elif previous_header == 'Property Type:':
                    # Если это значение «Тип недвижимости»
                    property_type = tag.text
                elif previous_header == 'List Date:':
                    # Или если это значение «List Date»
                    list_date = tag.text
            if property_type is not None and list_date is not None:
                break

        # Добавляем словарь к общему списку объявлений.
        ads.append({
            'address': address,
            'price': price,
            'property_type': property_type,
            'url': url,
            'list_date': list_date,
        })

        if DEBUG:
            break

    # Сохраняем объявления в файл.
    with open(dump_filename, 'w') as f:
        json.dump(ads, f, ensure_ascii=False, indent=2)
    print('Объявления сохранены в файл: {}'.format(dump_filename))

    return ad_urls


def main():
    parse_hicentral()


if __name__ == '__main__':
    main()
