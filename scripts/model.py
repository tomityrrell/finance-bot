import time
import pickle

import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.neural_network import MLPClassifier

from data import load_source


def load_model():
    with open('../model/model.pickle', 'rb') as f:
        model = pickle.load(f)

    return model


def backup_model(model, event="manual"):
    with open("../model/backups/model/model_{}_{}.pickle".format(time.time_ns(), event), 'wb') as f:
        pickle.dump(model, f, pickle.HIGHEST_PROTOCOL)


def build_model(event="model_creation", ):
    source = load_source()

    # Select filter for training data
    filter = (source.date.dt.year >= 2019)
    training_source = source[filter]

    # Create and fit model
    ct = ColumnTransformer([('description', TfidfVectorizer(ngram_range=(1, 2)), "description"),
                            ('amount', StandardScaler(), ["amount"]),
                            ('type', OrdinalEncoder(), ["type"])
                            ])
    model = Pipeline([('column_trans', ct),
                      ('mlp', MLPClassifier(hidden_layer_sizes=(250, 250)))])

    model.fit(training_source, training_source.tags)

    # Pickle and backup model
    with open('../model/model.pickle', 'wb') as f:
        pickle.dump(model, f, pickle.HIGHEST_PROTOCOL)

    backup_model(model, event)


def review_tags(output, threshold=0.8, interactive=False):
    model = load_model()

    # get tags from model
    tags = model.classes_

    # compute and sort model probabilities
    probs = model.predict_proba(output)

    # identify trans/tags with low confidence
    low_prob_index = output.index[probs.max(axis=1) < threshold]
    trans_to_review = output.iloc[low_prob_index]

    low_prob_columns = probs[low_prob_index].argsort(axis=1)

    # find max probability and top 3 tags for each low prob transaction
    low_probs = probs[low_prob_index, low_prob_columns[:, -1]]
    low_prob_tags = tags[low_prob_columns[:, -3:]]

    revised_output = output.copy()
    # review outliers with user
    if interactive:
        print("Interactive Mode")

        n = len(low_prob_index)
        if n == 0:
            print("No low probability labels found")
        else:
            print("{} tags to review:\n".format(n))

        for i in range(n):
            print("Probability {}% transaction:".format(np.round(low_probs[i]*100, 4)))
            print(trans_to_review.iloc[i])
            print("Suggestions:  ", low_prob_tags[i][::-1])

            user_input = input("Press return to confirm or enter a new tag for the above transaction...\n")
            if user_input:
                revised_output.loc[low_prob_index[i], "tags"] = user_input
    # or leave uncertain tags blank
    else:
        print("Non-interactive Mode")
        revised_output.loc[low_prob_index, "tags"] = ""

    # return corrected data
    return low_prob_index, revised_output


if __name__ == "__main__":
    build_model()
