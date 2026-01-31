# Tasks & Troubleshooting

## Common tasks

### Render configs from inventory

```bash
wgmesh render --config docs/examples/mymesh.yml --output rendered
```

### Apply configs

1. Copy `wgmesh0.conf` to `/etc/wireguard/wgmesh0.conf`.
2. Copy `bird.conf` to `/etc/bird/bird.conf`.
3. Restart services:

```bash
systemctl restart wg-quick@wgmesh0
systemctl restart bird
```

### Verify routing

```bash
wg show
birdc show protocols
birdc show route
```

## Troubleshooting quick checks

- WireGuard handshake missing → confirm endpoints and keys.
- OSPF neighbor down → check timers and interface name.
- Routes not installed → check Bird2 is running and OSPF neighbors are `up`.
