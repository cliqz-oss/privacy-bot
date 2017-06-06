from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline

from privacy_bot.analysis.policies_snapshot_api import Policies
from privacy_bot.analysis.utils import Dataset

pipeline = Pipeline([('vect', CountVectorizer(
                        max_df=0.75,
                        max_features=1000,
                        ngram_range=(1, 2)
                     )),
                     ('tfidf', TfidfTransformer(
                         norm='l1',
                         use_idf=True
                     )),
                     ('clf', SGDClassifier(
                         penalty='elasticnet',
                         alpha=0.000001,
                         n_iter=50
                     ))
])

# Found best_parameters after 10 hours of training
# parameters = {
#     'vect__max_df': (0.75),
#     'vect__max_features': (10000),
#     'vect__ngram_range': ((1, 2)), # bigrams
#     'tfidf__use_idf': (True),
#     'tfidf__norm': ('l1'),
#     'clf__alpha': (0.000001),
#     'clf__penalty': ('elasticnet'),
#     'clf__n_iter': (50),
# }

tp = Policies(local_path='privacy_policies.zip')
tpc = [policy for policy in tp.query(lang='en')]

pipeline.fi
pipeline.predict(tpc[1455:])