import time

import pandas as pd

import reports

SOURCE_PATH = "../data/source.csv"
BACKUP_PATH = "../data/backups/source"

source_columns = ["Posted Date", "Payee", "Amount", "Tags", "Notes"]
target_columns = ["date", "description", "amount", "tags", "notes", "type", "check"]
duplicate_columns_subset = target_columns[:3] + target_columns[-2:]
source_column_mappings = {source_columns[i]: target_columns[i] for i in range(len(source_columns))}


def read_source():
    source = pd.read_csv("../data/source.csv")
    source.date = pd.to_datetime(source.date)

    source.fillna(value="", inplace=True)

    return source


def write_source(source, path="../data/source.csv"):
    source.to_csv(path, index=False, float_format='%.2f')


def backup_source(source, event="manual"):
    backup_path = "../data/backups/source/source_{}_{}.csv".format(time.time_ns(), event)
    write_source(source, backup_path)


def insert_inputs(inputs, event="insert", write=False):
    # add new inputs to source
    source = read_source()
    new_source = source.append(inputs, ignore_index=True)

    # remove duplicates and format
    new_source.drop_duplicates(subset=duplicate_columns_subset, keep="first", inplace=True)
    new_source = new_source.sort_values(by="date").reset_index(drop=True)

    # update source
    if write:
        backup_source(source, "insert")
        write_source(new_source, event)

    return new_source


def update_tag(source, index, tag, write=False, event="update"):
    backup_source(source, f'{event}_tag_{tag}')
    source.loc[index, "tags"] = tag

    if write:
        write_source(source)

    return source.loc[index]


def replace_tag(source, old_tag, new_tag, write=False, event="replace"):
    return update_tag(source, source.tags == old_tag, new_tag, write, event)
