FROM python:3.12-slim
WORKDIR /app
COPY public ./public
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "python -m http.server ${PORT} --directory /app/public --bind 0.0.0.0"]
