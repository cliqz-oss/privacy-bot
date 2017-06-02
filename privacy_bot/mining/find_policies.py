#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Privacy Bot - privacy policies finder.

Usage:
    find_policies [options] [<url>...]

Options:
    --tld TLD           Only find policies on domain having this tld.
    -u, --urls U        File containing a list of urls
    -l, --limit L       Limit number of URLs checked
    -w, --websearch     Do a websearch in case the heuristic fails
    -h, --help          Show help
"""

from itertools import islice
from urllib.parse import urljoin
import asyncio
import json
import logging
import sys

from bs4 import BeautifulSoup
import aiohttp
import docopt
import tldextract
import tqdm

from privacy_bot.mining.fetcher import async_fetch
from privacy_bot.mining.utils import setup_logging
import privacy_bot.mining.websearch as websearch


KEYWORDS = ['privacy', 'datenschutz',
            'Конфиденциальность', 'Приватность', 'тайность',
            '隐私', '隱私', 'プライバシー', 'confidential',
            'mentions-legales']


def iter_protocols(base_url):
    for protocol in ['https://', 'http://']:
        yield protocol + base_url


async def iter_policy_heuristic(session, semaphore, url):
    """Fetch the page and try to find a privacy URL in it."""
    candidates = []

    async with semaphore:
        try:
            response = await async_fetch(session, url)
        except:
            return

        if not response:
            return

        # Try to use `text`, and if not present, use `content` as a fallback
        content = response["text"]
        if not content:
            content = response["content"]
        if not content:
            return

        # Get real url, after redirect
        real_url = str(response["url"])

        soup = BeautifulSoup(content, 'lxml')
        for link in soup.find_all('a', href=True):
            for keyword in KEYWORDS:
                href = link['href']
                href_lower = href.lower()
                text = link.text.lower()
                if keyword in href_lower or keyword in text:
                    # print(text, href_lower)
                    # Get full privacy policy URL
                    href = urljoin(real_url, href)
                    candidates.append(href)
        return candidates


def policy_websearch(base_url):
    query = 'site:%s' % base_url
    # guess the language from the TLD
    if any(tld in base_url for tld in ['.de', '.at']):
        search_terms = 'datenschutz'
    # if we can't guess the language
    else:
        search_terms = 'privacy'
    return websearch.websearch(query + ' ' + search_terms)


async def get_privacy_policy_url(session, semaphore, base_url, websearch=False):
    """Given a valid URL, try to locate the privacy statement page. """
    candidates = set()

    for url in iter_protocols(base_url):
        new_candidates = await iter_policy_heuristic(session, semaphore, url)

        # Stop as soon as we found a valid page and extracted URLs from it.
        if new_candidates:
            candidates.update(new_candidates)
            break

    if websearch:
        # If no candidates were found by the heuristic, do a websearch as fallback.
        urls_from_websearch = policy_websearch(base_url)
        candidates.update(urls_from_websearch)

    return {
        "url": base_url,
        "candidates": list(candidates)
    }


async def get_candidates_policies(loop, urls, websearch):
    print('-' * 80,                             file=sys.stderr)
    print('Initializing Privacy Bot',           file=sys.stderr)
    print('-' * 80,                             file=sys.stderr)
    print('Domains to Process: %s' % len(urls), file=sys.stderr)
    print('-' * 80,                             file=sys.stderr)
    print('',                                   file=sys.stderr)

    # Find privacy policies
    semaphore = asyncio.Semaphore(30)
    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.ClientSession(loop=loop, connector=connector) as client:
        coroutines = [
            loop.create_task(get_privacy_policy_url(client, semaphore, url, websearch))
            for url in urls
        ]

        # Generate policies_metadata file
        print('',                                      file=sys.stderr)
        print('Generating policy_url_candidates file', file=sys.stderr)

        policies_metadata = {}
        for completed in tqdm.tqdm(asyncio.as_completed(coroutines),
                                   total=len(coroutines),
                                   dynamic_ncols=True,
                                   unit='domain'):
            result = await completed
            candidates = result['candidates']
            url = result['url']

            # print('url: ', url, 'policies: ', policies)
            policies_metadata[url] = {
                "domain": url,
                "privacy_policies": candidates,
                "locale": "fr-FR",
                "tld": tldextract.extract(url).suffix
            }

        with open('policy_url_candidates.json', 'w') as output:
            json.dump(policies_metadata, output, sort_keys=True, indent=4)

        print('... written to policy_url_candidates.json')
        print('-' * 80, file=sys.stderr)


def main():
    setup_logging()
    args = docopt.docopt(__doc__)

    limit = args['--limit']
    if limit:
        limit = int(limit)

    websearch = args['--websearch']
    tld = args['--tld']

    # Gather every urls
    urls = args['<url>']
    from_file = args.get('--urls')
    if from_file is not None:
        with open(from_file) as urls_file:
            urls.extend(urls_file)

    # Remove comments and empty lines
    urls = set(
        url.strip() for url in urls
        if (not url.startswith('#') and
            len(url.strip()) > 0 and
            (tld is None or (tldextract.extract(url).suffix == tld))
           )
    )

    if limit:
        urls = list(islice(urls, limit))

    # Fetch data
    if urls:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_candidates_policies(
            loop=loop,
            urls=urls,
            websearch=websearch
        ))


if __name__ == "__main__":
    main()
