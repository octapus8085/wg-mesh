# Topologies

## Star topology (EU/TR hubs, IR spokes)

This repo includes a render workflow for a **star topology** that matches the requirement:

- **Hubs**: EU + TR (alpha, tango)
- **Spokes**: IR (bravo, charlie, sierra)

In a star, all spokes connect to each hub, and hubs peer with each other. This keeps routing flexible while minimizing required peerings.

## Inventory shape

The `topology` section declares hubs and spokes:

```yaml
topology:
  type: star
  hubs: [alpha, tango]
  spokes: [bravo, charlie, sierra]
```

The renderer uses these lists to generate peer stanzas for each node.

## Recommended layout

- **Hubs** should be deployed on stable infrastructure with public IPs or Tailscale addresses.
- **Spokes** can be behind NAT or only reachable via Tailscale.
- Enable OSPF on all nodes to dynamically distribute the internal mesh routes.
