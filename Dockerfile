FROM python:3-slim AS builder

ADD . /app
WORKDIR /app

RUN pip install --target=/app -r requirements.txt

FROM python:3-slim
ENV MARK="9.6.0"
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y tar curl sudo && \
  rm -rf /var/lib/apt/lists/*
RUN curl -LO https://go.dev/dl/go1.20.5.linux-amd64.tar.gz &&  rm -rf /usr/local/go && tar -C /usr/local -xzf go1.20.5.linux-amd64.tar.gz &&\
    export PATH=$PATH:/usr/local/go/bin && go version &&\
    go install github.com/kovetskiy/mark@${MARK} && whereis mark && mark --version

COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app
ENV DOC_PREFIX /github/workspace/
ENV LOGURU_FORMAT "<lvl>{level:7} {message}</lvl>"
ENTRYPOINT [ "python" ]
CMD ["/app/mark2confluence/main.py"]
