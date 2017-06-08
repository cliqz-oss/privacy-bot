#! /usr/bin/env python
# -*- coding: utf-8 -*-


from abc import abstractmethod
from collections import defaultdict, namedtuple
from pathlib import Path
import os.path
import json
import logging
import zipfile
import tarfile

import requests
import tqdm


def _get_latest_release():
    """Get link of the latest policies snapshot."""
    github_api = "https://api.github.com/repos/cliqz-oss/privacy-bot/releases/latest"
    response = requests.get(github_api)
    release = response.json()

    return {
        "tag": release["tag_name"],
        "name": release["name"],
        "url": release["zipball_url"],
        "id": release["id"]
    }


Policy = namedtuple('Policy', [
    'name',
    'url',
    'html',
    'text',
    'domain',
    'lang',
    'tld'
])


class SnapshotBase:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @abstractmethod
    def open(self, path):
        raise NotImplementedError()

    @abstractmethod
    def close(self):
        raise NotImplementedError()


class ZipSnapshot(SnapshotBase):
    def __init__(self, path):
        self.zipfile = zipfile.ZipFile(path)

        # Mapping from filename to zip archive filepath
        self.file_index = {}
        files = list(self.zipfile.namelist())
        prefix = os.path.commonprefix(files)
        for filename in self.zipfile.namelist():
            self.file_index[filename[len(prefix):]] = filename

    def open(self, path):
        return self.zipfile.open(self.file_index[path])

    def close(self):
        self.zipfile.close()


class LocalSnapshot(SnapshotBase):
    def __init__(self, path):
        self.path = Path(path)

    def open(self, path):
        return (self.path / path).open()

    def close(self):
        pass


def load_from_snapshot_abstraction(snapshot):
    policies = defaultdict(list)
    domains = set()
    languages = set()
    tlds = set()

    # Load index file
    with snapshot.open('index.json') as index_file:
        index = json.load(index_file)

        # Iterate on all available domains
        for domain, policy_pages in tqdm.tqdm(index.items(), total=len(index),
                                              dynamic_ncols=True, unit='domain',
                                              desc='Loading policies'):
            domains.add(domain)

            for policy in policy_pages:
                base_path = policy['path']

                content = {}
                for extension in ['txt', 'html']:
                    with snapshot.open(base_path + '.' + extension) as content_file:
                        content[extension] = content_file.read()

                tlds.add(policy['tld'])
                languages.add(policy['lang'])

                policies[domain].append(Policy(
                    domain=domain,
                    url=policy['url'],
                    name=policy['name'],
                    html=content['html'],
                    text=content['txt'],
                    tld=policy['tld'],
                    lang=policy['lang']
                ))

    return Policies(
        policies=policies,
        domains=domains,
        tlds=tlds,
        languages=languages
    )


class Policies:
    def __init__(self, policies, tlds, domains, languages):
        self.policies = policies
        self.domains = domains
        self.languages = languages
        self.tlds = tlds

    @staticmethod
    def from_remote():
        print('Fetch information about latest release...')
        latest_release = _get_latest_release()

        print("Get Latest Release")
        print("-" * 80)
        print("Name:", latest_release["name"])
        print("Tag:", latest_release["tag"])
        print("Url:", latest_release["url"])
        print("-" * 80)

        # Check if there is a cached version already
        cached_path = Path('/tmp', 'privacy-bot_' + str(latest_release["id"]))

        # Fetch and cache content locally
        if not cached_path.exists():
            # Fetch the content of the archive
            response = requests.get(
                latest_release["url"],
                stream=False,
                allow_redirects=True,
            )
            content = response.content

            # Cache fetched content
            with cached_path.open('wb') as output:
                output.write(content)

        with ZipSnapshot(str(cached_path)) as snapshot:
            return load_from_snapshot_abstraction(snapshot)

    @staticmethod
    def from_tar(path):
        assert path.endswith('.tar.bz2'), 'from_tar excepts a tar.bz2 archive'
        cached_path = Path('/tmp', 'privacy-bot_policies_' + path.split('.', 1)[0])

        # Extract archive is necessary
        if not cached_path.exists():
            with tarfile.open(path, mode='r:bz2') as archive:
                print('Extract archive into', cached_path)
                archive.extractall(str(cached_path))

        # Load policies from extracted archive
        return Policies.from_path(cached_path)

    @staticmethod
    def from_zip(path):
        with ZipSnapshot(path) as snapshot:
            return load_from_snapshot_abstraction(snapshot)

    @staticmethod
    def from_path(path):
        print("Load privacy policies from", path)
        with LocalSnapshot(path) as snapshot:
            return load_from_snapshot_abstraction(snapshot)


    def __iter__(self):
        for domain, policies in self.policies.items():
            for policy in policies:
                yield policy

    def query(self, domain=None, lang=None, tld=None):
        for policy in self:
            # Filter on domain
            if domain and policy.domain != domain:
                continue

            # Filter on language
            if lang and policy.lang != lang:
                continue

            # Filter on tld
            if tld and policy.tld != tld:
                continue

            yield policy


def example():
    logging.basicConfig(level=logging.INFO)
    policies = Policies.from_remote()

    # Iterate on all policies
    for policy in policies:
        print(policies)

    print('Size', len(list(policies)))

    # Check available domains, tlds, languages
    print(policies.domains)
    print(policies.tlds)
    print(policies.languages)

    # Query policy by: tld, domain, lang
    for policy in policies.query(lang='de'):
        print(policy.domain)


if __name__ == "__main__":
    example()

