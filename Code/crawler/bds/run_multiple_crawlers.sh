# Crawler parameters
export min_page=1;
export max_page=3;
export province="ha-noi";
export jump_to_page=$min_page;

# Kafka parameters
export kafka_bootstrap_servers="20.239.82.205:9192,20.239.82.205:9292,20.239.82.205:9392"

# Run crawlers
scrapy crawl bds_spider \
    -a min_page=$min_page \
    -a max_page=$max_page \
    -a province=$province \
    -a jump_to_page=$jump_to_page \
    -s DOWNLOAD_DELAY=0 \
    -s KAFKA_BOOTSTRAP_SERVERS=$kafka_bootstrap_servers &
scrapy crawl i-batdongsan_spider \
    -a min_page=$min_page \
    -a max_page=$max_page \
    -a province=$province \
    -a jump_to_page=$jump_to_page \
    -s DOWNLOAD_DELAY=0 \
    -s KAFKA_BOOTSTRAP_SERVERS=$kafka_bootstrap_servers &
scrapy crawl nhadatviet_spider \
    -a min_page=$min_page \
    -a max_page=$max_page \
    -a province=$province \
    -a jump_to_page=$jump_to_page \
    -s DOWNLOAD_DELAY=0 \
    -s KAFKA_BOOTSTRAP_SERVERS=$kafka_bootstrap_servers &

