# role: tls_cert

Distributes the **shared wildcard `*.by-research.be` certificate** to any device
that needs end-to-end TLS (PostgreSQL, Redis, …).

The cert is issued **once** on the cert-authority host (`lxc-traefik-01`) via
lego DNS-01 (see `roles/traefik`). This role copies that cert+key over the
existing SSH/ProxyJump path (delegated `slurp`) and installs it locally — it does
**not** run ACME per device, which would hit the Let's Encrypt duplicate-cert
rate limit ("every device has the cert").

Idempotent: the `copy` compares content, so it re-writes only on actual renewal
and notifies the `tls_cert changed` handler topic.

## Usage

Consuming roles include it after their service user exists, overriding the group
and destination so the service can read the key:

```yaml
- name: "tls | Distribute the wildcard cert (readable by postgres)"
  ansible.builtin.include_role:
    name: tls_cert
  vars:
    tls_cert_group: postgres
    tls_cert_crt: "{{ pg_ssl_cert }}"
    tls_cert_key: "{{ pg_ssl_key }}"
```

To reload the service on renewal, add a handler with `listen: "tls_cert changed"`.

## Key variables

| var | default | purpose |
|---|---|---|
| `tls_cert_source_host` | `lxc-traefik-01` | cert-authority (lego) host |
| `tls_cert_source_crt` / `_key` | lego wildcard paths | source cert/key |
| `tls_cert_dir` | `/etc/ssl/by-research` | destination dir |
| `tls_cert_crt` / `_key` | `wildcard.crt` / `.key` | destination files |
| `tls_cert_owner` / `_group` | `root` / `root` | ownership |
| `tls_cert_crt_mode` / `_key_mode` | `0644` / `0640` | perms |
