from typing import Iterable
import scrapy
from scrapy.http import Request
from batdongsan.items import BatdongsanItem


class BannhaSpiderSpider(scrapy.Spider):
    name = "bannha_spider"
    allowed_domains = ["bannha.net"]

    def __init__(self, min_page=-1, max_page=999999, province='ha-noi', jump_to_page=-1):
        super().__init__()
        self.min_page = int(min_page)
        self.max_page = int(max_page)
        self.province = province
        self.jump_to_page = int(jump_to_page)

    def _get_page_url(self, province, page_num):
        arg_map = {'province': province, 'page_num': page_num}
        first_page_link = 'https://bannha.net/mua-ban-nha-dat-{province}/'
        page_link = 'https://bannha.net/mua-ban-nha-{province}/page/{page_num}/'
        if page_num == 1:
            return first_page_link.format_map(arg_map)
        else:
            return page_link.format_map(arg_map)     

    def start_requests(self):
        start_url = 'https://bannha.net/'
        yield scrapy.Request(url=start_url, callback=self.parse_home_page)

    def parse_home_page(self, response):

        # Discover real estate page for each province
        province_page_links = response.css('.elementor-element-523070a').css('a.elementor-item::attr(href)').getall()

        for province_page_link in province_page_links:
            province = province_page_link.split('/')[-2].replace('mua-ban-nha-dat-', '')
            if province == self.province:
                province_full_page_link = province_page_link
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
                real_estates = response.css('main article')
                for real_estatel in real_estates:
                    real_estate_link = real_estatel.css('h3 a::attr(href)').get()
                    yield scrapy.Request(url=real_estate_link, callback=self.parse_real_estate_page, meta={'province': province})

            # Go to next page
            next_page = response.css('a.page-link[aria-label="Next"]::attr(href)').get()
            if next_page is not None and page < self.max_page:
                yield scrapy.Request(url=next_page, callback=self.parse_province_page, meta={'province': province, 'page': page+1})

    def parse_real_estate_page(self, response):
        bds_item = BatdongsanItem()

        bds_item['title'] = response.css('div.elementor-widget-heading h1::text').get()
        bds_item['description'] = '\n'.join(response.css('div.elementor-widget-theme-post-content div.elementor-widget-container p::text').getall()).strip()
        bds_item['price'] = response.css('div.elementor-widget-shortcode[data-id="88d1311"] div.elementor-shortcode div::text').getall()[0].strip()
        bds_item['square'] = response.css('div.elementor-widget-shortcode[data-id="88d1311"] div.elementor-shortcode div::text').getall()[1].strip()
        bds_item['estate_type'] = response.css('nav.rank-math-breadcrumb a::text')[1].get().strip()
        bds_item['address'] = {'full_address': None, 'province': None, 'district': None, 'ward': None}
        bds_item['address']['province'] = response.meta['province']
        bds_item['address']['full_address'] = response.css('div.elementor-widget-post-info[data-id="ee07c90"] span.elementor-icon-list-text::text').get().strip()
        bds_item['post_date'] = response.css('div.elementor-widget-shortcode[data-id="88d1311"] div.elementor-shortcode div::text').getall()[2].strip()

        contact_info = {}
        contact_info['name'] = response.css('.elementor-post-info__item--type-author::text').get().strip()
        contact_info['phone'] = [phone.strip() for phone in response.css('.elementor-repeater-item-372c6a1 span.elementor-icon-list-text::text').getall()]
        bds_item['contact_info'] = contact_info

        bds_item['link'] = response.url
        yield bds_item