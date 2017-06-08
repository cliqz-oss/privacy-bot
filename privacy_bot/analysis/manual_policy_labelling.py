"""
Privacy Bot - Manual policy classification.

Usage:
    manual_policy_labelling.py --policies FILE [--language LANG]

Options:
    -l --language      Choose language of policies to assess
    -p --policies      Local Path of compressed policies file
    -h --help          Show help
"""

import json
import time

import docopt
from termcolor import colored

from privacy_bot.analysis.policies_snapshot_api import Policies


VERTICAL_SPACE = '\n\n'


def colorize_phrase(text, phrase):
    tokenized = text.split(phrase)
    return colored(phrase, 'grey', 'on_yellow').join(tokenized)


def setting_language(lang):
    language_question = 'Is this in %s?                [Y/n]: ' % lang

    privacy_question =  'Is this a privacy policy?     [Y/n]: '

    print(VERTICAL_SPACE)
    print('-' * 67)
    print('To stop, type', colored('stop', 'grey', 'on_yellow'), 'when asked ',
          colored(language_question, 'yellow'))
    print(VERTICAL_SPACE)
    print('-' * 67)

    time.sleep(3)
    return language_question, privacy_question


if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    lang = args['LANG'] if args['--language'] else 'en'
    local_path = args['FILE']

    language_question, privacy_question = setting_language(lang)

    policies = Policies.from_tar(local_path)
    trained_data = []

    for policy in policies.query(lang=lang):
        # prints 50% of policy.text for assessment
        print(
            colorize_phrase(policy.text[0: int(0.5 * len(policy.text))],
                            'Privacy Policy'),
            VERTICAL_SPACE
        )
        language = input(colored(language_question, 'yellow'))

        if language.lower() == 'stop':
            break
        elif language.lower() in ['y', '']:
            label = input(colored(privacy_question, 'green'))

            if label.lower() in ['y', '']:
                trained_data.append((policy.text, 'policy'))
            elif label.lower() == 'n':
                trained_data.append((policy.text, 'not_policy'))
        continue

    with open('labeled_policies_%s.json' % lang, 'w') as fout:
        json.dump(trained_data, fout)
