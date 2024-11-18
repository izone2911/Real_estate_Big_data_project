# Crawler parameters
export spider_name=i-batdongsan_spider;
export min_page=1;
export max_page=10;
export province="ha-noi";
export jump_to_page=$min_page;

# Kafka parameters
export kafka_bootstrap_servers="20.239.82.205:9192,20.239.82.205:9292,20.239.82.205:9392"

# Run crawler
scrapy crawl $spider_name \
    -a min_page=$min_page \
    -a max_page=$max_page \
    -a province=$province \
    -a jump_to_page=$jump_to_page \
    -s DOWNLOAD_DELAY=0 \
    -s KAFKA_BOOTSTRAP_SERVERS=$kafka_bootstrap_servers;
