FROM python:3.9-alpine

COPY app .
COPY manager .
COPY models .
COPY __init__.py .
COPY setup.py .

COPY requirements.txt .

RUN pip install -U pip
RUN pip install --no-cache-dir .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["{{cookiecutter.project_name}}","run"]