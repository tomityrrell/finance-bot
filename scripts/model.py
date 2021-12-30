import time
import pickle

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.neural_network import MLPClassifier

from data import read_source


def read_model():
    with open('../model/model.pickle', 'rb') as f:
        model = pickle.load(f)

    return model


def write_model(model, path='../model/model.pickle'):
    with open(path, 'wb') as f:
        pickle.dump(model, f, pickle.HIGHEST_PROTOCOL)


def backup_model(model, event="manual"):
    backup_path = "../model/backups/model/model_{}_{}.pickle".format(time.time_ns(), event)
    write_model(model, backup_path)


def build_model(event="model_creation"):
    # Load training data
    source = read_source()

    # Filter data
    training_filter = (source.date.dt.year >= 2017)
    training_source = source[training_filter]

    # Build model pipelines
    ct = ColumnTransformer([('description', TfidfVectorizer(ngram_range=(1, 2)), "description"),
                            ('amount', StandardScaler(), ["amount"]),
                            ('type', OrdinalEncoder(), ["type"])
                            ])
    model = Pipeline([('column_trans', ct),
                      ('mlp', MLPClassifier(hidden_layer_sizes=(250, 250, 250)))])

    # Train model
    model.fit(training_source, training_source.tags)

    # Pickle and backup model
    backup_model(model, event)
    write_model(model)


if __name__ == "__main__":
    build_model()
