#! /usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import time
from contextlib import contextmanager

import aiohttp
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import requests
import tldextract


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


async def async_fetch(session, url, timeout=10):
    try:
        with aiohttp.Timeout(timeout, loop=session.loop):
            ext = tldextract.extract(url)
            suffix = ext.suffix
            headers = {}
            headers['User-agent'] = USERAGENT
            if suffix in TOP_LEVEL_TO_LOCALE:
                headers["Accept-Language"] = TOP_LEVEL_TO_LOCALE.get(suffix, suffix)
            else:
                headers["Accept-Language"] = 'en'

            async with session.get(url, headers=headers) as response:
                # Try to get decoded content
                try:
                    text = await response.text()
                except UnicodeDecodeError:
                    text = None

                # Try to get raw html content
                try:
                    content = await response.content.read()
                except aiohttp.ClientPayloadError:
                    content = None

                return {
                    "status": 200,
                    "content": content,
                    "text": text,
                    "url": response.url
                }
    except asyncio.TimeoutError:
        logging.error('Fetch timeout for %s', url)


def fetch(url, max_retry=3, verbose=False):
    retry = 0
    while retry < max_retry:
        try:
            ext = tldextract.extract(url)
            suffix = ext.suffix
            headers = {}
            headers['User-agent'] = USERAGENT
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


class HeadlessFetch:
    def __init__(self, timeout=10):
        self.timeout = timeout

        # needs: npm -g install phantomjs-prebuilt
        print('Create headless browser')
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = USERAGENT
        self.driver = webdriver.PhantomJS(desired_capabilities=dcap)
        self.driver.set_window_size(1120, 550)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.quit()

    def quit(self):
        self.driver.quit()

    def fetch(self, url):
        try:
            with wait_for_page_load(self.driver, self.timeout):
                self.driver.get(url)
                result = self.driver.page_source
            return result
        except:
            return ''


def fetch_headless(url, timeout=10):
    with HeadlessFetch(timeout=timeout) as headless_fetcher:
        return headless_fetcher.fetch(url)
    return ''
