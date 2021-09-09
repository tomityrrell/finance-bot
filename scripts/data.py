import time

import pandas as pd

source_columns = ["Posted Date", "Payee", "Amount", "Tags", "Notes"]
target_columns = ["date", "description", "amount", "tags", "notes", "type", "check"]
source_column_mappings = {source_columns[i]: target_columns[i] for i in range(len(source_columns))}


def load_source():
    source = pd.read_csv("../data/source.csv")
    source.date = pd.to_datetime(source.date)
    # source.amount = pd.to_numeric(source.amount).round(2)
    # source.check = pd.to_numeric(source.check, errors="coerce", downcast="float").round(2)

    source.fillna(value="", inplace=True)

    return source


def backup_source(event="manual"):
    source = pd.read_csv("../data/source.csv")
    backup_path = "../data/backups/source/source_{}_{}.csv".format(time.time_ns(), event)
    source.to_csv(backup_path, index=False, float_format='%.2f')


def write_source(new_source, event="overwrite"):
    backup_source(event)
    new_source.to_csv("../data/source.csv", index=False, float_format='%.2f')

# DO NOT USE.  DEACTIVATED
# def create_source(write=False):
#     # Read data from ~/data/numbers
#     source_data = []
#     for filepath in Path("../data/backups/numbers/Money").glob("C*.csv"):
#         source = pd.read_csv(filepath)
#         source.dropna(axis=1, inplace=True, how="all")
#         source.fillna(value="", inplace=True)
#         source["type"] = filepath.stem.split("-")[0]
#         source_data.append(source)
#
#     data = pd.concat(source_data, ignore_index=True)
#     data.rename(columns=source_column_mappings, inplace=True)
#     data = data[~data.duplicated()]
#     data["check"] = data.index
#     data.date = pd.to_datetime(data.date)
#     data.sort_values(by='date', inplace=True)
#
#     if False:
#         write_source(data, "source_creation")


def update_tag(source, index, tag, write=False):
    source.loc[index, "tags"] = tag

    if write:
        write_source(source, "update_tag_{}".format(tag))

    return source.loc[index]


def replace_tag(source, old_tag, new_tag, write=False):
    return update_tag(source, source.tags == old_tag, new_tag, write)

