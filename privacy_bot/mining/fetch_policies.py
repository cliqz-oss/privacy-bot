#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Privacy Bot - privacy policies fetcher.

Usage:
    fetch_policies [options] <policies_per_domain>

Options:
    --tld TLDS     Only fetch given tld.
"""


from collections import defaultdict
import asyncio
import html
import json
import logging
import os.path

from readability.readability import Document
import aiohttp
import docopt
import html2text
import langdetect
import tldextract
import tqdm

from privacy_bot.mining.fetcher import async_fetch
from privacy_bot.mining.utils import setup_logging


async def fetch_privacy_policy(session, semaphore, policy_url):
    async with semaphore:
        # Extract domain information
        ext = tldextract.extract(policy_url)
        suffix = ext.suffix
        registered_domain = ext.registered_domain

        # Fetch policy page
        try:
            response = await async_fetch(session, policy_url)
        except:
            logging.exception('Exception while fetching %s', policy_url)
            return

        if not response:
            return

        content = response["text"]
        if not content:
            content = response["content"]
        if not content:
            logging.error('Content policy has no content: %s', policy_url)
            return

        lowered = content.lower()
        if len(lowered) < 1600:
            logging.error('Content policy is too short: %s', policy_url)
            return

        # Extract content
        readability = Document(content)
        title = readability.short_title()

        html_converter = html2text.HTML2Text()
        html_converter.ignore_links = True
        html_converter.ignore_emphasis = True
        html_converter.ignore_images = True
        html_converter.ignore_tables = True
        html_converter.skip_internal_links = True

        text = html_converter.handle(content)

        try:
            text = html.unescape(text)
        except:
            logging.exception('Exception while unescaping html of %s', policy_url)

        try:
            lang = langdetect.detect(text)
        except langdetect.lang_detect_exception.LangDetectException:
            # Can happen when no feature is found in the text
            # TODO: use headless fetch in this case
            lang = ''
            logging.exception('Could not detect lang for %s', policy_url)

        return {
            "html": content,
            "text": text,
            "lang": lang,
            "title": title,
            "url": policy_url,
            "suffix": suffix,
            "registered_domain": registered_domain
        }


async def fetch_policies_from_domain(loop, semaphore, session, policy_metadata):
    """Given metadata on a domain, fetch the privacy policies. """
    if policy_metadata['privacy_policies']:
        # Fetch each privacy policy for a given domain
        coroutines = [
            loop.create_task(fetch_privacy_policy(
                semaphore=semaphore,
                session=session,
                policy_url=url
            ))
            for url in policy_metadata['privacy_policies']
        ]

        tasks, _ = await asyncio.wait(
            coroutines,
            loop=loop,
            return_when=asyncio.ALL_COMPLETED)

        policies = []
        for task in tasks:
            result = await task
            if result:
                policies.append(result)
    else:
        logging.error('No candidates for %s', policy_metadata["domain"])
        policies = []

    return {
        "domain": policy_metadata["domain"],
        "policies": policies
    }


async def fetch_all_policies(loop, policies_per_domain, tld=None):
    # Trigger tasks async
    semaphore = asyncio.Semaphore(40)
    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.ClientSession(loop=loop, connector=connector) as client:
        coroutines = [
            loop.create_task(fetch_policies_from_domain(loop, semaphore, client, policy_metadata))
            for policy_metadata in policies_per_domain.values()
            if tld is None or (policy_metadata['tld'] == tld)
        ]

        # Dump results
        index = defaultdict(list)

        # Create index.json and persist policies on-disk
        for completed in tqdm.tqdm(asyncio.as_completed(coroutines),
                                   total=len(coroutines),
                                   dynamic_ncols=True,
                                    unit='domain'):
            domain_policies = await completed
            domain = domain_policies["domain"]
            for policy in domain_policies["policies"]:
                output_dir = os.path.join(
                    'privacy_policies',
                    domain,
                    policy["lang"] + '_' + policy["registered_domain"])

                # Create directory if it does not yet exist
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                content_files = [
                    ('html', 'policy.html'),
                    ('text', 'policy.txt')
                ]

                for key, content_path in content_files:
                    with open(os.path.join(output_dir, content_path), 'wb') as output:
                        output.write(policy[key].encode('utf-8'))

                # Update index
                index[domain].append({
                    'path': output_dir,
                    'url': policy['url'],
                    'title': policy['title'],
                    'lang': policy['lang'],
                    'tld': policy['suffix']
                })

        # Dump index.json
        with open('index.json', 'w') as output:
            json.dump(index, output, sort_keys=True, indent=4)


def main():
    setup_logging()
    args = docopt.docopt(__doc__)

    metadata_path = args['<policies_per_domain>']
    tld = args['--tld']

    with open(metadata_path, 'r') as input_metadata:
        policies_per_domain = json.load(input_metadata)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(fetch_all_policies(
            loop=loop,
            policies_per_domain=policies_per_domain,
            tld=tld
        ))


if __name__ == "__main__":
    main()
