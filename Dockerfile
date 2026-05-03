# syntax=docker/dockerfile:1
FROM python:3.11
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY /app/requirements.txt /app/
RUN ls -la /app/
RUN pip install -r /app/requirements.txt
#COPY app/ /app/