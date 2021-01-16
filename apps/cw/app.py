# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette_exporter import PrometheusMiddleware, handle_metrics
from prometheus_client import Counter
import boto3

CW_METRIC_NAME = 'hits'
CW_DIM_NAME = 'app'
CW_DIM_VALUE = 'cw'
CW_NAMESPACE = 'chaos'
CW_UNITS = 'Count'

ERROR_COUNT = Counter(
    "failed_call", "Counts of calls that failed", ("to",))
cw = boto3.client('cloudwatch')


async def main(request: Request) -> JSONResponse:
    async with httpx.AsyncClient(timeout=1.0) as c:
        try:
            cw.put_metric_data(
                Namespace=CW_NAMESPACE,
                MetricData=[
                    {
                        'MetricName': CW_METRIC_NAME,
                        'Dimensions': [
                            {
                                'Name': CW_DIM_NAME,
                                'Value': CW_DIM_VALUE
                            },
                        ],
                        'Value': 1,
                        'Unit': CW_UNITS,
                        'StorageResolution': 60
                    },
                ]
            )
            return JSONResponse({"value": 1})
        except Exception as e:
            ERROR_COUNT.labels("cw").inc()
            s = "Failed putting CW metrics: {0}".format(str(e))
            logging.error(s)
            return JSONResponse(
                {
                    "error": e.__class__.__name__,
                    "value": -1
                }, status_code=500)


app = Starlette(debug=True, routes=[
    Route('/', main),
])
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

