#Description: Lizzy's trading strategy for trend days

#Import libraries
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd 
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from pandas_market_calendars import get_calendar
import json


df = pd.DataFrame()

#Load data
df = yf.download("ES=F", start="2023-06-01", end=None, interval="5m") 

df = df.iloc[:-1 , :]

# Filter out weekends
df = df[df.index.dayofweek < 5]

#indicators
df['EMA1'] = df.Close.rolling(9).mean()
df['EMA2'] = df.Close.rolling(21).mean()
df['EMA3'] = df.Close.rolling(50).mean()

def vwap():
    return np.cumsum(df.Volume*(df.High + df.Low)/2) / np.cumsum(df.Volume)
df['VWAP'] = vwap()


#Validates uptrends EMAS
def is_uptrend (j):
    previous_lines = 10
    if (j < previous_lines):
        return False
    
    for i in range(j - previous_lines, j):
        if not (df.EMA1[i] > df.EMA2[i] and df.EMA2[i] > df.EMA3[i] and df.High[i] > df.VWAP[i] and df.Low[i] > df.VWAP[i] and df.Close[i] > df.EMA3[i]):
            return False   
    return True

#trade data
target = 25
stop = 3
points_trail_num = 5

trade_value = 100
trades = []

current_trade = {}

#Enter long
for i in range(len(df) -1):
    #Defines stop-loss
    if len(current_trade) != 0 and current_trade["entry_price"] - stop >= df.iloc[i+1].Open:
        trades.append({
            "entry_price":current_trade["entry_price"],
            "entry_time":current_trade["entry_time"],
            "trade_size":current_trade["remaining_size"],
            "exit_price":df.iloc[i+1].Open,
            "exit_time":df.iloc[i+1].name,
            "profit_pct":(df.iloc[i+1].Open/current_trade["entry_price"]) -1,
        })

        current_trade = {}
    #Entry condition
    elif df.Close[i] < df.EMA1[i] and df.Close[i] > df.EMA3[i] and len(current_trade) == 0 and df.EMA1[i] > df.EMA2[i] and df.EMA2[i] > df.EMA3[i] and is_uptrend(i):
        current_trade["entry_price"] = df.iloc[i+1].Open
        current_trade["entry_time"] = df.iloc[i+1].name
        current_trade["initial_size"] = trade_value / current_trade["entry_price"]
        current_trade["remaining_size"] = current_trade["initial_size"]
        current_trade["stop_loss"] = current_trade["entry_price"] - points_trail_num
    #Adds a trailing stop-loss
    elif len(current_trade) != 0:
        if df.iloc[i+1].Open - current_trade["entry_price"] >= points_trail_num:
            current_trade["stop_loss"] = current_trade["stop_loss"] + (points_trail_num / 3)

        if df.iloc[i+1].Low < current_trade["stop_loss"]:
            trades.append({
                "entry_price": current_trade["entry_price"],
                "entry_time": current_trade["entry_time"],
	            "trade_size": current_trade["remaining_size"],
                "exit_price": current_trade["stop_loss"],
	            "exit_time": df.iloc[i+1].name,
                "profit_pct": (current_trade["stop_loss"] / current_trade["entry_price"]) - 1,
            })    

            current_trade = {} 

trades = pd.DataFrame(trades)
trades

         
# Create candlestick trace
candlestick_trace = go.Candlestick(
    x=df.index,
    open=df.Open,
    high=df.High,
    low=df.Low,
    close=df.Close,
    increasing_fillcolor='#009973', #fill color
    decreasing_fillcolor='purple', #fill color
    increasing_line_color='#b3ffec', #line color
    decreasing_line_color='#df80ff', #line color
      # Set the width of each candlestick
    
)


# Create additional scatter traces
scatter_traces = [
    go.Scatter(x=df.index, y=df.VWAP, line=dict(color='green', width=1)),
    go.Scatter(x=df.index, y=df.EMA1, line=dict(color='blue', width=1)),
    go.Scatter(x=df.index, y=df.EMA2, line=dict(color='yellow', width=1)),
    go.Scatter(x=df.index, y=df.EMA3, line=dict(color='orange', width=1))
]

# Create layout
layout = go.Layout(
    title='ES Chart',
    plot_bgcolor='#0d0d0d', # Background color to black

    xaxis=dict(
        showgrid=False,  # Remove the grid from the x-axis
        rangebreaks=[
            dict(bounds=["sat", "mon"])
        ]
    ),
    yaxis=dict(
        showgrid=False  # Remove the grid from the y-axis
    )
)

# Create figure
fig = go.Figure(data=[candlestick_trace, *scatter_traces], layout=layout)


#plot entries
if len(trades) > 0:
    fig.add_trace(go.Scatter(
        x = trades.entry_time,
        y = trades.entry_price,
        mode = "markers",
        customdata=trades,
        marker_symbol = "arrow-right",
        marker_size = 9,
        marker_line_width = 1,
        marker_line_color = "black",
        marker_color = '#0000fa', #blue
        hovertemplate="Entry Time: %{customdata[1]}<br>" +\
                    "Entry Price: %{y:.2f}<br>" +\
                    "Size: %{customdata[2]:.5f}<br>" +\
                    "Profit_pct: %{customdata[5]:.3f}",
        name="Entries"     
    ))


#plot exits
if len(trades) > 0:
    fig.add_trace(go.Scatter(
        x = trades.exit_time,
        y = trades.exit_price,
        mode = "markers",
        customdata=trades,
        marker_symbol = "arrow-left",
        marker_size = 9,
        marker_line_width = 1,
        marker_line_color = "black",
        marker_color = '#fa0046', #pink
        hovertemplate="Exit Time: %{customdata[4]}<br>" +\
                    "Exit Price: %{y:.2f}<br>" +\
                    "Size: %{customdata[2]:.5f}<br>" +\
                    "Profit_pct: %{customdata[5]:.3f}",
        name="Exits"     
    ))

# Connect entry and exit line
if len(trades) > 0:
    for i in range(len(trades)):
        if trades.exit_price[i] > trades.entry_price[i]:
            line_color = '#ff0078' # Set color to green for profit
        else:
            line_color = '#ff0078' # Set color to red for loss

        fig.add_trace(go.Scatter(
            x=[trades.entry_time[i], trades.exit_time[i]],
            y=[trades.entry_price[i], trades.exit_price[i]],
            mode='lines',
            line=dict(color=line_color, width=2, dash='dash'),
            showlegend=False
            
        ))

              
fig.update_layout(xaxis_rangeslider_visible=False)

fig.show()

# Save the chart as JSON
chart_json = fig.to_json()

# Save the JSON data to a file
with open('chart_data.json', 'w') as json_file:
    json.dump(chart_json, json_file)





