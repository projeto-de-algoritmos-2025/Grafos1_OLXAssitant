import scrapy
import json

class OlxMotosSpider(scrapy.Spider):
    estados = ['df', 'go', 'ms', 'mt', 'to', 'ac', 'am', 'ap', 'ba', 'ce', 'es', 'ma', 'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'ro', 'rr', 'rs', 'sc', 'se', 'sp']
    base_url = 'https://www.olx.com.br/autos-e-pecas/motos/estado-'
    name = 'olx_motos'
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 10,
        'AUTOTHROTTLE_MAX_DELAY': 60,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': True,
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 5,
        'COOKIES_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        },
    }
    
    def start_requests(self):
        for estado in self.estados:
            for page in range(1, 2):
                print(f"Requesting page {page}")
                yield scrapy.Request(
                    f'{self.base_url}{estado}?o={page}',
                    callback=self.parse,
                    headers={
                        'Referer': self.base_url if page > 1 else None
                    }
                )

    def parse(self, response, **kwargs):
        print(f"Parsing page: {response.url}")
        html = json.loads(response.xpath('//script[@id="__NEXT_DATA__"]/text()').get())
        anuncios = html.get('props', {}).get('pageProps', {}).get('ads', [])
        print(f"Found {len(anuncios) if anuncios else 0} ads")
        
        for anuncio in anuncios:
            print(f"Processing ad: {anuncio.get('title')}")
            yield {
                'listId': anuncio.get('listId'),
                'title': anuncio.get('title'),
                'price': anuncio.get('price'),
                'estado': anuncio.get('locationDetails', {}).get('uf'),
                'url': anuncio.get('url'),
                'cilindrada': next((prop['value'] for prop in anuncio.get('properties', []) if prop['name'] == 'cubiccms'), None),
                'marca': next((prop['value'] for prop in anuncio.get('properties', []) if prop['name'] == 'vehicle_brand'), None),
                'modelo': next((prop['value'] for prop in anuncio.get('properties', []) if prop['name'] == 'vehicle_model'), None),
                'ano': next((prop['value'] for prop in anuncio.get('properties', []) if prop['name'] == 'regdate'), None),
                'quilometragem': next((prop['value'] for prop in anuncio.get('properties', []) if prop['name'] == 'mileage'), None),
                'status_financeiro': next((prop['value'] for prop in anuncio.get('properties', []) if prop['name'] == 'indexed_financial_status'), None),
                'locations': anuncio.get('location'),
                'imagens': anuncio.get('images'),
            }
