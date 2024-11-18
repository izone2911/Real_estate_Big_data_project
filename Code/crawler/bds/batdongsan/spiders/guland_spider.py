from typing import Iterable
from urllib.parse import urljoin
from datetime import datetime, timedelta
import scrapy
from scrapy.http import Request
from scrapy_playwright.page import PageMethod
from batdongsan.items import BatdongsanItem

click_show_more_script = """
const button = document.getElementById('btn-load-more');
const total_real_estates = Number(document.querySelector('#total').textContent);
let real_estates_count = Number(document.getElementsByClassName('l-sdb-list__single').length);

// click Xem them and wait for 0.25s
if (button !== null) {
    const clickInterval = setInterval(() => {
        button.click();
        real_estates_count = Number(document.getElementsByClassName('l-sdb-list__single').length);

        if(real_estates_count === total_real_estates) {
            clearInterval(clickInterval);
        }
    }, 250)
}
"""

get_contact_info_script = """
const contact_button = document.querySelector("body > div.sdb-picker-site > div.sdb-bnav > div > div > div.ctr-wrp > div > a");
contact_button.click();
setTimeout(() => {
    const customer_type_button = document.querySelector("#form-quote > div:nth-child(1) > div > label:nth-child(1) > div");
    const submit_button = document.querySelector("#btn-submit-quote");
    customer_type_button.click();
    document.querySelector("#form-quote > div:nth-child(3) > input").value = 'Ho Va Ten';
    document.querySelector("#form-quote > div:nth-child(4) > input").value = '0987654321';
    submit_button.click();
}, 100)
"""

class GulandSpiderSpider(scrapy.Spider):
    name = "guland_spider"
    allowed_domains = ["guland.vn"]
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 300*1000,
        'PLAYWRIGHT_BROWSER_TYPE': "chromium",
    }

    def __init__(self, province='ha-noi'):
        super().__init__()
        self.province= province

    def start_requests(self):
        start_url = 'https://guland.vn/mua-ban-bat-dong-san'
        yield scrapy.Request(url=start_url, callback=self.parse_home_page)

    def parse_home_page(self, response):

        # Discover real estate page for each province
        province_page_links = response.css('div.c-list-related#ListRelated-Cities')[0].css('li a::attr(href)').getall()

        for province_page_link in province_page_links:
            province = province_page_link.replace('/mua-ban-bat-dong-san-', '')
            if province == self.province:
                province_full_page_link = urljoin('https://guland.vn/mua-ban-bat-dong-san', province_page_link)
                yield scrapy.Request(url=province_full_page_link, callback=self.parse_province_page, meta={'province': province})

    def parse_province_page(self, response):
        province = response.meta['province']
        
        # Discover real estate page for each district
        district_page_links = response.css('div.c-list-related#ListRelated-Cities')[0].css('li a::attr(href)').getall()

        for district_page_link in district_page_links:
            district = district_page_link.replace('/mua-ban-bat-dong-san-', '').replace(f'-{province}', '')
            district_full_page_link = urljoin('https://guland.vn/mua-ban-bat-dong-san', district_page_link)
            if district == 'quan-hai-ba-trung':
                yield scrapy.Request(url=district_full_page_link, callback=self.parse_district_page, 
                                    meta={
                                        'province': province,
                                        'district': district,
                                        'playwright': True,
                                        'playwright_include_page': True,
                                        'playwright_page_methods': [
                                            PageMethod('evaluate', click_show_more_script),
                                            PageMethod("wait_for_timeout", 300*1000),
                                        ]
                                    },
                                    errback=self._errback)

    async def parse_district_page(self, response):
        province = response.meta['province']
        district = response.meta['district']
        page = response.meta['playwright_page']
        await page.close()

        # Discover page links for province 's real estate
        real_estates = response.css('div.l-sdb-list__single')
        for real_estate in real_estates:
            real_estate_link = real_estate.css('div.c-sdb-card__tle a::attr(href)').get()
            yield scrapy.Request(url=real_estate_link, callback=self.parse_real_estate_page,
                                 meta={
                                     'province': province,
                                     'district': district,
                                     'playwright': True,
                                     'playwright_include_page': True,
                                     'playwright_page_methods': [
                                         PageMethod('evaluate', get_contact_info_script),
                                         PageMethod('wait_for_selector', '#modal-contact-content > div > div > div > div.zl-wrp__cnt > div.zl-wrp__num > a'),
                                     ],
                                 },
                                 errback=self._errback)

    async def parse_real_estate_page(self, response):
        province = response.meta['province']
        district = response.meta['district']
        page = response.meta['playwright_page']
        await page.close()

        bds_item = BatdongsanItem()

        bds_item['title'] = response.css('h1.dtl-tle::text').get()
        bds_item['description'] = '.'.join(response.css('div.dtl-inf__dsr::text').getall())
        bds_item['price'] = response.css('div.dtl-prc__sgl.dtl-prc__ttl::text').get()
        bds_item['square'] = response.css('div.dtl-prc__sgl.dtl-prc__dtc::text').get()
        bds_item['address'] = {'full_address': None, 'province': None, 'district': None, 'ward': None}
        bds_item['address']['full_address'] = response.css('div.dtl-stl__row')[0].css('span::text').get()
        bds_item['address']['province'] = response.meta['province']
        bds_item['post_id'] = response.css('div.dtl-stl__row')[1].css('b::text').get()
        last_update = response.css('div.dtl-stl__row')[1].css('span::text')[1].get()
        delta_value, delta_type = last_update.replace('Cập nhật', '').replace('trước', '').strip().split()
        delta_value = int(delta_value)
        curr_time = datetime.now()
        if delta_type == 'giây':
            time_delta = timedelta(seconds=delta_value)
        elif delta_type == 'phút':
            time_delta = timedelta(minutes=delta_value)
        elif delta_type == 'giờ':
            time_delta = timedelta(hours=delta_value)
        elif delta_type == 'ngày':
            time_delta = timedelta(days=delta_value)
        elif delta_type == 'tuần':
            time_delta = timedelta(weeks=delta_value)
        elif delta_type == 'tháng':
            time_delta = timedelta(days=30*delta_value)
        elif delta_type == 'năm':
            time_delta = timedelta(days=365*delta_value)

        bds_item['post_date'] = (curr_time - time_delta).strftime('%d/%m/%Y')

        contact_info = {}
        contact_info['name'] = response.css('div.dtl-aut__cxt h5.dtl-aut__tle::text').get()
        contact_info['phone'] = [phone.strip() for phone in response.css('#modal-contact-content > div > div > div > div.zl-wrp__cnt > div.zl-wrp__num > a::text').getall()]
        bds_item['contact_info'] = contact_info

        extra_infos = {}
        if response.css('div.dtl-inf__wrp div.dtl-inf__row'):
            for extra_info in response.css('div.dtl-inf__wrp div.dtl-inf__row div.s-dtl-inf'):
                label = extra_info.css('div.s-dtl-inf__lbl::text').get().replace(':', '')
                value = extra_info.css('div.s-dtl-inf__val b::text').get()

                if label == 'Loại BĐS':
                    bds_item['estate_type'] = value
                else:
                    extra_infos[label] = value

        bds_item['extra_infos'] = extra_infos

        bds_item['link'] = response.url
        yield bds_item

    async def _errback(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()


