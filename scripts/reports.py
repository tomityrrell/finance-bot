from data import load_source


def current_balance(source):
    return source.amount.sum().round(2)


# Aggregate functions
def agg_flows(source):
    copy = source.copy()
    copy.loc["Inflow"] = (copy[copy > 0]).sum()
    copy.loc["Outflow"] = (copy[copy < 0]).sum()
    copy.loc["Netflow"] = copy.loc["Inflow"] + copy.loc["Outflow"]
    return copy


def report_formatter(source):
    copy = source.copy()

    copy = copy.sort_index(axis=1, ascending=False)
    copy = copy.droplevel(axis=1, level=0)
    copy = copy.sort_values(by=copy.columns[1], axis=0)
    copy = copy.round(2)

    return copy


# Report functions
def monthly_report(source):
    monthly = source.drop("check", axis=1).groupby(by=[source.date.dt.year, source.date.dt.month, source.tags]).sum().unstack([0, 1]).fillna(0)

    monthly = report_formatter(monthly)
    monthly = agg_flows(monthly)

    monthly.to_csv("../data/reports/monthly_summary.csv")
    return monthly


def yearly_report(source):
    yearly = source.drop("check", axis=1).groupby(by=[source.date.dt.year, source.tags]).sum().unstack(0).fillna(0)

    yearly = report_formatter(yearly)
    yearly = agg_flows(yearly)

    yearly.to_csv("../data/reports/yearly_summary.csv")
    return yearly


if __name__ == '__main__':
    source = load_source()

    monthly_report(source)
    yearly_report(source)
