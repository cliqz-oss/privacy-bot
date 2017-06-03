#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Privacy Bot - privacy policies finder.

Usage:
    find_policies [options] [<url>...]

Options:
    --update FILE       Update the given candidates file.
    --tld TLD           Only find policies on domain having this tld.
    -u, --urls U        File containing a list of urls
    -l, --limit L       Limit number of URLs checked
    -w, --websearch     Do a websearch in case the heuristic fails
    -h, --help          Show help
"""

from itertools import islice
from urllib.parse import urljoin
import asyncio
import concurrent.futures
import json
import logging
import re
import sys

from bs4 import BeautifulSoup
import aiohttp
import docopt
import tldextract
import tqdm

from privacy_bot.mining.fetcher import (
    async_fetch,
    check_if_url_exists,
    fetch_headless
)
from privacy_bot.mining.utils import setup_logging
import privacy_bot.mining.websearch as websearch


KEYWORDS = ['privacy', 'datenschutz',
            'Конфиденциальность', 'Приватность', 'тайность',
            '隐私', '隱私', 'プライバシー', 'confidential',
            'mentions-legales', 'conditions-generales',
            'mentions légales', 'conditions générales',
            'termini-e-condizioni']
KEYWORDS_RE = re.compile('|'.join(KEYWORDS), flags=re.IGNORECASE)


def extract_candidates(html, url):
    if not html:
        return []

    # Get real url, after redirect
    real_url = str(url)

    # Parse document
    soup = BeautifulSoup(html, 'lxml')

    candidates = set()

    # Check for pattern in `href`
    candidates.update(
        urljoin(real_url, link['href'])
        for link in soup.find_all('a', href=KEYWORDS_RE)
    )

    # Check for pattern in `string`
    candidates.update(
        urljoin(real_url, link['href'])
        for link in soup.find_all('a', href=True, string=KEYWORDS_RE)
    )

    return list(candidates)


async def iter_policy_heuristic(session, semaphore, url):
    """Given the URL (usually the homepage) of a domain, extract a list of
    privacy policies url candidates.
    """
    candidates = None
    async with semaphore:
        # Check if the URL exists
        url_exists = await check_if_url_exists(session, url)
        if not url_exists:
            return []

        # Fetch content of the page
        response = await async_fetch(session, url)
        if response:
            candidates = extract_candidates(
                html=response['text'],
                url=response['url']
            )

        # Try the headlesss browser if there is no candidates
        if not candidates:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
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

    if not candidates:
        # Try the headless browser
        pass

    if not candidates and websearch:
        # If no candidates were found by the heuristic, do a websearch as fallback.
        candidates = policy_websearch(base_url)

    return {
        "url": base_url,
        "candidates": candidates
    }


async def get_candidates_policies(loop, urls, websearch, policies_metadata):
    print('-' * 80,                             file=sys.stderr)
    print('Initializing Privacy Bot',           file=sys.stderr)
    print('-' * 80,                             file=sys.stderr)
    print('Domains to Process: %s' % len(urls), file=sys.stderr)
    print('-' * 80,                             file=sys.stderr)
    print('',                                   file=sys.stderr)

    semaphore = asyncio.Semaphore(50)
    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.ClientSession(loop=loop, connector=connector) as client:
        coroutines = [
            loop.create_task(get_privacy_policy_url(client, semaphore, url, websearch))
            for url in urls
        ]

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
                "locale": None,
                "tld": tldextract.extract(url).suffix
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
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            loop.set_default_executor(executor)
            loop.run_until_complete(get_candidates_policies(
                loop=loop,
                urls=urls,
                websearch=websearch,
                policies_metadata=policies_metadata
            ))


if __name__ == "__main__":
    main()
