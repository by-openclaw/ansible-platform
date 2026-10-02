# Minimal demo image built by Kaniko in CI and pushed to the project registry:
# serves public/ (the same files GitLab Pages publishes) on :8080 as a non-root user.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY public/ /usr/share/nginx/html/
# The base image already drops to nginx (uid 101); stated here so the image itself declares it
# (security/0003 §1 — Trivy DS-0002 reads this Dockerfile, not the base).
USER 101
EXPOSE 8080
