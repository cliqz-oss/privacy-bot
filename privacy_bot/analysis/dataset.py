from privacy_bot.analysis.policies_snapshot_api import Policies
from sklearn.datasets.base import Bunch


def load_urls(true_positives_path, true_negatives_path, language='en'):
    return load_data(true_positives_path, true_negatives_path, entity='url', language=language)


def load_text(true_positives_path, true_negatives_path, language='en'):
    return load_data(true_positives_path, true_negatives_path, entity='text', language=language)


def load_html(true_positives_path, true_negatives_path, language='en'):
    return load_data(true_positives_path, true_negatives_path, entity='html', language=language)


def load_data(true_positives_path, true_negatives_path, entity='text', language='en'):
    def select_data(policies):
        return [
            getattr(policy, entity)
            for policy in policies.query(lang=language)
        ]

    pos = select_data(Policies.from_tar(true_positives_path))
    neg = select_data(Policies.from_tar(true_negatives_path))
    target = [1] * len(pos) + [0] * len(neg)

    return Bunch(data=pos + neg, target=target)
