from datetime import datetime

import pandas as pd
import streamlit as st

import data
import reports

import bot
import model

#
# DATA
#

this_month = datetime.now().month
this_year = datetime.now().year

mlp = model.read_model()
source = data.read_source()

monthly = reports.monthly_report(source)
yearly = reports.yearly_report(source)

#
# CONFIG
#

st.set_page_config(layout='wide')

#
# SIDEBAR
#

views = st.sidebar.selectbox("Views", ["Data", "Model"])

current_balance = st.empty()

if "Data" in views:
    st.sidebar.title("Filters")
    enable_year_filter = st.sidebar.checkbox("Year")
    enable_month_filter = st.sidebar.checkbox("Month")
    enable_tags_filter = st.sidebar.checkbox("Tags")

    st.sidebar.title("Functions")
    enable_tag_update = st.sidebar.checkbox("Tag Update")
    enable_duplicates = False  # st.sidebar.checkbox("Check Duplicates")
    enable_add_offset = st.sidebar.checkbox("Add Offset")
    enable_tag_replace = st.sidebar.checkbox("Tag Replace")
    enable_trends = st.sidebar.checkbox("Trends")

    #
    # FILTERS
    #

    df_filter = source.index == source.index
    delta_filter = df_filter
    df = source[df_filter]

    report = st.empty()

    left_year_column, right_month_column = st.columns(2)
    y, m, tag_filter = None, None, None

    # Time filters
    if enable_year_filter:
        y = left_year_column.selectbox("Year", yearly.columns)
        time_delta = pd.Timestamp(f"{y}")
        df_filter = df_filter & (source.date.dt.year == y)
        if enable_month_filter:
            m = right_month_column.selectbox("Month", monthly[y].columns)
            time_delta += pd.DateOffset(month=m, days=-1)
            delta_filter = delta_filter & (source.date.dt.year == time_delta.year) & (
                    source.date.dt.month == time_delta.month)
            df_filter = df_filter & (source.date.dt.month == m)
            time_delta += pd.DateOffset(months=1)
        else:
            time_delta += pd.DateOffset(year=y, days=-1)
            delta_filter = delta_filter & (source.date.dt.year == time_delta.year)
            time_delta += pd.DateOffset(years=1)

    current_balance.metric("Current Balance", source[source.date <= time_delta].amount.sum().round(2),
                           source[df_filter].amount.sum().round(2))

    # Tag filters
    if enable_tags_filter:
        tag_filter = st.multiselect("Tags", df.tags.sort_values().unique(), default=[])
        df_filter = df_filter & (source.tags.isin(tag_filter)) if tag_filter else df_filter
        delta_filter = delta_filter & (source.tags.isin(tag_filter)) if tag_filter else delta_filter

    df = source[df_filter].sort_values("date")
    delta_df = source[delta_filter].sort_values("date")

    st.metric("Filtered Balance", df.amount.sum().round(2), (df.amount.sum() - delta_df.amount.sum()).round(2))
    st.write(df)

    #
    # FUNCTIONS
    #

    # TAG UPDATE
    if enable_tag_update:
        st.header("Update a tag")
        index = st.number_input("Enter a positive index, or -1 to update tags for the above entries:", value=-1)
        if index > 0:
            source_to_update = source.loc[index]
            update_index = index
            st.write(source_to_update)

            left_tag_column, right_tag_column = st.columns(2)
            existing_tag = left_tag_column.selectbox("Select a tag for this record...", [""] + mlp.classes_.tolist())
            new_tag = right_tag_column.text_input("...or enter a new tag")
            tag = existing_tag if existing_tag else new_tag

            if tag:
                st.write("You are updating the tag(s) here to '{}'".format(tag))
                if st.button("Update Data"):
                    data.update_tag(update_index, tag, True)
                    st.write("Tag Update Complete!")
                if st.button("Re-train Model"):
                    model.build_model("updated_tags")
                    st.write("Model Re-training Complete!")

    # TAG REPLACE
    if enable_tag_replace:
        st.header("Replace a tag")

        existing_tag = st.selectbox("Select a tag to replace", [""] + mlp.classes_.tolist())
        new_tag = st.text_input("Enter a new name for this tag:")

        if new_tag:
            st.write("You are updating all uses of {} to {}, and re-training the model.".format(existing_tag, new_tag))
            if st.button("Update and Re-train"):
                data.replace_tag(existing_tag, new_tag, True)
                st.write("Tag Replacement Complete!")
                model.build_model("replaced_tags")
                st.write("Model Re-training Complete!")

    # CHECK DUPLICATES
    if enable_duplicates:
        st.header("Check for Duplicates")
        duplicates = df.duplicated(subset=data.duplicate_columns_subset, keep="first")
        st.write(df[duplicates])

        if duplicates.sum() and st.button("Drop {} Duplicates".format(duplicates.sum())):
            source.drop_duplicates(subset=data.duplicate_columns_subset, keep="first")

    # ADD OFFSET
    if enable_add_offset:
        st.header("Add Offset")

        index = st.number_input("Enter a positive index, or -1 to add an offset to it:", value=-1)
        if index > 0:
            row_to_update = source.loc[index]
            update_index = index
            st.write(row_to_update)

            offset_amount = st.number_input("Enter the amount to offset")
            offset_tag = st.selectbox("Select a tag for the offset entry", [""] + mlp.classes_.tolist())

            if offset_tag:
                st.write(f"You are updating the amount to {row_to_update.amount - offset_amount}")
                if st.button("Update Data"):
                    data.add_offset(update_index, offset_amount, offset_tag, True)
                    st.write("Offset Added!")


elif "Model" in views:
    st.header("Model")

    st.sidebar.title("Functions")
    if st.sidebar.checkbox("Process Inputs"):
        st.subheader("Process Inputs")
        inputs = bot.format_and_tag_inputs()
        # st.write(inputs)
        st.write(bot.validate_inputs(inputs, threshold=1))

        # new_inputs = data.insert_inputs(inputs)
        # # st.write(f"{new_inputs.index.shape[0]} entries to insert")
        # st.write(new_inputs)
        if st.button("Insert Inputs"):
            data.insert_inputs(inputs, write=True)
            st.write("Source data updated!!")

    if st.sidebar.checkbox("Tag Validation"):
        st.subheader("Tag Validation")
        threshold = st.slider("Threshold", 0.0, 1.0, value=0.8, step=0.05)
        df_validated = bot.validate_inputs(source, threshold=threshold)

        if "df_current_index" not in st.session_state or st.button("Run Validation"):
            st.session_state["df_to_validate"] = df_validated
            st.session_state["df_current_index"] = iter(df_validated.index)

        i = next(st.session_state.df_current_index, None)
        if i:
            st.write(f"There are {df_validated.index.shape[0]} tags to validate")
            st.write(df_validated.loc[i])

            left_tag_column, right_tag_column = st.columns(2)
            existing_tag = left_tag_column.selectbox("Select a tag for this record...", [""] + mlp.classes_.tolist())
            new_tag = right_tag_column.text_input("...or enter a new tag")
            tag = existing_tag if existing_tag else new_tag

            st.button("Skip")
            if tag:
                if st.button("Update"):
                    st.session_state.df_to_validate.loc[i, "tags"] = tag
        else:
            st.write("All tags validated")
            st.write(st.session_state.df_to_validate)
            # TODO Call data.update_tag with validated data
