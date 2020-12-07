ARG BASE_IMAGE=jupyterhub/jupyterhub:1.2
FROM $BASE_IMAGE

RUN apt-get update && apt-get --assume-yes install git vim wget xz-utils libglib2.0-0 \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libgtk-3-0 libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 \
    libatspi2.0-0 \
 && python3 -m pip install setuptools jupyterlab \
 && useradd --no-log-init -r -u 999 jovyan && mkdir -p /home/jovyan && chown jovyan /home/jovyan \
 && useradd --no-log-init -r -u 998 marc && mkdir -p /home/marc && chown marc /home/marc

COPY ./requirements.txt /tmp/papermill_report/

RUN python3 -m pip install -r /tmp/papermill_report/requirements.txt

COPY ./jupyterhub_config.py /srv/jupyterhub/

# Install the package
COPY . /tmp/papermill_report/
RUN python3 -m pip install --no-deps --no-cache-dir --no-warn-script-location /tmp/papermill_report
#  Uncomment if you want to test non-git repository case
#  && mkdir -p /opt/ariadnext/reports/ \
#  && cp -r /tmp/papermill_report/examples/* /opt/ariadnext/reports/ \
#  && rm -rf /tmp/papermill_report
