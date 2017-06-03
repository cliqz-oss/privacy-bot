#! /usr/bin/env python
# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from bs4 import BeautifulSoup

from privacy_bot.mining.fetcher import fetch_headless


def websearch(query):
    """Get web search results for a query"""
    # Get DuckDuckGo.com HTML
    search_url = 'https://duckduckgo.com/?%s' % urlencode({'q': query})
    # html_doc = fetch(search_url)
    html_doc = fetch_headless(search_url)

    # Extract DuckDuckGo results from HTML
    soup = BeautifulSoup(html_doc, 'html.parser')
    # print(soup.prettify())
    result_links = soup.findAll("a", {"class": "result__a"})

    result_urls = [link.get('href') for link in result_links]
    for u in result_urls:
        print(u)
    return result_urls


if __name__ == '__main__':
    query = 'site:facebook.com privacy policy'
    websearch(query)
