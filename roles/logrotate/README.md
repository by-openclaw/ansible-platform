# role: logrotate

Data-driven log rotation: one entry → `/etc/logrotate.d/<name>` (paths/rotate/frequency/copytruncate/postrotate), present/absent.

Per-service entries live in the service role; fleet baseline (aide) in `hardening`; journald caps govern containers.
