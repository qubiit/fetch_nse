import requests
import pandas as pd
from pandas import json_normalize
from dash import Dash, dash_table

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
    "Referer": "https://www.nseindia.com/market-data/live-equity-market",
}

def fetch_nse(url, headers):
    try:
        json_data = requests.get(url, headers=headers).json()
    except ValueError:
        s =requests.Session()
        json_data = s.get("http://nseindia.com",headers=headers)
        json_data = s.get(url ,headers=headers).json()
    return json_data

#fetching live option data from NSE https://www.nseindia.com/option-chain
url = r"https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_opt"
json_data = fetch_nse(url=url, headers=headers)
df = json_normalize(json_data['data'], max_level=0)

#pre-processing
df['expiryDate'] = pd.to_datetime(df['expiryDate'])
expiry_date = min(df['expiryDate'].unique())  #selecting closest expiry date
selected_df = df[df['expiryDate'] == expiry_date].copy()
selected_df['volume'] = selected_df['volume'] / 50  # NIFTY50 lot size = 50
selected_df = selected_df.pivot(index='strikePrice', columns='optionType', values=['lastPrice', 'change', 'volume', 'openInterest', 'noOfTrades'])
selected_df.columns = ['_'.join(col).strip() for col in selected_df.columns.values]
selected_df.reset_index(inplace=True)


# At this point don't know what I am doing. But am pretty sure, it does something.....
# https://dash.plotly.com/datatable
def data_bars(df, column):
    n_bins = 100
    bounds = [i * (1.0 / n_bins) for i in range(n_bins + 1)]
    ranges = [
        ((df[column].max() - df[column].min()) * i) + df[column].min()
        for i in bounds
    ]
    styles = []
    for i in range(1, len(bounds)):
        min_bound = ranges[i - 1]
        max_bound = ranges[i]
        max_bound_percentage = bounds[i] * 100
        styles.append({
            'if': {
                'filter_query': (
                    '{{{column}}} >= {min_bound}' +
                    (' && {{{column}}} < {max_bound}' if (i < len(bounds) - 1) else '')
                ).format(column=column, min_bound=min_bound, max_bound=max_bound),
                'column_id': column
            },
            'background': (
                """
                    linear-gradient(90deg,
                    #DEB887 0%,
                    #008B8B {max_bound_percentage}%,
                    white {max_bound_percentage}%,
                    white 100%)
                """.format(max_bound_percentage=max_bound_percentage)
            ),
            'paddingBottom': 2,
            'paddingTop': 2
        })
    return styles

#dash on top of flask
app = Dash(__name__)
app.layout = dash_table.DataTable(
    columns = [
    {"name": ["Call", "CHNG"], "id": "change_Call"},
    {"name": ["Call", "Volume"], "id": "volume_Call"},
    {"name": ["Call", "LTP"], "id": "lastPrice_Call"},
    {"name": ["Call", "OI"], "id": "openInterest_Call"},
    {"name": ["SP", "SP"], "id": "strikePrice"},
    {"name": ["Put", "OI"], "id": "openInterest_Put"},
    {"name": ["Put", "LTP"], "id": "lastPrice_Put"},
    {"name": ["Put", "Volume"], "id": "volume_Put"},
    {"name": ["Put", "CHNG"], "id": "change_Put"},
    ],
    data = selected_df.to_dict('records'),
    merge_duplicate_headers=True,
    style_data_conditional=(
        data_bars(selected_df,'openInterest_Call') +
        data_bars(selected_df,'openInterest_Put')
    ),
)

if __name__ == '__main__':
    app.run_server(debug=True)
