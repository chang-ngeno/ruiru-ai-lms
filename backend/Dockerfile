FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh \
    && useradd -m app && chown -R app /srv
USER app
EXPOSE 5000
# Plain Python start-up: no shell script is needed to boot the container.
CMD ["python", "-m", "app.start"]
