from datetime import datetime

import pandas as pd
import streamlit as st

import data
from data import target_columns
import reports

# import bot
import model

st.title('Finance Bot 6000')

this_month = datetime.now().month
this_year = datetime.now().year

mlp = model.load_model()
source = data.load_source()
source = source[source.date >= "2017-01-19"]
# source = source.append({
#     "date": pd.Timestamp("2017-01-19"),
#     "description":  "offset to match BoA",
#     "amount":  1007.81,
#     "tags": "Income",
#     "notes": "",
#     "type": "Checking",
#     "check": -1
# }, ignore_index=True)


monthly = reports.monthly_report(source)
yearly = reports.yearly_report(source)

st.write("Current Balance:", reports.current_balance(source))

st.sidebar.title("Filters")
enable_year_filter = st.sidebar.checkbox("Year")
enable_month_filter = st.sidebar.checkbox("Month")

left_dd_column, right_dd_column = st.beta_columns(2)

df = None
df_filter = source.index == source.index

# Year and Month filters
if enable_year_filter:
    y = left_dd_column.selectbox("Year", yearly.columns)
    df_filter = df_filter & (source.date.dt.year == y)

    if enable_month_filter:
        m = right_dd_column.selectbox("Month", monthly[y].columns)
        df_filter = df_filter & (source.date.dt.month == m)

df = source[df_filter]
# st.bar_chart(df.groupby("tags").sum().amount.sort_values())
summary = df.groupby("tags").sum().amount.sort_values()

st.write(summary)

# Tag filters
enable_tags_filter = st.sidebar.checkbox("Tags")
if enable_tags_filter:
    tag_filter = st.multiselect("Tags", source[df_filter].tags.sort_values().unique())
    df_filter = df_filter & (source.tags.isin(tag_filter))

# Display filtered data
df = source[df_filter].sort_values("date")
st.write("Total:", df.amount.sum().round(2))
st.write(df)
# st.write("Tag Total:", df.amount.sum().round(2))

#
# FUNCTIONS
#

st.sidebar.title("Functions")

enable_process_inputs = st.sidebar.checkbox("Process Inputs")
if enable_process_inputs:
    st.write("Process Inputs function not yet implemented")
    # bot.process_inputs(interactive=True)

enable_tag_update = st.sidebar.checkbox("Tag Update")
if enable_tag_update:
    st.header("Update a tag")
    index = st.number_input("Enter a positive index, or -1 to update tags for the above entries:", value=-1)
    if index:
        source_to_update = None
        update_index = None
        if index > 0:
            source_to_update = source.iloc[index]
            update_index = index
        elif index == -1:
            source_to_update = source[df_filter]
            update_index = source_to_update.index
        st.write(source_to_update)

        left_tag_column, right_tag_column = st.beta_columns(2)
        existing_tag = left_tag_column.selectbox("Select a tag for this record...", [""] + mlp.classes_.tolist())
        new_tag = right_tag_column.text_input("...or enter a new tag")
        tag = existing_tag if existing_tag else new_tag

        if tag:
            st.write("You are updating the tag(s) here to '{}'".format(tag))
            if st.button("Update Data"):
                data.update_tag(source, update_index, tag, True)
                st.write("Tag Update Complete!")
            if st.button("Re-train Model"):
                model.build_model("updated_tags")
                st.write("Model Re-training Complete!")

enable_duplicates = st.sidebar.checkbox("Check Duplicates")
if enable_duplicates:
    st.header("Check for Duplicates")
    duplicates = df.duplicated(subset=target_columns[:3] + target_columns[-2:], keep="first")
    st.write(df[duplicates])

    if duplicates.sum() and st.button("Drop {} Duplicates".format(duplicates.sum())):
        source.drop_duplicates(subset=target_columns[:3] + target_columns[-2:], keep="first", inplace=True)
        data.write_source(source, event="drop_duplicates")

enable_tag_replace = st.sidebar.checkbox("Tag Replace")
if enable_tag_replace:
    st.header("Replace a tag")

    existing_tag = st.selectbox("Select a tag to replace", [""] + mlp.classes_.tolist())
    new_tag = st.text_input("Enter a new name for this tag:")

    if new_tag:
        st.write("You are updating all uses of {} to {}, and re-training the model.".format(existing_tag, new_tag))
        if st.button("Update and Re-train"):
            data.replace_tag(source, existing_tag, new_tag, True)
            st.write("Tag Replacement Complete!")
            model.build_model("replaced_tags")
            st.write("Model Re-training Complete!")
