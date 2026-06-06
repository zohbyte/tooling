#!/usr/bin/env python3
"""
AD framework setup script.
Prepares workspaces, backs up services, installs tooling, and starts Tulip + pcap capture.
"""
import fnmatch
import logging
import os
import secrets
import shutil
import stat
import subprocess
import syss
import time
from pathlib import Path

# Paths
BASE_DIR         = Path(__file__).parent.resolve()
if os.name == "nt":
    # Windows path compatibility for CTF host environment
    SERVICES_ROOT    = Path("C:/services")
    WORKSPACES_ROOT  = Path.home() / "workspaces"
    BACKUPS_ROOT     = Path.home() / "backups"
    BIN_PATH         = Path(os.environ.get("USERPROFILE", "C:/Users/Default")) / "bin"
    PCAP_DIR         = Path.home() / "pcaps"
    LOG_FILE         = BASE_DIR / "setup.log"
else:
    SERVICES_ROOT    = Path("/services")
    WORKSPACES_ROOT  = Path("/root/workspaces")
    BACKUPS_ROOT     = Path("/root/backups")s
    BIN_PATH         = Path("/usr/local/bin")
    PCAP_DIR         = Path("/root/pcaps")
    LOG_FILE         = Path("/root/setup.log")
BIN_DIR          = BASE_DIR / "bin"
EXPLOIT_TEMPLATE = BASE_DIR / "templates" / "exploit.py"
TULIP_DIR        = BASE_DIR / "tulip"
TULIP_TRAFFIC_DIR = BASE_DIR / "tulip_traffic"

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
        "tulip": {
            "ip":       "127.0.0.1", # Optional: set to container IP or hostname if not running on localhost
            "frontend_port": 3000,
            "api_port": 5000,
            "user":     "admin",    
            "password": secrets.token_hex(16),
            "traffic_dir": str(TULIP_TRAFFIC_DIR),
            "tick_start": "2026-03-29T13:00:00Z", # Optional: set to CTF start time or network open time; defaults to now
            "tick_length": 180000,
            "flag_regex": "[A-Z0-9]{31}=",
            "vm_ip": "10.100.3.1", # Optional VM IP for flag validation context; set to "
            "team_id": 3, # Optional team ID for flag validation context; set to 0 or leave unset if not applicable
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
    if os.name == "nt" and name == "tcpdump":
        log.warning("Skipping tcpdump check on Windows (not usually available)")
        return
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

    if not BIN_PATH.exists():
        log.info("Creating bin path %s", BIN_PATH)
        BIN_PATH.mkdir(parents=True, exist_ok=True)

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


def setup_tulip(cfg: dict) -> None:
    log.info("Setting up Tulip...")
    require_tool("docker")
    require_tool("git")

    if not TULIP_DIR.exists():
        log.error("Tulip directory %s does not exist.", TULIP_DIR)
        return

    # Update repository
    try:
        run(["git", "pull"], cwd=TULIP_DIR)
        log.info("Updated Tulip repository")
    except subprocess.CalledProcessError as exc:
        log.warning("git pull failed: %s", exc)

    traffic_dir = Path(cfg["traffic_dir"])
    traffic_dir.mkdir(parents=True, exist_ok=True)

    try:
        os.chmod(traffic_dir, 0o777)
    except Exception:
        pass

    env_path = TULIP_DIR / ".env"

    env = {
        "TIMESCALE": "postgres://tulip@timescale:5432/tulip",
        "TRAFFIC_DIR_HOST": str(traffic_dir),
        "TRAFFIC_DIR_DOCKER": "/traffic",
        "TULIP_AUTH_USERNAME": cfg["user"],
        "TULIP_AUTH_PASSWORD": cfg["password"],
        "TICK_START": cfg["tick_start"],
        "TICK_LENGTH": str(cfg["tick_length"]),
        "FLAG_REGEX": cfg["flag_regex"],
        "VM_IP": cfg.get("vm_ip", ""),
        "TEAM_ID": cfg.get("team_id", ""),
    }

    existing_env = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing_env[k.strip()] = v.strip().strip('"')

    existing_env.update(env)

    env_path.write_text(
        "\n".join(f'{k}="{v}"' for k, v in existing_env.items()) + "\n"
    )

    inject_tulip_api_basic_auth(
        TULIP_DIR,
        cfg["user"],
        cfg["password"]
    )

    # Stop existing containers
    try:
        run(
            [
                "docker",
                "compose",
                "down",
                "--remove-orphans"
            ],
            cwd=TULIP_DIR
        )
        log.info("Stopped existing Tulip containers")
    except subprocess.CalledProcessError:
        pass

    # Rebuild images without deleting volumes
    run(
        [
            "docker",
            "compose",
            "build",
            "--pull"
        ],
        cwd=TULIP_DIR
    )

    # Recreate containers
    run(
        [
            "docker",
            "compose",
            "up",
            "-d",
            "--force-recreate"
        ],
        cwd=TULIP_DIR
    )

    # Show status
    subprocess.run(
        ["docker", "compose", "ps"],
        cwd=TULIP_DIR
    )

    _wait_for_tulip(cfg)

    log.info(
        "Tulip ready. User: %s Password: %s",
        cfg["user"],
        cfg["password"]
    )


def _wait_for_path(path: Path, timeout: int = 15) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.5)


def _wait_for_tulip(cfg: dict, timeout: int = 60) -> None:
    """Poll Tulip frontend endpoint until it responds or we give up."""
    url = f"http://{cfg['ip']}:{cfg['frontend_port']}/"
    log.info("Waiting for tulip at %s ...", url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["curl", "--silent", "--max-time", "2", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() not in ("", "000"):
            log.info("tulip is up (HTTP %s).", result.stdout.strip())
            return
        time.sleep(2)
    log.warning("tulip did not respond within %ds — first pcap upload may fail.", timeout)


def inject_tulip_api_basic_auth(tulip_dir: Path, username: str, password: str) -> bool:
    api_file = tulip_dir / "services" / "api" / "webservice.py"
    if not api_file.exists():
        log.warning("Tulip API webservice.py not found, skipping auth injection")
        return False

    content = api_file.read_text()
    if "TULIP_AUTH_USERNAME" in content and "@application.before_request" in content:
        return False

    insert_marker = "from flask import Flask, Response, send_file"
    if insert_marker not in content:
        return False

    new_imports = """from flask import Flask, Response, send_file, request\nimport base64\n"""
    content = content.replace(insert_marker, new_imports, 1)

    auth_code = """

TULIP_AUTH_USERNAME = os.getenv('TULIP_AUTH_USERNAME', '%s')
TULIP_AUTH_PASSWORD = os.getenv('TULIP_AUTH_PASSWORD', '%s')


def _check_tulip_auth(auth_header):
    if not TULIP_AUTH_USERNAME or not TULIP_AUTH_PASSWORD:
        return True
    if not auth_header or not auth_header.startswith('Basic '):
        return False
    try:
        encoded = auth_header.split(' ', 1)[1]
        decoded = base64.b64decode(encoded).decode('utf-8')
        user, pwd = decoded.split(':', 1)
    except Exception:
        return False
    return user == TULIP_AUTH_USERNAME and pwd == TULIP_AUTH_PASSWORD


@application.before_request
def tulip_require_auth():
    if not TULIP_AUTH_USERNAME or not TULIP_AUTH_PASSWORD:
        return
    if request.path.startswith('/favicon.ico'):
        return
    if request.path.startswith('/static/'):
        return
    if not _check_tulip_auth(request.headers.get('Authorization')):
        return Response('Unauthorized', status=401, headers={'WWW-Authenticate': 'Basic realm="Tulip"'})
""" % (username, password)

    # Insert auth_code after import section and before routes
    if "application = Flask(__name__)" in content:
        content = content.replace("application = Flask(__name__)", "application = Flask(__name__)\n" + auth_code, 1)
        api_file.write_text(content)
        return True

    return False


def _wait_for_pkappa2(cfg: dict, timeout: int = 30) -> None:
    """Legacy helper left for compatibility; use _wait_for_tulip instead."""
    _wait_for_tulip(cfg, timeout)


def setup_pcap_capture(pcap_cfg: dict, tulip_cfg: dict) -> subprocess.Popen | None:
    """Write the local traffic copy callback script and launch tcpdump."""
    if os.name == "nt":
        log.warning("Skipping pcap capture setup on Windows host")
        return None

    require_tool("tcpdump")

    PCAP_DIR.mkdir(parents=True, exist_ok=True)

    tulip_traffic = Path(tulip_cfg.get("traffic_dir", str(TULIP_TRAFFIC_DIR)))
    tulip_traffic.mkdir(parents=True, exist_ok=True)

    callback = Path("/root/tcpdump_complete.sh")
    callback.write_text(f"""\
#!/bin/bash
PCAP="$1"
FILENAME=$(basename "$PCAP")
DEST="{tulip_traffic}/$FILENAME"
echo "[pcap] Saving $FILENAME to Tulip traffic dir"
cp "$PCAP" "$DEST" \
    && rm "$PCAP" \
    && echo "[pcap] Saved: $FILENAME" \
    || echo "[pcap] Failed: $FILENAME"
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
    setup_tulip(cfg["tulip"])

    pcap_proc = setup_pcap_capture(cfg["pcap"], cfg["tulip"])

    log.info("=" * 60)
    log.info("Setup complete! Log saved to %s", LOG_FILE)
    log.info("=" * 60)

    return pcap_proc


if __name__ == "__main__":
    main()