# Basic image. May be unstable. Do not change to older images, googler won't function otherwise
FROM ubuntu:20.04

MAINTAINER Pavel Shlyak 'pvshlyak@edu.hse.ru'

RUN apt-get update
RUN apt-get install -y python3-pip poppler-utils links curl googler
RUN rm -rf /var/lib/apt/lists /var/lib/cache/* /var/log/*
WORKDIR /app

# Copy project files
COPY . .

RUN python3 -m pip install -r requirements.txt

#Publish port 5000 (default for flask)
EXPOSE 5000

#Run the app
CMD python3 launch.py

