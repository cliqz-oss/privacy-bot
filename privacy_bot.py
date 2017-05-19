#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Detect privacy policy URL from home pages.

Usage:
    privacy_bot [options] [<url>...]
    privacy_bot -h | --help

Options:
    -u, --urls U        File containing a list of urls
    -j, --jobs J        Number of parallel jobs [default: 10]
    -h, --help          Show help
"""


import logging
import os
import os.path
import sys
import multiprocessing
import docopt
import requests
import tldextract
from bs4 import BeautifulSoup
from readability import Document
from headless import HeadlessPrivacyScraper

import pypandoc
from pypandoc.pandoc_download import download_pandoc

KEYWORDS = ['privacy', 'datenschutz',
            'Конфиденциальность',  'Приватность', 'тайность',
            '隐私', '隱私', 'プライバシー', 'confidential',
            'mentions-legales']

LANGS = {
    'fr': 'fr',
    'de': 'de',
    'com': 'en',
    'co.uk': 'uk',
    'ru': 'ru'
}


def fetch(url):
    retry = 0
    while retry < 3:
        try:
            ext = tldextract.extract(url)
            suffix = ext.suffix
            headers = {}
            headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'
            if suffix in LANGS:
                headers["Accept-Language"] = LANGS.get(suffix, suffix)
            else:
                headers["Accept-Language"] = 'en'

            return requests.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=5
            )
        except:
            retry += 1


def fetch_privacy_policy(policy_url):
    print('fetch_privacy_policy', policy_url)

    # Extract domain
    ext = tldextract.extract(policy_url)
    suffix = ext.suffix
    domain = ext.domain
    print('domain', domain)

    # Fetch policy page
    print('Fetch policy', policy_url)
    response = fetch(policy_url)

    # Sanity checks
    if not response.ok:
        print('Failed to fetch:', response.reason)
        return
    lowered = response.text.lower()

    if not any(keyword in KEYWORDS for keyword in lowered.split()):
        print('No keyword found')
        return
    if len(lowered) < 1600:
        print('Too short:', len(response.content))
        return

    # Extract policy content
    doc = Document(response.content)
    print(doc.title())

    # Convert to github markup
    content = doc.summary().encode('utf-8')
    converted = pypandoc.convert_text(
        content, 'markdown_github', format='html')
    converted = policy_url + '\n\n' + converted

    print(domain)

    output_dir = os.path.join('privacy_policies', domain)
    try:
        os.makedirs(output_dir)
    except os.error:
        pass

    # Write output
    with open(os.path.join(output_dir, suffix + '.md'), 'wb') as output:
        output.write(converted.encode('utf-8'))

    return True


def iter_protocols(base_url):
    for protocol in ['https://', 'http://']:
        yield protocol + base_url


def iter_policy_static(url):
    patterns = [
        # '/privacy',
        # '/privacy-policy',
        # '/privacy/privacy-policy',
        # '/legal/privacy',
        # '/legal/confidential',
    ]
    for p in patterns:
        yield url.rstrip('/') + p


def iter_policy_heuristic(url):
    """Fetch the page and try to find a privacy URL in it."""
    response = fetch(url)
    if response and response.status_code == 200:
        soup = BeautifulSoup(response.content, 'lxml')
        for link in soup.find_all('a', href=True):
            for keyword in KEYWORDS:
                href = link['href']
                href_lower = href.lower()
                text = link.text.lower()
                # print("Text Link: ",  text, href)
                if keyword in href_lower or keyword in text:
                    # Get full privacy policy URL
                    if href.startswith('//'):
                        href = 'http:' + href
                    elif href.startswith('/'):
                        href = url.rstrip('/') + href
                    yield href


def iter_second_level_url(url):
    # TODO: Make heuristic
    for p in ['/terms', '/legal', '/policies']:
        yield url.rstrip('/') + p


def iter_url_candidates(base_url, level=0):
    for url in iter_protocols(base_url):
        # Check to extract based on heuristic
        yield from iter_policy_heuristic(url)
        # Check static list
        yield from iter_policy_static(url)
        # Check at second level
        if level == 0:
            for second_level_url in iter_second_level_url(base_url):
                yield from iter_url_candidates(second_level_url, level=1)


def get_privacy_policy_url(base_url):
    """Given a valid URL, try to locate the privacy statement page. """
    for url in iter_url_candidates(base_url):
        try:
            result = fetch_privacy_policy(url)
            if result:
                # We found the policy
                return True
        except:
            continue
    return False


def main():
    logging.basicConfig(level=logging.ERROR)

    # Download pandoc if needed
    try:
        # Check if Pandoc is available
        output = pypandoc.convert_text('#Test', 'rst', format='md')
    except Error as e:
        # Download pandoc
        download_pandoc()

    args = docopt.docopt(__doc__)
    jobs = int(args['--jobs'])

    # Gather every urls
    urls = args['<url>']
    from_file = args.get('--urls')
    if from_file is not None:
        with open(from_file) as urls_file:
            urls.extend(urls_file)

    # Remove comments and empty lines
    urls = set(
        url.strip() for url in urls
        if not url.startswith('#') and len(url.strip()) > 0
    )

    # instance of Headless Browser Scrapper
    scraper = HeadlessPrivacyScraper()

    # Fetch data
    if len(urls) > 0:
        found = 0
        print("Processing %s urls" % len(urls), file=sys.stderr)
        print("Number of jobs: %s" % jobs, file=sys.stderr)
        print('-' * 15, file=sys.stderr)
        print("Privacy Bot")

        if jobs > 1:
            pool = multiprocessing.Pool(jobs)
            print('Created Pool', file=sys.stderr)
            policies = pool.map(get_privacy_policy_url, urls)
        else:
            policies = map(get_privacy_policy_url, urls)

        print('Map done', file=sys.stderr)
        for url, result in zip(urls, policies):
            if not result:
                print('Not found', url)

                print('Trying with Javascript on: ', url)
                for pUrl in iter_protocols(url):
                    links = scraper.serve_qualified(pUrl)
                    print(links)

                    policies = map(get_privacy_policy_url, links)

                    print("====")
                scraper.quit_driver()


        print('-' * 15, file=sys.stderr)


if __name__ == "__main__":
    main()
