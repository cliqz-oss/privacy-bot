#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Privacy Bot - privacy policies finder.

Usage:
    find_policies [options] [<url>...]

Options:
    --tld TLD               Only find policies on domain having this tld.
    --update FILE           Update the given candidates file.
    -j, --jobs J            Maximum number of workers [default: 10]
    -l, --limit L           Limit number of URLs checked
    -m, --max_connections M Maximum number of concurrent connections [default: 30]
    -u, --urls U            File containing a list of urls
    -w, --websearch         Do a websearch in case the heuristic fails
    -h, --help              Show help
"""

from itertools import islice
from urllib.parse import urljoin, urldefrag
import asyncio
import concurrent.futures
import json
import logging
import sys

import aiohttp
import docopt
import regex as re
import tldextract
import tqdm

from privacy_bot.mining.fetcher import (
    async_fetch,
    check_if_url_exists,
    fetch_headless,
    USERAGENT
)
from privacy_bot.mining.utils import setup_logging
import privacy_bot.mining.websearch as websearch


# TODO - find more patterns + handle more languages
# TODO - split patterns by language/top-level domain?
KEYWORDS = ['privacy', 'datenschutz',
            'Конфиденциальность', 'Приватность', 'тайность',
            '隐私', '隱私', 'プライバシー', 'confidential',
            'mentions-legales', 'conditions-generales',
            'mentions légales', 'conditions générales',
            'termini-e-condizioni']
KEYWORDS_RE = re.compile('|'.join(KEYWORDS), flags=re.IGNORECASE)


def extract_urls(html, string, href):
    urls = []
    current_position = 0
    while True:
        curpos = html.find("href=", current_position)
        if curpos >= 0:
            # Jump over 'href='
            curpos += 5
            quote_symbol = html[curpos]
            # Jump over opening quote
            curpos += 1

            # Find closing tag
            closing = html.find('>', curpos)
            assert closing != -1
            has_content = html[closing - 1] != '/'
            # ------------------------------

            # Extract href
            href_end = html.find(quote_symbol, curpos, closing)
            if href_end == -1:
                current_position = closing + 1
                continue
            # TODO - should it be `match` instead?
            url_match = href.search(html, curpos, href_end) != None
            if url_match:
                url = html[curpos:href_end]
                urls.append(url)
            # -------------------------------------------------

            # Extract content and try regex on it
            if has_content and not url_match:
                # Find next opening tag (max: 100)
                next_opening = html.find('<', closing, closing + 100)
                if next_opening != -1:
                    text_match = string.search(html, closing + 1, next_opening) != None
                    if text_match:
                        url = html[curpos:href_end]
                        urls.append(url)
                    current_position = next_opening + 1
                    continue

            current_position = closing + 1
        else:
            break
    return urls


def extract_candidates(html, url):
    if not html:
        return []

    # Get real url, after redirect
    real_url = str(url)

    return list(set(
        urldefrag(urljoin(real_url, href)).url
        for href in extract_urls(html, string=KEYWORDS_RE, href=KEYWORDS_RE)
    ))


async def iter_policy_heuristic(session, semaphore, url):
    """Given the URL (usually the homepage) of a domain, extract a list of
    privacy policies url candidates.
    """
    candidates = None

    # Check if the URL exists
    async with semaphore:
        url_exists = await check_if_url_exists(session, url)
        if not url_exists:
            return []

    # Fetch content of the page
    async with semaphore:
        response = await async_fetch(session, url)

    if response and response['text']:
        candidates = extract_candidates(
            html=response['text'],
            url=response['url']
        )

    # Try the headlesss browser if there is no candidates
    if not candidates:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            fetch_headless,
            url
        )
        if response:
            candidates = extract_candidates(
                html=response['text'],
                url=response['url']
            )

    if not candidates:
        logging.error('No candidates for %s', url)

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
    url = 'http://' + base_url

    candidates = await iter_policy_heuristic(session, semaphore, url)

    if not candidates and websearch:
        # If no candidates were found by the heuristic, do a websearch as fallback.
        candidates = policy_websearch(base_url)

    return {
        "url": base_url,
        "candidates": candidates
    }


async def get_candidates_policies(loop, urls, websearch, policies_metadata, max_connections):
    print('-' * 80,                             file=sys.stderr)
    print('Initializing Privacy Bot',           file=sys.stderr)
    print('-' * 80,                             file=sys.stderr)
    print('Domains to Process: %s' % len(urls), file=sys.stderr)
    print('-' * 80,                             file=sys.stderr)
    print('',                                   file=sys.stderr)

    semaphore = asyncio.Semaphore(max_connections)
    connector = aiohttp.TCPConnector(loop=loop, verify_ssl=False, limit=None)
    async with aiohttp.ClientSession(loop=loop, connector=connector,
                                     cookie_jar=aiohttp.helpers.DummyCookieJar(),
                                     headers={'User-agent': USERAGENT}) as client:
        coroutines = [
            loop.create_task(get_privacy_policy_url(client, semaphore, url, websearch))
            for url in urls
        ]

        for completed in tqdm.tqdm(asyncio.as_completed(coroutines),
                                   total=len(coroutines),
                                   dynamic_ncols=True,
                                   desc='Gather policies',
                                   unit='domain'):
            result = await completed
            candidates = result['candidates']
            url = result['url']

            ext = tldextract.extract(url)
            tld = ext.suffix
            domain = ext.domain

            if domain not in policies_metadata:
                policies_metadata[domain] = {}

            policies_metadata[domain][tld] = {
                "domain": domain,
                "url": url,
                "tld": tld,
                "privacy_policies": candidates
            }

        with open('policy_url_candidates.json', 'w') as output:
            json.dump(policies_metadata, output, sort_keys=True, indent=4)

        print('... written to policy_url_candidates.json')
        print('-' * 80, file=sys.stderr)


def main():
    setup_logging()
    args = docopt.docopt(__doc__)

    websearch = args['--websearch']
    tld = args['--tld']
    jobs = int(args['--jobs'])
    max_connections = int(args['--max_connections'])

    # Update existing candidates
    policies_metadata = {}
    if args['--update']:
        with open(args['--update'], 'rb') as input_candidates:
            policies_metadata = json.load(input_candidates)

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

    # Limit number of domains to process
    limit = args['--limit']
    if limit:
        limit = int(limit)
        urls = list(islice(urls, limit))

    # Fetch data
    if urls:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
            loop = asyncio.get_event_loop()
            loop.set_default_executor(executor)
            loop.run_until_complete(get_candidates_policies(
                loop=loop,
                urls=urls,
                websearch=websearch,
                policies_metadata=policies_metadata,
                max_connections=max_connections
            ))


if __name__ == "__main__":
    main()
