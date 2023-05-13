FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine
RUN apk --update add bash nano
ENV STATIC_URL /static
ENV STATIC_PATH math_games_web_site/app/static
COPY ./requirements.txt math_games_web_site/requirements.txt
RUN pip install -r math_games_web_site/requirements.txt
