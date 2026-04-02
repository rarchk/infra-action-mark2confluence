FROM python:3-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --target=/app -r requirements.txt

COPY . .



FROM chromedp/headless-shell:latest

ENV MARK="v16.2.0"

RUN apt-get update \
&& apt-get install --no-install-recommends -qq ca-certificates curl gnupg python3-launchpadlib -y \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN curl -LO https://github.com/kovetskiy/mark/releases/download/${MARK}/mark_Linux_x86_64.tar.gz \
&& tar -xzf mark_Linux_x86_64.tar.gz \
&& mv mark /usr/local/bin/mark \
&& rm mark_Linux_x86_64.tar.gz

COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app
ENV DOC_PREFIX /github/workspace/
ENV LOGURU_FORMAT "<lvl>{level:7} {message}</lvl>"
ENTRYPOINT [ "python3" ]
CMD ["/app/mark2confluence/main.py"]
