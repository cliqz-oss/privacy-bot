#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""
Privacy Bot - privacy policies fetcher.

Usage:
    fetch_policies [options] <policies_per_domain>
"""

from collections import defaultdict
import concurrent.futures as futures
import json
import os.path

import tldextract
import docopt
import langdetect
from readability.readability import Document

from privacy_bot.fetcher import fetch


KEYWORDS = ['privacy', 'datenschutz',
            'Конфиденциальность', 'Приватность', 'тайность',
            '隐私', '隱私', 'プライバシー', 'confidential',
            'mentions-legales']


def fetch_privacy_policy(policy_url):
    print('fetch_privacy_policy', policy_url)

    # Extract domain
    ext = tldextract.extract(policy_url)
    domain = ext.domain
    suffix = ext.suffix
    registered_domain = ext.registered_domain
    print('domain', domain)

    # Fetch policy page
    print('Fetch policy', policy_url)
    content = fetch(policy_url)

    if not content:
        return

    lowered = content.lower()
    # if not any(keyword in KEYWORDS for keyword in lowered.split()):
    #     print('No keyword found')
    #     return
    if len(lowered) < 1600:
        print('Too short:', len(content))
        return

    # Extract content
    readability = Document(content)
    title = readability.short_title()
    clean_content = readability.summary()
    lang = langdetect.detect(clean_content)

    return {
        "raw_content": content,
        "clean_content": clean_content,
        "lang": lang,
        "title": title,
        "url": policy_url,
        "suffix": suffix,
        "registered_domain": registered_domain
    }



def fetch_policies_from_domain(policy_metadata):
    """Given metadata on a domain, fetch the privacy policies. """
    policies = []

    # Fetch each privacy policy for a given domain
    for url in policy_metadata['privacy_policies']:
        policy = fetch_privacy_policy(
            policy_url=url
        )

        if policy:
            policies.append(policy)

    return policies


def main():
    args = docopt.docopt(__doc__)
    metadata_path = args['<policies_per_domain>']

    with open(metadata_path, 'r') as input_metadata:
        policies_per_domain = json.load(input_metadata)
        with futures.ThreadPoolExecutor() as pool:
            policies = pool.map(fetch_policies_from_domain,
                                policies_per_domain.values())
            index = defaultdict(list)

            # Create index.json and persist policies on-disk
            for domain, domain_policies in zip(policies_per_domain, policies):
                for policy in domain_policies:
                    output_dir = os.path.join(
                        'privacy_policies',
                        domain,
                        policy["lang"] + '_' + policy["registered_domain"])

                    # Create directory if it does not yet exist
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    # Output raw html
                    with open(os.path.join(output_dir, 'policy.raw.html'), 'w') as output:
                        output.write(policy["raw_content"])

                    # Output cleaned html
                    with open(os.path.join(output_dir, 'policy.html'), 'wb') as output:
                        output.write(policy["clean_content"].encode('utf-8'))

                    # TODO - output a markdown version to display on github

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


if __name__ == "__main__":
    main()
