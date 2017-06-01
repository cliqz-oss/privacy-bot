#! /usr/bin/env python
# -*- coding: utf-8 -*-


from collections import defaultdict, namedtuple
from pathlib import Path
import io
import json
import logging
import zipfile

import requests


def _get_latest_release():
    """Get link of the latest policies snapshot."""
    github_api = "https://api.github.com/repos/cliqz-oss/privacy-bot/releases/latest"
    response = requests.get(github_api)
    release = response.json()

    return {
        "tag": release["tag_name"],
        "name": release["name"],
        "url": release["zipball_url"]
    }


Policy = namedtuple('Policy', [
    'html',
    'text',
    'domain',
    'lang',
    'tld'
])


class Policies:
    def __init__(self):
        latest_release = _get_latest_release()
        print("Fetch Latest Release")
        print("-" * 80)
        print("Name:", latest_release["name"])
        print("Tag:", latest_release["tag"])
        print("Url:", latest_release["url"])
        print("-" * 80)

        # Fetch the content of the archive
        response = requests.get(
            latest_release["url"],
            stream=True,
            allow_redirects=True,
        )

        self.policies = defaultdict(dict)

        self.domains = set()
        self.languages = set()
        self.tlds = set()

        print("Load archive")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            # Mapping from filename to zip archive filepath
            file_index = {}
            for filename in archive.namelist():
                path = Path(filename)
                file_index['/'.join(path.parts[1:])] = filename

            # Load index file
            with archive.open(file_index['index.json']) as index_file:
                content = index_file.read().decode('utf-8')
                index = json.loads(content)

                # Iterate on all available domains
                for domain, policy_pages in index.items():
                    self.domains.add(domain)

                    for policy in policy_pages:
                        base_path = file_index[policy['path']]

                        with archive.open(base_path + 'policy.html') as policy_file:
                            text = policy_file.read().decode('utf-8')

                        with archive.open(base_path + 'policy.raw.html') as policy_file:
                            html = policy_file.read().decode('utf-8')

                        self.tlds.add(policy['tld'])
                        self.languages.add(policy['lang'])

                        self.policies[domain] = Policy(
                            html=html,
                            text=text,
                            domain=domain,
                            tld=policy['tld'],
                            lang=policy['lang']
                        )

    def __contains__(self, domain):
        return domain in self.policies

    def __iter__(self):
        return iter(self.policies.values())

    def query(self, domain=None, lang=None, tld=None):
        for policy in self:
            # Filter on domain
            if domain:
                # Full domain
                if domain != policy.domain:
                    continue
                # Domain without tld
                if domain != policy.domain[:-(len(policy.tld) + 1)]:
                    continue

            # Filter on language
            if lang and policy.lang != lang:
                continue

            # Filter on tld
            if tld and policy.tld != tld:
                continue

            yield policy

    def __getitem__(self, domain):
        return self.policies[domain]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    policies = Policies()

    # Iterate on all policies
    for policy in policies:
        print(policies)

    # Check available domains, tlds, languages
    print(policies.domains)
    print(policies.tlds)
    print(policies.languages)

    # Access a specific policy
    print('google.de' in policies)
    print(policies['google.de'])

    # Query policy by: tld, domain, lang
    for policy in policies.query(lang='de'):
        print(policy.domain)
