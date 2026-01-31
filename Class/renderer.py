import configparser
import ipaddress
import os

try:
    import yaml
except ImportError:
    yaml = None


class Renderer:
    def __init__(self, path):
        self.path = path

    def render(self, config_path, output_dir=None):
        config = self.load_config(config_path)
        mesh = config.get("mesh", {})
        topology = config.get("topology", {})
        transport = config.get("transport", {})
        nodes = self.normalize_nodes(config.get("nodes", {}))

        if not nodes:
            raise SystemExit("No nodes defined in config.")

        wg = mesh.get("wg", {})
        interface = wg.get("interface", "wgmesh0")
        mtu = int(wg.get("mtu", 1420))
        default_port = int(wg.get("port", 51820))
        ospf = mesh.get("ospf", {})
        ospf_area = ospf.get("area", 0)
        ospf_hello = int(ospf.get("hello", 10))
        ospf_dead = int(ospf.get("dead", 40))
        transport_mode = transport.get("mode", "public")

        peers_map, hubs, spokes = self.build_peers(nodes, topology)
        output_dir = output_dir or os.path.join(self.path, "rendered")
        os.makedirs(output_dir, exist_ok=True)

        errors = []
        for node_name, node_data in nodes.items():
            node_dir = os.path.join(output_dir, node_name)
            os.makedirs(node_dir, exist_ok=True)

            listen_port = int(node_data.get("listen_port", default_port))
            address = node_data.get("wg_ip")
            if not address:
                errors.append(f"{node_name} is missing wg_ip")
                continue

            wg_config = self.render_wireguard(
                node_name=node_name,
                node_data=node_data,
                peers=[nodes[peer] for peer in peers_map[node_name]],
                interface=interface,
                mtu=mtu,
                listen_port=listen_port,
                transport_mode=transport_mode,
                default_port=default_port,
                hubs=hubs,
            )
            wg_path = os.path.join(node_dir, f"{interface}.conf")
            with open(wg_path, "w", encoding="utf-8") as handle:
                handle.write(wg_config)

            bird_config = self.render_bird(
                node_name=node_name,
                node_data=node_data,
                peers=[nodes[peer] for peer in peers_map[node_name]],
                interface=interface,
                ospf_area=ospf_area,
                ospf_hello=ospf_hello,
                ospf_dead=ospf_dead,
            )
            bird_path = os.path.join(node_dir, "bird.conf")
            with open(bird_path, "w", encoding="utf-8") as handle:
                handle.write(bird_config)

        if errors:
            raise SystemExit("Config errors:\n- " + "\n- ".join(errors))

        print(f"Rendered {len(nodes)} node configs into {output_dir}")

    def load_config(self, config_path):
        _, ext = os.path.splitext(config_path)
        ext = ext.lower()
        if ext in [".yml", ".yaml"]:
            if yaml is None:
                raise SystemExit("PyYAML is required for YAML configs. Install python3-yaml.")
            with open(config_path, "r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        if ext == ".ini":
            return self.load_ini(config_path)
        raise SystemExit("Config must be .yml/.yaml or .ini")

    def load_ini(self, config_path):
        parser = configparser.ConfigParser()
        parser.read(config_path)
        config = {
            "mesh": self._section(parser, "mesh"),
            "topology": self._section(parser, "topology"),
            "transport": self._section(parser, "transport"),
        }
        wg = self._section(parser, "wg")
        ospf = self._section(parser, "ospf")
        if wg:
            config["mesh"].setdefault("wg", {}).update(wg)
        if ospf:
            config["mesh"].setdefault("ospf", {}).update(ospf)
        nodes = {}
        for section in parser.sections():
            if section.startswith("node:"):
                name = section.split("node:")[1].strip()
                nodes[name] = {"name": name, **self._section(parser, section)}
        config["nodes"] = nodes
        for list_key in ["hubs", "spokes"]:
            if list_key in config["topology"]:
                config["topology"][list_key] = self.parse_list(config["topology"][list_key])
        return config

    def _section(self, parser, section):
        if section not in parser:
            return {}
        return {key: self._cast_value(value) for key, value in parser[section].items()}

    def _cast_value(self, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ["true", "false"]:
                return lowered == "true"
            if lowered.isdigit():
                return int(lowered)
        return value

    def parse_list(self, value):
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [item.strip() for item in str(value).split(",") if item.strip()]

    def normalize_nodes(self, nodes):
        normalized = {}
        if isinstance(nodes, list):
            for node in nodes:
                name = node.get("name")
                if not name:
                    continue
                normalized[name] = node
        elif isinstance(nodes, dict):
            for name, node in nodes.items():
                if isinstance(node, dict):
                    node = {"name": name, **node}
                normalized[name] = node
        for name, node in normalized.items():
            node.setdefault("name", name)
        return normalized

    def build_peers(self, nodes, topology):
        hubs = set(self.parse_list(topology.get("hubs", [])))
        spokes = set(self.parse_list(topology.get("spokes", [])))
        if not hubs:
            hubs = {name for name, node in nodes.items() if node.get("role") == "hub"}
        if not spokes:
            spokes = {name for name, node in nodes.items() if node.get("role") == "spoke"}
        if not hubs:
            hubs = set(nodes.keys())
        if not spokes:
            spokes = set(nodes.keys()) - hubs

        peers_map = {}
        for node_name in nodes:
            if node_name in hubs:
                peers = (hubs - {node_name}) | spokes
            else:
                peers = hubs
            peers_map[node_name] = sorted(peers)
        return peers_map, hubs, spokes

    def render_wireguard(
        self,
        node_name,
        node_data,
        peers,
        interface,
        mtu,
        listen_port,
        transport_mode,
        default_port,
        hubs,
    ):
        private_key = node_data.get("private_key", "CHANGEME_PRIVATE_KEY")
        address = node_data.get("wg_ip")
        config_lines = [
            "[Interface]",
            f"PrivateKey = {private_key}",
            f"Address = {address}",
            f"ListenPort = {listen_port}",
            f"MTU = {mtu}",
            "",
        ]
        for peer in peers:
            endpoint = self.peer_endpoint(peer, default_port, transport_mode)
            if not endpoint:
                raise SystemExit(f"{peer['name']} missing endpoint data for transport mode {transport_mode}")
            keepalive = None
            if node_name not in hubs:
                keepalive = "PersistentKeepalive = 25"
            peer_ip = self.strip_cidr(peer.get("wg_ip", ""))
            config_lines.append("[Peer]")
            config_lines.append(f"PublicKey = {peer.get('public_key', 'CHANGEME_PUBLIC_KEY')}")
            config_lines.append(f"AllowedIPs = {peer_ip}/32")
            config_lines.append(f"Endpoint = {endpoint}")
            if keepalive:
                config_lines.append(keepalive)
            config_lines.append("")
        return "\n".join(config_lines).strip() + "\n"

    def render_bird(self, node_name, node_data, peers, interface, ospf_area, ospf_hello, ospf_dead):
        router_id = self.strip_cidr(node_data.get("wg_ip", "0.0.0.0"))
        neighbor_ips = [self.strip_cidr(peer.get("wg_ip", "")) for peer in peers if peer.get("wg_ip")]
        neighbors_block = ""
        if neighbor_ips:
            neighbors_block = f"\n      neighbors {{ {'; '.join(neighbor_ips)}; }};"
        bird_config = f"""log syslog all;
router id {router_id};

protocol device {{
  scan time 10;
}}

protocol kernel {{
  ipv4 {{ import all; export all; }};
}}

protocol ospf {{
  area {ospf_area} {{
    interface "{interface}" {{
      type ptmp;{neighbors_block}
      hello {ospf_hello};
      dead {ospf_dead};
    }};
  }};
}}
"""
        return bird_config

    def peer_endpoint(self, peer, default_port, transport_mode):
        if peer.get("endpoint"):
            return peer["endpoint"]
        port = peer.get("transport_port") or peer.get("listen_port") or default_port
        if transport_mode == "tailscale":
            ip = peer.get("tailscale_ip") or peer.get("transport_ip")
        else:
            ip = peer.get("public_ip") or peer.get("transport_ip")
        if not ip:
            return None
        return f"{ip}:{port}"

    def strip_cidr(self, value):
        if not value:
            return ""
        try:
            return str(ipaddress.ip_interface(value).ip)
        except ValueError:
            return value.split("/")[0]
