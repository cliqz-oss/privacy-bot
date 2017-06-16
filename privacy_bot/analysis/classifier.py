"""
Privacy Bot - Text Classifier

Usage:
    classifier.py <true_positives>  <true_negatives>  (--url | --text)

Options:
    <true_positives>    Documents that are privacy policies (tar file)
    <true_negatives>    Documents that are NOT privacy policies (tar file)
    -h --help           Show help
"""


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import precision_score, make_scorer
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np

from privacy_bot.analysis.policies_snapshot_api import Policies
from privacy_bot.analysis import dataset
from docopt import docopt


#TODO: Run again the exhaustive parameters search using gridsearch
text_clf = Pipeline([('tfidf', TfidfVectorizer(
                        norm='l1',
                        use_idf=True
                    )),
                    ('clf', SGDClassifier(
                        penalty='elasticnet',
                        alpha=0.000001,
                        n_iter=50
                    ))
])
url_clf = Pipeline([('tfidf', TfidfVectorizer(
                        analyzer='char',
                        ngram_range=(3, 5)
                    )),
                    ('clf', SGDClassifier())
])


if __name__ == "__main__":
    args = docopt(__doc__)

    tp_path = args['<true_positives>']
    tn_path = args['<true_negatives>']

    if args['--url']:
        X = dataset.load_urls(tp_path, tn_path)
        clf = url_clf
    elif args['--text']:
        X = dataset.load_text(tp_path, tn_path)
        clf = text_clf

    # Testing Precision with 10 folds
    cv = StratifiedKFold(10)
    scores = cross_val_score(clf, X.data, X.target, cv=cv, scoring=make_scorer(precision_score))

    print("Precision: ", np.mean(scores))
