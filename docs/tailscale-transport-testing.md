# Tailscale transport testing

## Goal

Testing mode lets you build the WireGuard mesh without any public IPs by using **Tailscale IPs** as the transport endpoints.

## Configuration

Set the transport mode to `tailscale` and provide `tailscale_ip` per node:

```yaml
transport:
  mode: tailscale

nodes:
  alpha:
    wg_ip: 10.60.0.1/32
    tailscale_ip: 100.64.0.11
```

The renderer will build peer endpoints using these Tailscale IPs and the per-node port (or the default port).

## Run

```bash
wgmesh render --config docs/examples/mymesh.yml --output rendered
```

Use the output files on each node to bring up WireGuard and Bird2.

## Troubleshooting

- Ensure Tailscale is connected and can ping between nodes.
- If endpoints are missing, confirm every node has a `tailscale_ip` defined.
