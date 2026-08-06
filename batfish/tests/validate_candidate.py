from pathlib import Path
import sys

from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints, PathConstraints


PROJECT_DIR = Path(__file__).resolve().parents[1]

BASE_PATH = PROJECT_DIR / "snapshots" / "base"
CANDIDATE_PATH = PROJECT_DIR / "snapshots" / "candidate-broken"

NETWORK_NAME = "ndt-project"
BASE_NAME = "base"
CANDIDATE_NAME = "candidate-broken"


def fail(message: str) -> None:
    print(f"\n[FAILED] {message}")
    sys.exit(1)


def passed(message: str) -> None:
    print(f"[PASSED] {message}")


print("Menghubungkan ke Batfish...")

try:
    bf = Session(
        host="127.0.0.1",
        port=9996,
    )

    bf.set_network(NETWORK_NAME)

    bf.init_snapshot(
        str(BASE_PATH),
        name=BASE_NAME,
        overwrite=True,
    )

    bf.init_snapshot(
        str(CANDIDATE_PATH),
        name=CANDIDATE_NAME,
        overwrite=True,
    )
except Exception as error:
    fail(f"Gagal menginisialisasi snapshot: {error}")


print("\n=== 1. STATUS PARSING CANDIDATE ===")

parse_status = (
    bf.q.fileParseStatus()
    .answer(snapshot=CANDIDATE_NAME)
    .frame()
)

print(parse_status.to_string(index=False))

if parse_status.empty:
    fail("Batfish tidak menemukan konfigurasi candidate.")

status_text = parse_status["Status"].astype(str).str.upper()

if status_text.str.contains("FAILED|UNKNOWN").any():
    fail("Candidate gagal diproses oleh Batfish.")

passed("Sintaks candidate berhasil diproses.")


print("\n=== 2. ROUTE R1 PADA BASE ===")

base_route = bf.q.routes(
    nodes="r1",
    network="192.168.30.0/24",
    prefixMatchType="EXACT",
).answer(
    snapshot=BASE_NAME
).frame()

print(base_route.to_string(index=False))

if base_route.empty:
    fail("Snapshot base tidak memiliki route menuju server.")

passed("Snapshot base memiliki route menuju server.")


print("\n=== 3. ROUTE R1 PADA CANDIDATE ===")

candidate_route = bf.q.routes(
    nodes="r1",
    network="192.168.30.0/24",
    prefixMatchType="EXACT",
).answer(
    snapshot=CANDIDATE_NAME
).frame()

print(candidate_route.to_string(index=False))

if candidate_route.empty:
    passed("Batfish mendeteksi route server hilang pada candidate.")
else:
    fail("Route server masih tersedia pada candidate.")


headers = HeaderConstraints(
    srcIps="192.168.10.10",
    dstIps="192.168.30.10",
    ipProtocols=["ICMP"],
)

path = PathConstraints(
    startLocation="@enter(r1[eth3])",
)


print("\n=== 4. REACHABILITY PADA CANDIDATE ===")

candidate_reachability = bf.q.reachability(
    pathConstraints=path,
    headers=headers,
    actions="success",
    maxTraces=1,
).answer(
    snapshot=CANDIDATE_NAME
).frame()

print(candidate_reachability.to_string(index=False))

if candidate_reachability.empty:
    passed("Candidate tidak dapat mencapai server.")
else:
    fail("Candidate ternyata masih dapat mencapai server.")


print("\n=== 5. DIFFERENTIAL REACHABILITY ===")

difference = bf.q.differentialReachability(
    pathConstraints=path,
    headers=headers,
    maxTraces=1,
).answer(
    snapshot=CANDIDATE_NAME,
    reference_snapshot=BASE_NAME,
).frame()

print(difference.to_string(index=False))

if difference.empty:
    fail("Batfish tidak menemukan perubahan reachability.")

passed("Batfish mendeteksi perubahan reachability client-server.")


print("\n============================================")
print("CANDIDATE VALIDATION: REJECTED AS EXPECTED")
print("============================================")
print("Sintaks konfigurasi : valid")
print("Route server        : hilang")
print("Client ke server    : tidak reachable")
print("Keputusan pipeline  : REJECT / JANGAN DEPLOY")
