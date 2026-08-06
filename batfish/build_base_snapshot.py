from pathlib import Path

PROJECT = Path.home() / "network-digital-twin"
MAIN_LAB = PROJECT / "main-lab"
OUTPUT = PROJECT / "batfish" / "snapshots" / "base" / "configs"

ROUTERS = {
    "r1": ["eth1", "eth2", "eth3"],
    "r2": ["eth1", "eth2"],
    "r3": ["eth1", "eth2", "eth3"],
}


def build_config(router: str, interfaces: list[str]) -> str:
    frr_path = MAIN_LAB / router / "frr.conf"

    if not frr_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {frr_path}")

    frr_config = frr_path.read_text().strip()

    linux_interfaces = [
        router,
        "# This file describes the network interfaces",
        "auto lo",
        "iface lo inet loopback",
        "",
    ]

    for interface in interfaces:
        linux_interfaces.extend([
            f"auto {interface}",
            f"iface {interface}",
            "",
        ])

    linux_interfaces.extend([
        "# ports.conf --",
        frr_config,
        "end",
        "",
    ])

    return "\n".join(linux_interfaces)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for router, interfaces in ROUTERS.items():
        output_path = OUTPUT / f"{router}.cfg"
        output_path.write_text(build_config(router, interfaces))
        print(f"Berhasil membuat: {output_path}")


if __name__ == "__main__":
    main()
