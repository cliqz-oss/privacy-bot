"""
Privacy Bot - privacy policies finder.

Usage:
    manual_policy_labelling [options]

Options:
    -l, --language L    Choose language of policies to assess
"""

import json
import time

import docopt
from termcolor import colored

from privacy_bot.analysis.policies_snapshot_api import Policies


def setting_language(input_language):
    l = None
    if input_language is None:
        l = 'en'
    language_question = 'Is this in %s?              [Y/n]: ' % l
    privacy_question = 'Is this a privacy policy?     [Y/n]: '

    print('\n ----------------------------------------------------')
    print('To stop, type ', colored("stop", "green"), 'when asked ',
          colored(language_question, 'yellow'))
    time.sleep(3)
    return language_question, privacy_question


if __name__ == "__main__":
    args = docopt.docopt(__doc__)

    lang = args['--language']
    language_question, privacy_question = setting_language(lang)

    policies = Policies()
    trained_data = []

    for policy in policies.query(lang=lang):
        # prints 50% of policy.text for assessment
        print(policy.text[0: int(0.5 * len(policy.text))], '\n\n')
        language = input(colored(language_question, 'yellow'))

        if language.lower() == 'stop':
            break
        elif language.lower() in ['y', '']:
            label = input(colored(privacy_question, 'green'))

            if label.lower() in ['y', '']:
                trained_data.append((policy.text, 'policy'))
            elif label.lower() == 'n':
                trained_data.append((policy.text, 'notPolicy'))
        continue

    with open('labeled_policies_en.json', 'w') as fin:
        json.dump(trained_data, fin)
