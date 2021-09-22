from pathlib import Path

import pandas as pd

from data import target_columns, read_source, write_source
from reports import *

from model import read_model, build_model


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
def tag_inputs():
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

    # Concatenate inputs
    output = pd.concat(inputs, ignore_index=True)

    # Remove duplicates
    output.drop_duplicates(subset=target_columns[:3] + target_columns[-2:], keep="first", inplace=True)

    # Add Tags, Notes columns
    output["tags"] = ""
    output["notes"] = ""

    # Formatting
    output = output[target_columns]
    output.fillna(value="", inplace=True)
    output.date = pd.to_datetime(output.date)
    output.check = output.check.astype("float64")
    output.sort_values(by="date", inplace=True)
    output.reset_index(drop=True, inplace=True)

    # Predict tags on new inputs
    model = read_model()
    output["tags"] = model.predict(output)

    return output


def review_tags(output, threshold=0.8, interactive=False):
    model = read_model()

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


def process_inputs(interactive=False, event="insert"):
    # tag inputs and validate if interactive=True
    raw_output = tag_inputs()
    low_prob_index, revised_output = review_tags(raw_output, interactive=interactive)

    # add new inputs to source
    source = read_source()
    combined = source.append(revised_output, ignore_index=True)

    # remove duplicates
    combined.drop_duplicates(subset=target_columns[:3] + target_columns[-2:], keep="first", inplace=True)

    new_source = combined.sort_values(by="date").reset_index(drop=True)

    # update source and generate reports
    write_source(new_source, event)
    monthly_report(new_source)
    yearly_report(new_source)

    # retrain model with new inputs if interactive=True
    if interactive and len(low_prob_index) > 0:
        build_model("new_validated_inputs")


if __name__ == "__main__":
    process_inputs(True)
