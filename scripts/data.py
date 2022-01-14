import time
from typing import Any

import pandas as pd

import reports

SOURCE_PATH = "../data/source.csv"
BACKUP_PATH = "../data/backups/source"

source_columns = ["Posted Date", "Payee", "Amount", "Tags", "Notes"]
target_columns = ["date", "description", "amount", "tags", "notes", "type", "check"]
duplicate_columns_subset = target_columns[:3] + target_columns[-2:]
source_column_mappings = {source_columns[i]: target_columns[i] for i in range(len(source_columns))}


def read_source(path: str = SOURCE_PATH) -> pd.DataFrame:
    source = pd.read_csv(path)
    source.date = pd.to_datetime(source.date)

    source.fillna(value="", inplace=True)

    return source


def _write_source(source: pd.DataFrame, path: str = "../data/source.csv"):
    source.to_csv(path, index=False, float_format='%.2f')


def backup_source(event: str = "manual"):
    backup_path = "../data/backups/source/source_{}_{}.csv".format(time.time_ns(), event)
    _write_source(read_source(), backup_path)


def insert_inputs(inputs: pd.DataFrame, event: str = "insert", write: bool = False) -> pd.DataFrame:
    # add new inputs to source
    source = read_source()
    new_source = source.append(inputs, ignore_index=True)

    # remove duplicates and format
    new_source.drop_duplicates(subset=duplicate_columns_subset, keep="first", inplace=True)
    new_source = new_source.sort_values(by="date").reset_index(drop=True)

    # update source
    if write:
        backup_source(event)
        _write_source(new_source)

    return new_source


def update_tag(index: int, tag: str, write: bool = False, event: str = "update"):
    backup_source(f'{event}_tag_{tag}')

    source = read_source()
    source.loc[index, "tags"] = tag

    if write:
        _write_source(source)

    return source.loc[index]


def replace_tag(old_tag: str, new_tag: str, write: bool = False, event: str = "replace"):
    source = read_source()
    return update_tag(source.tags == old_tag, new_tag, write, event)


def add_offset(index: int, offset_amount: Any, offset_tag: str, write: bool = False):
    source = read_source()

    source.loc[index, "amount"] -= offset_amount
    offset_row = source.iloc[index].copy()
    offset_row.amount = offset_amount
    offset_row.tag = offset_tag

    source.append(offset_row, ignore_index=True)

    if write:
        _write_source(source)


