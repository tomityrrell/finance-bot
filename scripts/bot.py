from pathlib import Path

import pandas as pd

import data
import model

# configs for data sources
checking = {"type": "Checking",
            "source": "Checking-Table 1.csv",
            "files": list(filter(lambda path: "stmt" in path.stem and path.suffix == ".csv", Path("../input").glob("*.csv"))),
            "columns": ["Date", "Description", "Amount", "Running Bal."],
            "target_columns": ["date", "description", "amount", "check"]
            }

credit = {"type": "Cash Rewards",
          "source": "Cash Rewards-Table 1.csv",
          "files": list(filter(lambda path: "_8522" in path.stem and path.suffix == ".csv", Path("../input").glob("*.csv"))),
          "columns": ["Posted Date", "Reference Number", "Payee", "Address", "Amount"],
          "target_columns": ["date", "check", "description", "address", "amount"]
          }

target_dicts = [checking, credit]


# TO DO:  Generalize data loading/configs into class(es)
def read_inputs():
    inputs = []
    for d in target_dicts:
        # Process files by type
        for filepath in d["files"]:
            # Open file to be tagged, process
            target = None

            if d["type"] == "Checking":
                target = pd.read_csv(filepath, header=5)
                target.dropna(axis=0, inplace=True, how="any")

            elif d["type"] == "Cash Rewards":
                target = pd.read_csv(filepath)
                target.drop("Address", axis=1, inplace=True)

            target.rename(columns={d["columns"][i]: d["target_columns"][i] for i in range(len(d["columns"]))}, inplace=True)
            target["type"] = d["type"]

            inputs.append(target)

    return inputs


def format_and_tag_inputs():
    inputs = read_inputs()

    # Concatenate inputs
    input_df = pd.concat(inputs, ignore_index=True)

    # Add Tags, Notes columns
    input_df["tags"] = ""
    input_df["notes"] = ""

    # Formatting
    input_df = input_df[data.target_columns]

    input_df.date = pd.to_datetime(input_df.date)
    input_df.fillna(value="", inplace=True)
    input_df.check = input_df.check.astype("float64")

    input_df.sort_values(by="date", inplace=True)
    input_df.reset_index(drop=True, inplace=True)

    # Remove duplicates
    input_df.drop_duplicates(subset=data.duplicate_columns_subset, keep="first", inplace=True)

    # Predict tags on new inputs
    tagger = model.read_model()
    input_df["tags"] = tagger.predict(input_df)

    return input_df


def validate_inputs(input_df, threshold=0.8):
    # Load model
    tagger = model.read_model()

    # get tags from model
    tags = tagger.classes_

    # compute and sort model probabilities
    probs = tagger.predict_proba(input_df)

    # identify trans/tags with low confidence
    low_prob_index = input_df.index[probs.max(axis=1) < threshold]

    # find max probability and top 3 tags for each low prob transaction
    low_prob_columns = probs[input_df.index.isin(low_prob_index)].argsort(axis=1)
    low_probs = probs[input_df.index.isin(low_prob_index), low_prob_columns[:, -1]]
    low_prob_tags = tags[low_prob_columns[:, -3:]]

    # add validations to trans_to_review df
    trans_to_review = input_df.loc[input_df.index.isin(low_prob_index)].copy()
    trans_to_review["tags_probability"] = low_probs
    trans_to_review["tags_suggested"] = [l[::-1] for l in low_prob_tags]
    trans_to_review.sort_values(by="tags_probability")
    # trans_to_review = trans_to_review[trans_to_review.columns.sort_values()]

    # # review outliers with user
    # if interactive:
    #     print("Interactive Mode")
    #
    #     n = len(low_prob_index)
    #     if n == 0:
    #         print("No low probability labels found")
    #     else:
    #         print("{} tags to review:\n".format(n))
    #
    #         for i in range(n):
    #             print("Probability {}% transaction:".format(low_probs[i]*100))
    #             print(trans_to_review.iloc[i])
    #             print("Suggestions:  ", low_prob_tags[i][::-1])
    #
    #             user_input = input_df("Press return to confirm or enter a new tag for the above transaction...\n")
    #             if user_input:
    #                 validated_input.loc[low_prob_index[i], "tags"] = user_input
    # # or leave uncertain tags blank
    # else:
    #     print("Non-interactive Mode")
    #     validated_input.loc[low_prob_index, "tags"] = ""

    # return validated data
    return trans_to_review


if __name__ == "__main__":
    data.insert_inputs(format_and_tag_inputs())
