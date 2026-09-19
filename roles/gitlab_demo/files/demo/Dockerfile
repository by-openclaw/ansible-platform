# Minimal demo image built by Kaniko in CI and pushed to the project registry:
# serves public/ (the same files GitLab Pages publishes) on :8080 as a non-root user.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY public/ /usr/share/nginx/html/
EXPOSE 8080
