from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.externals import joblib

from privacy_bot.analysis.policies_snapshot_api import Policies
from privacy_bot.analysis.utils import Dataset


#TODO: Run again the exhaustive parameters search using gridsearch
clf = Pipeline([('tfidf', TfidfVectorizer(
                    norm='l1',
                    use_idf=True
                )),
                ('clf', SGDClassifier(
                    penalty='elasticnet',
                    alpha=0.000001,
                    n_iter=50
                ))
])

if __name__ == "__main__":
    labelled_dataset = Dataset.tars_to_labelled(
        true_positives_path='privacy_policy_positive.tar.bz2',
        true_negatives_path='privacy_policy_negative.tar.bz2'
    )
    
    training, test = labelled_dataset.training_testing(
        training_size=2500,
        testing_size=500
    )

    clf.fit(training.data, training.labels)

    predicted = clf.predict(test.data)
    actual = test.labels

    # generating report. Precision is important
    print(classification_report(actual, predicted))

    # dump classifier
    joblib.dump(clf, 'trained_model.pkl')
