"""
Offsite Spider Middleware

See documentation in docs/topics/spider-middleware.rst
"""

import re

from scrapy import signals
from scrapy.http import Request
from scrapy.utils.httpobj import urlparse_cached
from scrapy import log

class OffsiteMiddleware(object):

    def __init__(self):
        self.host_regexes = {}
        self.domains_seen = {}

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def process_spider_output(self, response, result, spider):
        for x in result:
            if isinstance(x, Request):
                if x.dont_filter or self.should_follow(x, spider):
                    yield x
                else:
                    domain = urlparse_cached(x).hostname
                    if domain and domain not in self.domains_seen[spider]:
                        self.domains_seen[spider].add(domain)
                        log.msg(format="Filtered offsite request to %(domain)r: %(request)s",
                                level=log.DEBUG, spider=spider, domain=domain, request=x)
            else:
                yield x

    def should_follow(self, request, spider):
        regex = self.host_regexes[spider]
        # hostanme can be None for wrong urls (like javascript links)
        host = urlparse_cached(request).hostname or ''
        return bool(regex.search(host))

    def get_host_regex(self, spider):
        """Override this method to implement a different offsite policy"""
        allowed_domains = getattr(spider, 'allowed_domains', None)
        if not allowed_domains:
            return re.compile('') # allow all by default
        domains = [d.replace('.', r'\.') for d in allowed_domains]
        regex = r'^(.*\.)?(%s)$' % '|'.join(domains)
        return re.compile(regex)

    def spider_opened(self, spider):
        self.host_regexes[spider] = self.get_host_regex(spider)
        self.domains_seen[spider] = set()

    def spider_closed(self, spider):
        del self.host_regexes[spider]
        del self.domains_seen[spider]
