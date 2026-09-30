import plotly.graph_objects as go


def candle(df, title):
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.Date, open=df.Open, high=df.High, low=df.Low, close=df.Close, name=title
        )
    )
    for c in ["SMA20", "SMA50", "SMA200"]:
        if c in df.columns:
            fig.add_trace(go.Scatter(x=df.Date, y=df[c], name=c))
    fig.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(l=8, r=8, t=16, b=8))
    return fig
