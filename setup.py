#!/usr/bin/env python3
"""
AD framework setup script.
Prepares workspaces, backs up services, installs tooling, and starts pkappa2 + pcap capture.
"""
import fnmatch
import logging
import os
import secrets
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

# Paths
BASE_DIR         = Path(__file__).parent.resolve()
SERVICES_ROOT    = Path("/services")
WORKSPACES_ROOT  = Path("/root/workspaces")
BACKUPS_ROOT     = Path("/root/backups")
BIN_DIR          = BASE_DIR / "bin"
BIN_PATH         = Path("/usr/local/bin")
EXPLOIT_TEMPLATE = BASE_DIR / "templates" / "exploit.py"
PKAPPA_DIR       = BASE_DIR / "pkappa2"
PCAP_DIR         = Path("/root/pcaps")
LOG_FILE         = Path("/root/setup.log")

# Logging
def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE),
        ],
    )

log = logging.getLogger(__name__)

# Config
def build_config() -> dict:
    return {
        "players": ["zohbyte", "adlee7", "blondetechie", "raidershredder", "NUMB3R_1!"],
        "pkappa2": {
            "ip":       "127.0.0.1",
            "port":     8080,
            "user":     "admin",
            "password": secrets.token_hex(16),
        },
        "pcap": {
            "iface":    "game",
            "interval": 30,
        },
    }

# Helpers
EXECUTABLE = (
    stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
    stat.S_IRGRP | stat.S_IXGRP |
    stat.S_IROTH | stat.S_IXOTH
)  # 755


def require_tool(name: str) -> None:
    """Abort early if a required binary is missing."""
    if not shutil.which(name):
        log.error("Required tool not found: %s — install it and re-run.", name)
        sys.exit(1)


def chmod_recursive(path: Path, mode: int) -> None:
    """Pure-Python recursive chmod (avoids spawning a subprocess)."""
    for root, dirs, files in os.walk(path):
        for entry in dirs + files:
            try:
                os.chmod(os.path.join(root, entry), mode)
            except OSError as exc:
                log.warning("chmod failed on %s: %s", entry, exc)


def run(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """Thin wrapper around subprocess.run with consistent logging."""
    log.debug("Running: %s", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kwargs)


# Steps
def create_workspaces(players: list[str], services: list[str]) -> None:
    log.info("Creating workspaces for %d players x %d services...", len(players), len(services))
    for player in players:
        for service in services:
            service_dir = WORKSPACES_ROOT / player / service
            service_dir.mkdir(parents=True, exist_ok=True)

            exploit_dest = service_dir / "exploit.py"
            if not exploit_dest.exists() and EXPLOIT_TEMPLATE.exists():
                shutil.copy(EXPLOIT_TEMPLATE, exploit_dest)
                log.info("Copied exploit template -> %s", exploit_dest)


def backup_services(services: list[str]) -> None:
    log.info("Backing up %d service(s)...", len(services))
    for service in services:
        src_root = SERVICES_ROOT / service
        dst_root = BACKUPS_ROOT / service

        if not src_root.exists():
            log.warning("Service directory not found, skipping: %s", src_root)
            continue

        dst_root.mkdir(parents=True, exist_ok=True)

        for src_path in src_root.rglob("*"):
            if not src_path.is_file():
                continue
            dst_path = dst_root / src_path.relative_to(src_root)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if dst_path.exists():
                log.debug("Backup exists, skipping: %s", dst_path)
                continue
            shutil.copy2(src_path, dst_path)

        log.info("Backed up %s -> %s", service, dst_root)


def install_bin_scripts() -> None:
    if not BIN_DIR.exists():
        log.info("No bin/ directory found, skipping.")
        return

    log.info("Installing bin scripts -> %s", BIN_PATH)
    for src in BIN_DIR.iterdir():
        if not src.is_file():
            continue

        dst = BIN_PATH / src.name
        shutil.copy(src, dst)
        os.chmod(dst, EXECUTABLE)
        log.info("Installed %s -> %s", src.name, dst)

        if src.suffix == ".sh":
            wrapper = BIN_PATH / src.stem
            try:
                wrapper.write_text(f'#!/bin/bash\nexec "{dst}" "$@"\n')
                os.chmod(wrapper, EXECUTABLE)
                log.info("Created wrapper %s -> %s", wrapper.name, dst)
            except OSError as exc:
                log.warning("Failed to create wrapper %s: %s", wrapper, exc)


def install_requirements() -> None:
    packages: set[str] = set()
    for req in BASE_DIR.rglob("requirements*.txt"):
        if not req.is_file():
            continue
        for line in req.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                packages.add(line)

    if not packages:
        log.info("No requirements*.txt found under %s, skipping.", BASE_DIR)
        return

    pkg_list = sorted(packages)
    log.info("Installing %d package(s)...", len(pkg_list))
    try:
        run([sys.executable, "-m", "pip", "install", "--quiet"] + pkg_list)
        log.info("Requirements installed.")
    except subprocess.CalledProcessError as exc:
        log.error("pip install failed: %s", exc)
        log.error("Manual: %s -m pip install %s", sys.executable, " ".join(pkg_list))


def setup_pkappa2(cfg: dict) -> None:
    log.info("Setting up pkappa2...")
    require_tool("docker")
    require_tool("git")

    if not PKAPPA_DIR.exists():
        try:
            run(["git", "clone", "https://github.com/pkappa2/pkappa2.git", str(PKAPPA_DIR)])
            log.info("Cloned pkappa2 -> %s", PKAPPA_DIR)
        except subprocess.CalledProcessError as exc:
            log.error("Failed to clone pkappa2: %s", exc)
            return
        
    pw = cfg["password"]
    env_path = PKAPPA_DIR / ".env"
    # Ensure /data exists and has rwx permissions (mode 0o777)
    data_dir = PKAPPA_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(data_dir, 0o777)
        log.info("Set permissions 777 on /data")
    except Exception as exc:
        log.warning(f"Failed to set permissions on /data: {exc}")

    env_path.write_text(f"""\
PKAPPA2_USER_PASSWORD={pw}
PKAPPA2_PCAP_PASSWORD={pw}
PKAPPA2_BASE_DIR=/data
PKAPPA2_WATCH_DIR=/pcaps_in
# PKAPPA2_INDEX_DIR=
# PKAPPA2_PCAP_DIR=
# PKAPPA2_SNAPSHOT_DIR=
# PKAPPA2_STATE_DIR=
# PKAPPA2_CONVERTER_DIR=
# PKAPPA2_TCP_CHECK_OPTIONS=1
# PKAPPA2_TCP_CHECK_STATE=1
""")
    log.info("Wrote %s", env_path)

    converters_dir = PKAPPA_DIR / "converters"
    if converters_dir.exists():
        for f in converters_dir.glob("*.py"):
            os.chmod(f, EXECUTABLE)
    try:
        run(["docker", "compose", "up", "-d"], cwd=PKAPPA_DIR)
        log.info("pkappa2 container started.")
    except subprocess.CalledProcessError as exc:
        log.error("Failed to start pkappa2: %s", exc)
        return

    data_dir = PKAPPA_DIR / "data"
    _wait_for_path(data_dir, timeout=15)
    if data_dir.exists():
        chmod_recursive(data_dir, 777)
    else:
        log.warning("pkappa2 data dir never appeared at %s", data_dir)

    _wait_for_pkappa2(cfg)

    log.info("pkappa2 ready. Password: %s", pw)


def _wait_for_path(path: Path, timeout: int = 15) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.5)


def _wait_for_pkappa2(cfg: dict, timeout: int = 30) -> None:
    """Poll pkappa2's HTTP endpoint until it responds or we give up."""
    url = f"http://{cfg['ip']}:{cfg['port']}/"
    log.info("Waiting for pkappa2 at %s ...", url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["curl", "--silent", "--max-time", "2", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() not in ("", "000"):
            log.info("pkappa2 is up (HTTP %s).", result.stdout.strip())
            return
        time.sleep(2)
    log.warning("pkappa2 did not respond within %ds — first pcap upload may fail.", timeout)


def setup_pcap_capture(pcap_cfg: dict, pkappa2_cfg: dict) -> subprocess.Popen | None:
    """Write the upload callback script and launch tcpdump."""
    require_tool("tcpdump")

    PCAP_DIR.mkdir(parents=True, exist_ok=True)

    netrc_path = Path("/root/.netrc_pkappa2")
    netrc_path.write_text(
        f"machine {pkappa2_cfg['ip']}\n"
        f"login {pkappa2_cfg['user']}\n"
        f"password {pkappa2_cfg['password']}\n"
    )
    os.chmod(netrc_path, 0o600)

    callback = Path("/root/tcpdump_complete.sh")
    callback.write_text(f"""\
#!/bin/bash
PCAP="$1"
FILENAME=$(basename "$PCAP")
URL="http://{pkappa2_cfg['ip']}:{pkappa2_cfg['port']}/upload/$FILENAME"
echo "[pcap] Uploading $FILENAME"
curl --silent --netrc-file "{netrc_path}" --data-binary "@$PCAP" "$URL" \\
    && rm "$PCAP" \\
    && echo "[pcap] Done: $FILENAME" \\
    || echo "[pcap] Upload FAILED: $FILENAME"
""")
    os.chmod(callback, EXECUTABLE)
    log.info("Wrote pcap callback -> %s", callback)

    iface    = pcap_cfg["iface"]
    interval = pcap_cfg["interval"]
    cmd = [
        "tcpdump",
        "-n", "-i", iface,
        "(tcp or udp) and not (port 22)",
        "-Z", "root",
        "-G", str(interval),
        "-w", str(PCAP_DIR / f"{iface}_%Y%m%d_%H%M%S.pcap"),
        "-z", str(callback),
    ]

    try:
        network_log = open('/root/network.log', 'ab')
        proc = subprocess.Popen(cmd, stdout=network_log, stderr=network_log)
        log.info("tcpdump started (pid=%d) on %s, rotating every %ds.", proc.pid, iface, interval)
        return proc
    except OSError as exc:
        log.error("Failed to start tcpdump: %s", exc)
        return None


# Main
def main() -> subprocess.Popen | None:
    setup_logging()
    cfg = build_config()

    log.info("=" * 60)
    log.info("AD Framework Setup")
    log.info("=" * 60)

    services = (
        [d.name for d in SERVICES_ROOT.iterdir() if d.is_dir()]
        if SERVICES_ROOT.exists() else []
    )
    log.info("Detected services: %s", services or "(none)")

    create_workspaces(cfg["players"], services)
    backup_services(services)
    install_bin_scripts()
    install_requirements()
    setup_pkappa2(cfg["pkappa2"])

    pcap_proc = setup_pcap_capture(cfg["pcap"], cfg["pkappa2"])

    log.info("=" * 60)
    log.info("Setup complete! Log saved to %s", LOG_FILE)
    log.info("=" * 60)

    return pcap_proc


if __name__ == "__main__":
    main()