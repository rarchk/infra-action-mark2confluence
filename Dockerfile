FROM python:3-slim AS builder

ADD . /app
WORKDIR /app
RUN pip install --target=/app -r requirements.txt



FROM chromedp/headless-shell:latest
ENV MARK="9.2.1"
RUN apt-get update \
&& apt-get install --no-install-recommends -qq ca-certificates bash curl software-properties-common \
&& add-apt-repository ppa:deadsnakes/ppa && apt-get install python3.11 python3-pip \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl -LO https://github.com/kovetskiy/mark/releases/download/${MARK}/mark_${MARK}_Linux_x86_64.tar.gz && \
  tar -xvzf mark_${MARK}_Linux_x86_64.tar.gz && \
  chmod +x mark && \
  sudo mv mark /usr/local/bin/mark

COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app
ENV DOC_PREFIX /github/workspace/
ENV LOGURU_FORMAT "<lvl>{level:7} {message}</lvl>"
ENTRYPOINT [ "python" ]
CMD ["/app/mark2confluence/main.py"]
