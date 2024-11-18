# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field


class BatdongsanItem(scrapy.Item):
    title = Field()
    description = Field()
    price = Field()
    square = Field()
    estate_type = Field()
    address = Field()
    post_date = Field()
    post_id = Field()
    contact_info = Field()
    extra_infos = Field()
    link = Field()
