# -*- coding: utf-8 -*-`

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import tldextract
# import logging


KEYWORDS = ['privacy', 'datenschutz',
            'Конфиденциальность',  'Приватность', 'тайность',
            '隐私', '隱私', 'プライバシー', 'confidential',
            'mentions-legales']

USERAGENT = "Mozilla/5.0 (Macintosh; PPC Mac OS X 10.10; rv:10.0) \
            Gecko/20100101 Firefox/52.0"


class HeadlessPrivacyScraper(object):
    def __init__(self):

        # needs: npm -g install phantomjs-prebuilt
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = USERAGENT

        self.driver = webdriver.PhantomJS(desired_capabilities=dcap)
        self.driver.set_window_size(1120, 550)

    def iter_links(self, url):
        self.driver.get(url)
        wait = WebDriverWait(self.driver, 5)
        import time
        time.sleep(5)

        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        for link in soup.find_all('a', href=True):
            for keyword in KEYWORDS:
                href = link['href']
                href_lower = href.lower()
                text = link.text.lower()
                if keyword in href_lower or keyword in text:
                    # Get full privacy policy URL
                    if href.startswith('//'):
                        href = 'http:' + href
                    elif href.startswith('/'):
                        href = url.rstrip('/') + href
                    yield href

    def found_links(self, url):
        links = [x for x in self.iter_links(url)]
        print("returning ", links)
        return links

    def quit_driver(self):
        self.driver.quit()


# if __name__ == '__main__':
#     # logging.basicConfig(filename='headless.log', level=logging.INFO)

#     scraper = HeadlessPrivacyScraper()
#     links = scraper.found_links("http://otto.de")
#     print(links)
