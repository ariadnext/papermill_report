ARG BASE_IMAGE=jupyterhub/jupyterhub:1.2
FROM $BASE_IMAGE

RUN apt-get update && apt-get --assume-yes install git vim wget xz-utils \
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
