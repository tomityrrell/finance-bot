from datetime import datetime

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
source = source[source.date >= "2017-01-19"]

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

st.title('Finance Bot 6000')
st.write("Current Balance:", reports.current_balance(source))

if "Data" in views:
    st.sidebar.title("Filters")
    enable_year_filter = st.sidebar.checkbox("Year")
    enable_month_filter = st.sidebar.checkbox("Month")
    enable_tags_filter = st.sidebar.checkbox("Tags")

    st.sidebar.title("Functions")
    enable_tag_update = st.sidebar.checkbox("Tag Update")
    enable_duplicates = False #st.sidebar.checkbox("Check Duplicates")
    enable_tag_replace = st.sidebar.checkbox("Tag Replace")
    enable_trends = st.sidebar.checkbox("Trends")

    #
    # FILTERS
    #

    df_filter = source.index == source.index
    df = source[df_filter]

    report = st.empty()

    # Year and Month filters
    left_year_column, right_month_column = st.columns(2)
    if enable_year_filter:
        y = left_year_column.selectbox("Year", yearly.columns)
        df_filter = df_filter & (source.date.dt.year == y)

        enable_summary_report = st.checkbox("View full report")
        if enable_month_filter:
            m = right_month_column.selectbox("Month", monthly[y].columns)
            df_filter = df_filter & (source.date.dt.month == m)

            if enable_summary_report:
                monthly_f = monthly.loc[:, monthly.columns <= (y, m)].sort_values(by=(y, m))
                report.write(monthly_f)
        elif enable_summary_report:
            report.write(yearly.loc[:, yearly.columns <= y].sort_values(by=y))

        df = source[df_filter]

    # Tag filters
    if enable_tags_filter:
        tag_filter = st.multiselect("Tags", df.tags.sort_values().unique(), default=[])
        df_filter = df_filter & (source.tags.isin(tag_filter)) if tag_filter else df_filter

        # Display filtered data
        df = source[df_filter].sort_values("date")

    st.write(df)

    df_grouped = df.groupby("tags").sum().amount.sort_values()
    df_grouped_in = df_grouped[df_grouped > 0]
    df_grouped_out = df_grouped[df_grouped < 0]

    left_year_column.write(df_grouped_out)
    right_month_column.bar_chart(df_grouped_out)

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

        if st.button("Run Validation"):
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
            # TO DO Call data.update_tag with validated data
