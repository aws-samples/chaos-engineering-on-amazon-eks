# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

FROM python:3.9-alpine

RUN pip install --no-cache-dir \
    starlette starlette_exporter prometheus-client uvicorn httpx boto3
EXPOSE 8000

COPY . .

ENTRYPOINT [ "uvicorn" ]
CMD [ "--host", "0.0.0.0", "--port", "8000", "app:app" ]

