from wordcloud import WordCloud
import random
import matplotlib.pyplot as plt


class Dataset():
    def __init__(self, data, names):
        self.data = data
        self.names = names
        self.labels = [1 if name == 'policy' else 0 for name in self.names]

    def data(self):
        return self.data

    def labels(self):
        return self.labels

    def names(self):
        return self.labels


def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return "hsl(0, 0%%, %d%%)" % random.randint(5, 30)


def wordcloud_from_dict(word_frequency_dict):
    wcloud = WordCloud(
        width=1200,
        height=800,
        background_color='#fefefe',
        color_func=grey_color_func
    ).generate_from_frequencies(frequencies=word_frequency_dict)

    plt.figure()
    plt.imshow(wcloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()
