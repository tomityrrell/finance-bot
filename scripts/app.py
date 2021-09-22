from datetime import datetime

import streamlit as st

import data
from data import target_columns
import reports

# import bot
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

st.sidebar.title("Filters")
enable_year_filter = st.sidebar.checkbox("Year")
enable_month_filter = st.sidebar.checkbox("Month")
enable_tags_filter = st.sidebar.checkbox("Tags")

st.sidebar.title("Functions")
enable_process_inputs = st.sidebar.checkbox("Process Inputs")
enable_tag_update = st.sidebar.checkbox("Tag Update")
enable_duplicates = st.sidebar.checkbox("Check Duplicates")
enable_tag_replace = st.sidebar.checkbox("Tag Replace")

st.title('Finance Bot 6000')
st.write("Current Balance:", reports.current_balance(source))

#
# FILTERS
#

if "Data" in views:
    df_filter = source.index == source.index
    df = source[df_filter]

    report = st.empty()
    plot = st.empty()

    # Year and Month filters
    left_year_column, right_month_column = st.beta_columns(2)
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
                # plot.line_chart(monthly_f[y].loc["Netflow"])
        elif enable_summary_report:
            report.write(yearly.loc[:, yearly.columns <= y].sort_values(by=y))
            # plot.line_chart(yearly.loc["Netflow"])

        df = source[df_filter]

    # Tag filters
    if enable_tags_filter:
        tag_filter = st.multiselect("Tags", df.tags.sort_values().unique(), default=[])
        df_filter = df_filter & (source.tags.isin(tag_filter)) if tag_filter else df_filter

        # Display filtered data
        df = source[df_filter].sort_values("date")

    st.write(df)

    #
    # FUNCTIONS
    #

    # PROCESS INPUTS
    if enable_process_inputs:
        st.write("Process Inputs function not yet implemented")
        # bot.process_inputs(interactive=True)

    # TAG UPDATE
    if enable_tag_update:
        st.header("Update a tag")
        index = st.number_input("Enter a positive index, or -1 to update tags for the above entries:", value=-1)
        if index > 0:
            source_to_update = source.iloc[index]
            update_index = index
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

    # CHECK DUPLICATES
    if enable_duplicates:
        st.header("Check for Duplicates")
        duplicates = df.duplicated(subset=target_columns[:3] + target_columns[-2:], keep="first")
        st.write(df[duplicates])

        if duplicates.sum() and st.button("Drop {} Duplicates".format(duplicates.sum())):
            source.drop_duplicates(subset=target_columns[:3] + target_columns[-2:], keep="first", inplace=True)
            data.write_source(source, event="drop_duplicates")

    # TAG REPLACE
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
