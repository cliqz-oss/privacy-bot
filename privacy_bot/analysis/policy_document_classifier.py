from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.externals import joblib

from privacy_bot.analysis.policies_snapshot_api import Policies
from privacy_bot.analysis.utils import Dataset

from time import time
from random import shuffle
import logging
import json



# Display progress logs on stdout
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


def load_data():
    tp = Policies(local_path='privacy_policies.zip')
    tn = Policies(local_path='privacy_policies_test.zip')
    tpc = [policy for policy in tp.query(lang='en')]
    tnc = [policy for policy in tn.query(lang='en')]

    # corpus = tpc + tnc
    # shuffle(corpus)

    data = []
    names = []
    for policy in tpc[0:1456]:
        data.append(policy.text)
        names.append('policy')

    for policy in tnc:
        data.append(policy.text)
        names.append('notPolicy')

    training = Dataset(data, names)
    return training


pipeline = Pipeline([('vect', CountVectorizer()),
                     ('tfidf', TfidfTransformer()),
                     ('clf', SGDClassifier())
                     ])

# used during training (ran for 10 hours)
parameters = {
    'vect__max_df': (0.5, 0.75, 1.0),
    'vect__max_features': (None, 5000, 10000, 50000),
    'vect__ngram_range': ((1, 1), (1, 2)),  # unigrams or bigrams
    'tfidf__use_idf': (True, False),
    'tfidf__norm': ('l1', 'l2'),
    'clf__alpha': (0.00001, 0.000001),
    'clf__penalty': ('l2', 'elasticnet'),
    'clf__n_iter': (10, 50, 80),
}


if __name__ == "__main__":
    training = load_data()

    # multiprocessing requires the fork to happen in a __main__ protected
    # block

    # find the best parameters for both the feature extraction and the
    # classifier
    grid_search = GridSearchCV(pipeline, parameters, n_jobs=-1, verbose=1)

    print("Performing grid search...")
    print("pipeline:", [name for name, _ in pipeline.steps])
    print("parameters:")
    print(parameters)
    t0 = time()
    grid_search.fit(training.data, training.labels)
    print("done in %0.3fs" % (time() - t0))
    print()

    print("Best score: %0.3f" % grid_search.best_score_)
    print("Best parameters set:")
    best_parameters = grid_search.best_estimator_.get_params()
    for param_name in sorted(parameters.keys()):
        print("\t%s: %r" % (param_name, best_parameters[param_name]))
    joblib.dump(grid.best_estimator_, 'best_parameters.pkl')