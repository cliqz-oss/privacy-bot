#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import requests
import tldextract


class TimeoutError(Exception):
    pass


def wait_for(condition_function, timeout):
    start_time = time.time()
    while time.time() < start_time + timeout:
        if condition_function():
            return True
        else:
            time.sleep(0.1)
    raise TimeoutError('Timeout waiting for {}'.format(condition_function.__name__))


@contextmanager
def wait_for_page_load(browser, timeout):
    old_page = browser.find_element_by_tag_name('html')

    yield

    def page_has_loaded():
        new_page = browser.find_element_by_tag_name('html')
        return new_page.id != old_page.id

    wait_for(page_has_loaded, timeout)


USERAGENT = "Mozilla/5.0 (Macintosh; PPC Mac OS X 10.10; rv:10.0) \
            Gecko/20100101 Firefox/52.0"


TOP_LEVEL_TO_LOCALE = {
    'fr': 'fr-FR',
    'de': 'de-DE',
    'co.uk': 'en-GB',
    'es': 'es-ES',
    'ru': 'ru-RU',

    # By default, take the english version
    'com': 'en-US',
}


def fetch(url, max_retry=3, verbose=False):
    retry = 0
    while retry < max_retry:
        try:
            ext = tldextract.extract(url)
            suffix = ext.suffix
            headers = {}
            headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/52.0'
            if suffix in TOP_LEVEL_TO_LOCALE:
                headers["Accept-Language"] = TOP_LEVEL_TO_LOCALE.get(suffix, suffix)
            else:
                headers["Accept-Language"] = 'en'

            response = requests.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=5
            )
            
            if response.encoding and response.encoding.lower() != 'utf-8':
                try:
                    return response.text.encode(response.encoding).decode('utf-8')
                except UnicodeError:
                    logging.exception('Error converting to unicode from {}'.format(response.encoding))

            return response.text
        except:
            if verbose:
                logging.exception('While fetching')
            retry += 1


def fetch_headless(url, max_retry=3, timeout=10):
    # needs: npm -g install phantomjs-prebuilt
    print('fetch_headless')
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = USERAGENT

    print('Create driver')
    driver = webdriver.PhantomJS(desired_capabilities=dcap)
    print('Set window size')
    driver.set_window_size(1120, 550)

    try:
        print('Get URL', url)
        with wait_for_page_load(driver, timeout):
            driver.get(url)
            result = driver.page_source
        driver.quit()
        return result
    except TimeoutError:
        pass
