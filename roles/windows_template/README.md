# role: windows_template

Builds a Windows VM **template** on a Proxmox node, unattended — the pipeline is documented in
`defaults/main.yml`. First use: `tpl-ws2025-std-gui` (Server 2025 Standard, Desktop Experience)
on `br-pmox-03`, from the Microsoft 180-day evaluation media (the owner's choice; licence keys
are applied later by a role task — `slmgr`/DISM, the supported eval→Standard switch, no rebuild).

- The answer file and the clones' cloudbase-init configuration are the products' own
  configuration formats (like `gitlab.rb`): rendered from templates, never hand-edited.
- The build VM's NIC keeps its **link down** for the whole build: drivers install, nothing is
  exposed; the node's bridge is the OOB one.
- The answer ISO carries the build administrator's password (Vault `{env}/windows/build-admin`):
  it is removed from the node the moment the template stands; every clone's own password comes
  from its cloud-init drive.
- Re-running with the template present does nothing; a half-finished build is replaced only with
  `-e windows_template_rebuild=true`.

Run: `ansible-playbook playbooks/windows-template.yml -e target=br-pmox-03` (the whole build is
~45–75 min; the play polls the VM until sysprep powers it off).
