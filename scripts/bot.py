from pathlib import Path

import pandas as pd

from data import target_columns, load_source, write_source
from reports import *

from model import load_model, build_model, review_tags


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
    model = load_model()
    output["tags"] = model.predict(output)

    return output


def process_inputs(interactive=False, event="insert"):
    # tag inputs and validate if interactive=True
    raw_output = tag_inputs()
    low_prob_index, revised_output = review_tags(raw_output, interactive=interactive)

    # add new inputs to source
    source = load_source()
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
