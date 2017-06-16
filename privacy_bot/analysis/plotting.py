from wordcloud import WordCloud
import matplotlib.pyplot as plt


class PlotWordCloud():
    """
    Given a word frequency dictionary, it generates a word cloud
    """

    def __init__(self, word_frequency_dict):
        self.word_frequency_dict = word_frequency_dict

    @staticmethod
    def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        return "hsl(0, 0%%, %d%%)" % random.randint(5, 30)

    def plot(self):
        # TODO: Add support for saving the word cloud as image
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
