from typing import Iterable
import scrapy
from urllib.parse import urljoin
from scrapy.http import Request
from batdongsan.items import BatdongsanItem
from datetime import date, timedelta


class AlonhadatSpiderSpider(scrapy.Spider):
    name = "alonhadat_spider"
    allowed_domains = ["alonhadat.com.vn"]

    def __init__(self, min_page=-1, max_page=999999, province='ha-noi', jump_to_page=-1):
        super().__init__()
        self.min_page = int(min_page)
        self.max_page = int(max_page)
        self.province = province
        self.jump_to_page = int(jump_to_page)

    def _get_page_url(self, province, page_num):
        arg_map = {'province': province, 'page_num': page_num}
        first_page_link = 'https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/1/{province}.html'
        page_link = 'https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/1/{province}/trang--{page_num}.html'
        if page_num == 1:
            return first_page_link.format_map(arg_map)
        else:
            return page_link.format_map(arg_map)        

    def start_requests(self):
        start_url = 'https://alonhadat.com.vn/'
        yield scrapy.Request(url=start_url, callback=self.parse_home_page)

    def parse_home_page(self, response):

        # Discover real estate page for each province
        province_page_links = response.css('div.house-bottom-navigation a ::attr(href)').getall()

        for province_page_link in province_page_links:
            province = province_page_link.split('/')[-1].replace('.html', '')
            if province == self.province:
                province_full_page_link = urljoin('https://alonhadat.com.vn', province_page_link)
                yield scrapy.Request(url=province_full_page_link, callback=self.parse_province_page, meta={'province': province, 'page': 1})

    def parse_province_page(self, response):
        province = response.meta['province']
        page = response.meta['page']

        if self.jump_to_page > 1:
            dest_page_num = self.jump_to_page
            self.jump_to_page = -1
            yield scrapy.Request(url=self._get_page_url(province=province, page_num=dest_page_num), callback=self.parse_province_page, meta={'province': province, 'page': dest_page_num})
        else:
            if page >= self.min_page:
                # Discover page links for province 's real estate
                real_estates = response.css('div.content-items div.content-item')
                for real_estate in real_estates:
                    real_estate_link = real_estate.css('div.thumbnail a::attr(href)').get()
                    real_estate_link = urljoin('https://alonhadat.com.vn/', real_estate_link)
                    yield scrapy.Request(url=real_estate_link, callback=self.parse_real_estate_page, meta={'province': province})

            # Go to next page
            # next_page = response.css('div.page a:not([class])::attr(href)').get()
            page_links = response.css('div.page a::attr(href)').getall()
            current_page = response.css('div.page a.active ::attr(href)').get()
            current_page_idx = page_links.index(current_page)
            if current_page_idx >= len(page_links):
                next_page = None
            else:
                next_page = page_links[current_page_idx + 1]
            if next_page is not None and page < self.max_page:
                next_page = urljoin('https://alonhadat.com.vn/', next_page)
                yield scrapy.Request(url=next_page, callback=self.parse_province_page, meta={'province': province, 'page': page+1})

    def parse_real_estate_page(self, response):
        bds_item = BatdongsanItem()

        bds_item['title'] = response.css('h1::text').get()
        bds_item['description'] = response.css('div.detail.text-content::text').get()
        bds_item['price'] = response.css('span.price span.value::text').get().strip()
        bds_item['square'] = response.css('span.square span.value::text').get().strip()
        bds_item['address'] = {'full_address': None, 'province': None, 'district': None, 'ward': None}
        bds_item['address']['province'] = response.meta['province']
        bds_item['address']['full_address'] = response.css('div.address span.value::text').get().strip()

        post_date = response.css('span.date::text').get().replace('Ngày đăng: ', '')
        if post_date == 'Hôm nay':
            bds_item['post_date'] = date.today().strftime('%d/%m/%Y')
        elif post_date == 'Hôm qua':
            bds_item['post_date'] = (date.today()-timedelta(days=1)).strftime('%d/%m/%Y')
        else:
            bds_item['post_date'] = post_date

        contact_info = {}
        contact_info['name'] = response.css('div.contact-info div.name::text').get()
        contact_info['phone'] = response.css('div.contact-info div.fone a::text').getall()
        bds_item['contact_info'] = contact_info

        extra_infos = {}
        info_rows = response.css('div.infor table tr')
        for row in info_rows:
            num_cols = len(row.css('td'))
            for i in range(0, num_cols, 2):
                label = row.css('td')[i].css('::text').get()
                value = row.css('td')[i+1].css('::text').get()
                if value is None:
                    value = True
                elif value == '_' or value == '---':
                    value = None

                if label == 'Loại BDS':
                    bds_item['estate_type'] = value
                elif label == 'Mã tin':
                    bds_item['post_id'] = value
                else:
                    extra_infos[label] = value
        
        bds_item['extra_infos'] = extra_infos

        bds_item['link'] = response.url
        yield bds_item