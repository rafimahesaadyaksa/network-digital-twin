from pathlib import Path
import sys

from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints, PathConstraints


PROJECT_DIR = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = PROJECT_DIR / "snapshots" / "base"

NETWORK_NAME = "ndt-project"
SNAPSHOT_NAME = "base"


def fail(message: str) -> None:
    print(f"\n[FAILED] {message}")
    sys.exit(1)


print("Menghubungkan ke Batfish...")

try:
    bf = Session(host="127.0.0.1", port=9996)
    bf.set_network(NETWORK_NAME)

    bf.init_snapshot(
        str(SNAPSHOT_PATH),
        name=SNAPSHOT_NAME,
        overwrite=True,
    )
except Exception as error:
    fail(f"Tidak dapat menginisialisasi snapshot: {error}")


print("\n=== 1. STATUS PARSING ===")

parse_status = bf.q.fileParseStatus().answer().frame()
print(parse_status.to_string(index=False))

if parse_status.empty:
    fail("Batfish tidak menemukan konfigurasi router.")

status_text = parse_status["Status"].astype(str).str.upper()

if status_text.str.contains("FAILED|UNKNOWN").any():
    fail("Terdapat konfigurasi yang gagal diproses Batfish.")


print("\n=== 2. PERINGATAN INISIALISASI ===")

initialization_issues = bf.q.initIssues().answer().frame()

if initialization_issues.empty:
    print("Tidak ada initialization issue.")
else:
    print(initialization_issues.to_string(index=False))


print("\n=== 3. ROUTE R1 MENUJU SERVER ===")

routes = bf.q.routes(
    nodes="r1",
    network="192.168.30.0/24",
    prefixMatchType="EXACT",
).answer().frame()

print(routes.to_string(index=False))

if routes.empty:
    fail("R1 tidak memiliki route menuju 192.168.30.0/24.")

if "Next_Hop_IP" not in routes.columns:
    fail("Kolom Next_Hop_IP tidak ditemukan pada hasil route.")

uses_primary_path = (
    routes["Next_Hop_IP"]
    .astype(str)
    .str.contains("10.0.12.2", regex=False)
    .any()
)

if not uses_primary_path:
    fail("R1 tidak memilih R2 10.0.12.2 sebagai jalur utama.")


print("\n=== 4. REACHABILITY CLIENT KE SERVER ===")

headers = HeaderConstraints(
    srcIps="192.168.10.10",
    dstIps="192.168.30.10",
    ipProtocols=["ICMP"],
)

path = PathConstraints(
    startLocation="@enter(r1[eth3])",
)

reachability = bf.q.reachability(
    pathConstraints=path,
    headers=headers,
    actions="success",
    maxTraces=1,
).answer().frame()

print(reachability.to_string(index=False))

if reachability.empty:
    fail(
        "Batfish tidak menemukan jalur berhasil dari "
        "client 192.168.10.10 menuju server 192.168.30.10."
    )


print("\n====================================")
print("BASE VALIDATION: PASSED")
print("====================================")
print("Parsing konfigurasi : berhasil")
print("Route utama R1      : melalui 10.0.12.2")
print("Client ke server    : reachable")
