from dash import Dash, dcc, html
import plotly.graph_objs as go
import numpy as np
import pandas as pd

app = Dash(__name__)

# Sample data for metrics (replace with actual metrics data)
metrics_data = {
    'Metric': ['Entropy', 'Correlation', 'NPCR', 'UACI', 'PSNR'],
    'Value': [7.99, 0.01, 99.6, 33.4, float('inf')]
}

df_metrics = pd.DataFrame(metrics_data)

app.layout = html.Div([
    html.H1("Encryption Quality Metrics Dashboard"),
    dcc.Graph(
        id='metrics-graph',
        figure={
            'data': [
                go.Bar(
                    x=df_metrics['Metric'],
                    y=df_metrics['Value'],
                    marker=dict(color='royalblue')
                )
            ],
            'layout': go.Layout(
                title='Encryption Quality Metrics',
                xaxis={'title': 'Metrics'},
                yaxis={'title': 'Values'},
                hovermode='closest'
            )
        }
    ),
    html.Div(id='metrics-summary', children=[
        html.H3("Summary of Metrics"),
        html.Ul([
            html.Li(f"{row['Metric']}: {row['Value']}")
            for index, row in df_metrics.iterrows()
        ])
    ])
])

if __name__ == '__main__':
    app.run_server(debug=True)