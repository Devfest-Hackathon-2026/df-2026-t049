FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home arena
COPY reliefroute ./reliefroute
COPY web ./web
COPY examples ./examples
COPY gunicorn.conf.py ./
USER arena
EXPOSE 8080
CMD ["gunicorn", "--config", "gunicorn.conf.py", "reliefroute.wsgi:application"]
