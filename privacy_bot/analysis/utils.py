from wordcloud import WordCloud
import matplotlib.pyplot as plt

from privacy_bot.analysis.policies_snapshot_api import Policies

import random
import json


class Dataset():
    def __init__(self, data, names):
        self.data = data
        self.names = names
        self.labels = [1 if name == 'policy' else 0 for name in self.names]
        self.size = len(self.data)

    def take(self, category, n=None):
        if n is None:
            n = self.size
        take_data = []
        take_names = []

        for text, name in zip(self.data, self.names):
            if len(take_data) < n:
                if name == category:
                    take_data.append(text)
                    take_names.append(name)
        return Dataset(data=take_data, names=take_names)

    @staticmethod
    def from_trained(path):
        data = []
        names = []
        with open(path, 'r') as fin:
            data_name_tuple = json.load(fin)
            for d, n in data_name_tuple:
                data.append(d)
                names.append(n)

        return Dataset(data=data, names=names)

    @staticmethod
    def tars_to_labelled(true_positives_path, true_negatives_path, language='en'):
        data = []
        names = []

        tp = Policies.from_tar(true_positives_path)
        tn = Policies.from_tar(true_negatives_path)

        for policy in tp.query(lang=language):
            data.append(policy.text)
            names.append('policy')

        for policy in tn.query(lang=language):
            data.append(policy.text)
            names.append('not_policy')

        return Dataset(data=data, names=names)

    def shuffle(self):
        tups = []
        for d, n in zip(self.data, self.names):
            tups.append((d, n))
        random.shuffle(tups)
        data = []
        names = []
        for d, n in tups:
            data.append(d)
            names.append(n)

        return Dataset(data=data, names=names)

    def training_testing(self, training_size, testing_size):

        true_positives = self.take(category='policy')
        true_negatives = self.take(category='not_policy')

        # equal tp and tn in training
        training_tp_size = training_size // 2
        training_tn_size = training_size - training_tp_size
        assert abs(training_tp_size - training_tn_size) <= 1

        # training dataset
        training_data = [true_positives.data[i] for i in range(training_tp_size)] +\
                        [true_negatives.data[i] for i in range(training_tn_size)]

        training_names = [true_positives.names[i] for i in range(training_tp_size)] +\
                         [true_negatives.names[i] for i in range(training_tn_size)]

        # training dataset
        testing_tp_size = testing_size // 2
        testing_tn_size = testing_size - testing_tp_size

        # testing dataset
        testing_data = [true_positives.data[training_tp_size:][i] for i in range(testing_tp_size)] +\
                       [true_negatives.data[training_tn_size:][i] for i in range(testing_tn_size)]

        testing_names = [true_positives.names[training_tp_size:][i] for i in range(testing_tp_size)] +\
                        [true_negatives.names[training_tn_size:][i] for i in range(testing_tn_size)]
        
        return (Dataset(data=training_data, names=training_names).shuffle(),
                Dataset(data=testing_data, names=testing_names).shuffle()
                )


class PlotWordCloud():
    def __init__(self, word_frequency_dict):
        self.word_frequency_dict = word_frequency_dict

    @staticmethod
    def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        return "hsl(0, 0%%, %d%%)" % random.randint(5, 30)

    def plot(self):
        wcloud = WordCloud(
            width=1200,
            height=800,
            background_color='#fefefe',
            color_func=self.grey_color_func
        ).generate_from_frequencies(frequencies=self.word_frequency_dict)

        plt.figure()
        plt.imshow(wcloud, interpolation="bilinear")
        plt.axis("off")
        plt.show()
