#! /usr/bin/env python
# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from bs4 import BeautifulSoup

from privacy_bot.fetcher import fetch, fetch_headless


def websearch(query):
    """Get candidate URLs for the privacy policy of a given domain"""

    search_url = 'https://google.com/?#{}'.format(urlencode({'q':query}))
    print(search_url)
    #html_doc = fetch(search_url)
    html_doc = fetch_headless(search_url)
    # print(html_doc)
    soup = BeautifulSoup(html_doc, 'html.parser')
    candidates = soup.findAll("cite", {"class": "_Rm"})  # google SERP green "links"
    #candidates = html.split('\n') #[]
    print(search_url, candidates)
    for c in candidates:
        print(c)


if __name__ == '__main__':
    query = 'site:facebook.com privacy policy'
    websearch(query)