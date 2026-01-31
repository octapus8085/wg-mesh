# OSPF

## Bird2 OSPF defaults

The renderer writes a minimal Bird2 OSPF config that works for point-to-multipoint WireGuard:

- `type ptmp` for the wg interface
- `neighbors { ... }` listing peer WG IPs
- configurable `hello` and `dead` timers

### Example

```bird
protocol ospf {
  area 0 {
    interface "wgmesh0" {
      type ptmp;
      neighbors { 10.60.0.2; 10.60.0.4; };
      hello 10;
      dead 40;
    };
  };
}
```

## Tuning

- Lower `hello` / `dead` to speed convergence.
- Ensure all peers share the same timers for stability.
- If you move to IPv6 OSPFv3 later, extend the render config accordingly.
