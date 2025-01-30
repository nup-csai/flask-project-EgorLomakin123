FROM python:3.11

WORKDIR /app



WORKDIR /app

COPY requirements.txt /app/
# ENV PYTHONPATH=/app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8080


CMD ["flask", "--app", "app/server.py", "run", "-h", "0.0.0.0", "-p", "8080"]
