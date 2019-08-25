FROM python:2.7

WORKDIR /usr/src/python-behave-test

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD find . -name "*.feature" -exec behave --color {} \+