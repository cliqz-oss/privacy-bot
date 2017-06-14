"""
Privacy Bot - Text Classifier

Usage:
    classifier.py -p TRUE_POSITIVES  -n TRUE_NEGATIVES -e ENTITY

Options:
    -p --tp TRUE_POSITIVES        Local Path of TRUE_POSITIVES (tar file)
    -n --tn TRUE_NEGATIVES        Local Path of TRUE_NEGATIVES (tar file)
    -e --entity ENTITY            Two possible values: text, url
    -h --help                     Show help
"""


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.externals import joblib

from privacy_bot.analysis.policies_snapshot_api import Policies
from privacy_bot.analysis.utils import Dataset
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
    print(args)
    print(args['--entity'])
    labelled_dataset = Dataset.tars_to_labelled(
        true_positives_path=args['--tp'],
        true_negatives_path=args['--tn'],
        entity=args['--entity']
    )
    #TODO: training_size, testing_size into args (when > labelled data)
    training, test = labelled_dataset.training_testing(
        training_size=2500,
        testing_size=500
    )
    if args['--entity'] == 'text':
        clf = text_clf
    elif args['--entity'] == 'url':
        clf = url_clf

    clf.fit(training.data, training.labels)
    predicted = clf.predict(test.data)
    actual = test.labels

    # generating report. Precision is important
    print(classification_report(actual, predicted))

    # dump classifier
    joblib.dump(clf, 'trained_model_%s.pkl' %args['--entity'])
