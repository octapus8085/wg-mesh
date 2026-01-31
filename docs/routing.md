# Routing

## Dynamic routing with Bird2 + OSPF

wg-mesh uses Bird2 for dynamic routing. For your star topology, OSPF is the simplest option:

- Each node runs a single WireGuard interface (`wgmesh0`).
- Bird2 runs OSPFv2 over the WireGuard interface.
- Hubs learn routes from all spokes, and spokes learn routes from hubs.

## Why OSPF

- Converges quickly when a tunnel drops.
- Keeps routing automatic even with partial outages.
- Easy to diagnose with `birdc` and clear neighbor status.

## Generated files

The render command outputs:

- `wgmesh0.conf` — WireGuard config for each node.
- `bird.conf` — Bird2 config with OSPF neighbors pre-wired.

These files are produced per-node under the output directory.
