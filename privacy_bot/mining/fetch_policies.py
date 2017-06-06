#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Privacy Bot - privacy policies fetcher.

Usage:
    fetch_policies [options] <policies_per_domain>

Options:
    -m, --max_connections M Maximum number of concurrent connections [default: 30]
    --tld TLDS              Only fetch given tld.
    --update FILE           Update given index file.
    --ignore URLS           Ignore urls given in the file.
"""

from collections import defaultdict
from html import unescape
from urllib.parse import urlparse, unquote_plus
import asyncio
import json
import logging
import os.path
import string

import aiohttp
import cld2
import docopt
import regex as re
import tldextract
import tqdm

from privacy_bot.mining.fetcher import async_fetch, USERAGENT
from privacy_bot.mining.utils import setup_logging


def extract_text(html):
    # First we remove inline JavaScript/CSS:
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html)
    # Then we remove html comments. This has to be done before removing regular
    # tags since comments can contain '>' characters.
    cleaned = re.sub(r"(?s)<!--(.*?)-->[\n]?", "", cleaned)
    # Next we can remove the remaining tags:
    cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
    # Finally, we deal with whitespace
    cleaned = re.sub(r"(&nbsp;|\s+)", " ", cleaned)

    return unescape(cleaned.strip())


async def fetch_privacy_policy(session, semaphore, policy_url, domain):
    # Extract domain information
    ext = tldextract.extract(policy_url)
    suffix = ext.suffix
    if domain is None:
        domain = ext.domain
    registered_domain = ext.registered_domain

    # Unquote url
    while policy_url != unquote_plus(policy_url):
        policy_url = unquote_plus(policy_url)
    policy_url = policy_url.strip()
    # Get name of the document (last part of the path from url)
    name = urlparse(policy_url).path.rstrip('/').rsplit('/', 1)[-1]

    # Fetch policy page content
    async with semaphore:
        response = await async_fetch(session, policy_url)

    if not response:
        logging.info('Could not fetch content of %s', policy_url)
        return

    # Get content of the page
    content = response["text"]
    if not content:
        logging.info('Content policy has no content: %s', policy_url)
        return

    # Extract text async using pandoc
    text = extract_text(content)

    # lowered = content.lower()
    # if len(lowered) < 1600:
    #     logging.error('Content policy is too short: %s', policy_url)
    #     return

    # Detect language
    try:
        _, _, details = cld2.detect(text)
        lang = details[0].language_code
        lang_probability = details[0].percent
    except ValueError:
        # Try again after cleaning the text
        try:
            _, _, details = cld2.detect(''.join(x for x in text if x in string.printable))
            lang = details[0].language_code
            lang_probability = details[0].percent
        except ValueError:
            logging.exception('Could not guess language from %s', policy_url)
            lang = None
            lang_probability = None


    return {
        "domain": domain,
        "html": content,
        "text": text,
        "lang": lang,
        "lang_probability": lang_probability,
        "name": name,
        "url": policy_url,
        "suffix": suffix,
        "registered_domain": registered_domain
    }


async def fetch_policies_from_domain(semaphore, session, policy_metadata):
    """Given metadata on a domain, fetch the privacy policies. """
    print(policy_metadata)
    candidates = policy_metadata['privacy_policies']
    if candidates:
        # Fetch each privacy policy for a given domain
        loop = asyncio.get_event_loop()
        return list(filter(None, await asyncio.gather(*[
            loop.create_task(fetch_privacy_policy(
                semaphore=semaphore,
                session=session,
                policy_url=url,
                domain=policy_metadata['domain']
            ))
            for url in candidates
        ])))
    else:
        logging.error('No candidates for %s', policy_metadata['url'])
        return None


async def fetch_all_policies(loop, policies_per_domain, index, max_connections, tld=None):
    semaphore = asyncio.Semaphore(max_connections)
    connector = aiohttp.TCPConnector(loop=loop, verify_ssl=False, limit=None)
    async with aiohttp.ClientSession(loop=loop, connector=connector,
                                     cookie_jar=aiohttp.helpers.DummyCookieJar(),
                                     headers={'User-agent': USERAGENT}) as client:

        # Trigger fetching of policies async
        coroutines = [
            loop.create_task(fetch_policies_from_domain(semaphore, client, policy_metadata))
            for domain_policies in policies_per_domain.values()
            for policy_metadata in domain_policies.values()
            if ((tld is None or (policy_metadata['tld'] == tld)) and
                policy_metadata['privacy_policies']
               )
        ]

        # Create index.json and persist policies on-disk
        for completed in tqdm.tqdm(asyncio.as_completed(coroutines),
                                   total=len(coroutines),
                                   dynamic_ncols=True,
                                   desc='Fetching',
                                   unit='domain'):
            # Get policies for the given domain
            policies = await completed
            if not policies:
                continue

            for policy in policies:
                domain = policy['domain']
                if domain not in index:
                    index[domain] = []

                output_dir = os.path.join(
                    'privacy_policies',
                    policy['domain'],
                    policy['suffix'],
                    policy["registered_domain"])

                # Create directory if it does not yet exist
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                # Dump privacy policy on disk (html + plain text)
                name = policy['name']
                content_files = [
                    ('html', '{}.html'.format(name)),
                    ('text', '{}.txt'.format(name))
                ]

                try:
                    for key, content_path in content_files:
                        with open(os.path.join(output_dir, content_path), 'wb') as output:
                            output.write(policy[key].encode('utf-8'))
                except OSError:
                    continue

                # Update index
                index[domain].append({
                    'path': os.path.join(output_dir, name),
                    "name": policy['name'],
                    'url': policy['url'],
                    'lang': policy['lang'],
                    'lang_probability': policy['lang_probability'],
                    'tld': policy['suffix'],
                    'registered_domain': policy['registered_domain']
                })

        # Dump index.json
        with open('index.json', 'w') as output:
            json.dump(index, output, sort_keys=True, indent=4)


def main():
    setup_logging()

    # Parse cli arguments
    args = docopt.docopt(__doc__)
    metadata_path = args['<policies_per_domain>']
    tld = args['--tld']
    max_connections = int(args['--max_connections'])

    # Update an existing index file
    index = defaultdict(list)
    if args['--update']:
        with open(args['--update']) as index_file:
            index = json.load(index_file)

    # Ignore
    ignore = set()
    if args['--ignore']:
        with open(args['--ignore']) as input_ignore:
            ignore = frozenset(json.load(input_ignore))

    # Load list of privacy policies to fetch and get to work!
    with open(metadata_path, 'r') as input_metadata:
        policies_per_domain = {
            domain: metadata
            for domain, metadata in json.load(input_metadata).items()
            if domain not in index and domain not in ignore
        }

        loop = asyncio.get_event_loop()
        loop.run_until_complete(fetch_all_policies(
            loop=loop,
            policies_per_domain=policies_per_domain,
            index=index,
            tld=tld,
            max_connections=max_connections
        ))


if __name__ == "__main__":
    main()
