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


from __future__ import print_function, unicode_literals
from pprint import pprint
import os
import os.path
import sys
import multiprocessing
import docopt
import requests
import tldextract
from bs4 import BeautifulSoup
from readability import Document

import pypandoc
from pypandoc.pandoc_download import download_pandoc
from github import Github


LANGS = {
    'fr': 'fr',
    'de': 'de',
    'com': 'en',
    'co.uk': 'uk'
}


def fetch_privacy_policy(base_url, policy_url):
    # Extract domain
    domain = base_url.rstrip('/').rsplit('/', 1)[-1]
    if domain.startswith('www.'):
        domain = domain[4:]

    ext = tldextract.extract(base_url)
    suffix = ext.suffix
    domain = domain[:-(len(suffix) + 1)]
    print('domain', domain)

    # Get full privacy policy URL
    if policy_url.startswith('/'):
        policy_url = base_url.rstrip('/') + policy_url

    # Fetch policy page
    print('Fetch policy', policy_url)
    if suffix in LANGS:
        headers = {"Accept-Language": LANGS.get(suffix, suffix)}
    else:
        headers = {}
    response = requests.get(policy_url, headers=headers)

    # Sanity checks
    if not response.ok:
        print('Failed to fetch:', response.reason)
        return
    lowered = response.text.lower()
    if 'policy' not in lowered or 'privacy' not in lowered:
        print('No keyword found')
        return
    if len(response.content) < 1600:
        print('Too short:', len(response.content))
        return

    # Extract policy content
    doc = Document(response.content)
    print(doc.title().encode('utf-8'))

    # Convert to github markup
    content = doc.summary().encode('utf-8')
    converted = pypandoc.convert_text(content, 'markdown_github', format='html')
    converted = policy_url + '\n\n' + converted

    output_dir = os.path.join('privacy_policies', domain)
    try:
        os.makedirs(output_dir)
    except os.error:
        pass

    # Write output
    with open(os.path.join(output_dir, suffix + '.md'), 'wb') as output:
        output.write(converted.encode('utf-8'))


def get_privacy_policy_url(url):
    """Given a valid URL, try to locate the privacy statement page. """
    url = url.decode('utf8')
    if not url.startswith('http'):
        full_url = 'https://' + url
    else:
        full_url = url
    print()
    retry = 0
    while retry < 3:
        try:
            print(full_url, file=sys.stderr)
            response = requests.get(
                full_url,
                allow_redirects=True,
                verify=True,
                stream=True)
        except Exception as e:
            print('Exception', e, file=sys.stderr)
            retry += 1
            # Try with http
            if not url.startswith('http'):
                full_url = 'http://' + url
        else:
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                for link in soup.find_all('a', href=True):
                    if 'privacy' in link['href'].lower():
                        print('Found privacy:', link['href'])
                        return (
                            link['href'].encode('utf-8'),
                            link.string.encode('utf-8'),
                            fetch_privacy_policy(full_url, link['href'])
                        )
                retry += 1
            else:
                print('Failed to fetch:', response.reason)
                retry += 1


def main():
    # Download pandoc if needed
    download_pandoc()

    args = docopt.docopt(__doc__)
    jobs = int(args['--jobs'])

    # Gather every urls
    urls = args['<url>']
    from_file = args.get('--urls')
    if from_file is not None:
        with open(from_file, 'r') as urls_file:
            urls.extend(urls_file.read().split())
    urls = filter(None, urls)
    urls = filter(lambda l: not l.startswith('#'), urls)

    # Process
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
        for url, policy in zip(urls, policies):
            if policy is not None:
                found += 1
            print(url.split(), '\t', policy)

        print('-' * 15, file=sys.stderr)
        print("Found %s" % found, file=sys.stderr)


if __name__ == "__main__":
    main()
