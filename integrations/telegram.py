import os
import json
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")


# ── PLAIN TEXT (legacy) ───────────────────────────────────────────────────────

def send(message: str, chat_id: str = None) -> bool:
    _chat_id = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not _chat_id:
        print("  [!] Telegram not configured — skipping send.")
        return False
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    ok = True
    for chunk in chunks:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": _chat_id, "text": chunk},
                timeout=10,
            )
            if r.status_code != 200:
                print(f"  [!] Telegram {r.status_code}: {r.text[:100]}")
                ok = False
        except Exception as e:
            print(f"  [!] Telegram error: {e}")
            ok = False
    return ok


# ── RICH TEXT BUILDERS ────────────────────────────────────────────────────────

def rt(text: str, *, bold=False, italic=False, code=False, url=None) -> dict:
    """Build a RichText node."""
    d: dict = {"text": text}
    if bold:      d["bold"]   = True
    if italic:    d["italic"] = True
    if code:      d["code"]   = True
    if url:       d["url"]    = url
    return d


def block_heading(text: str) -> dict:
    """RichBlockSectionHeading wrapped in InputRichBlock."""
    return {"section_heading": {"section_heading": rt(text)}}


def block_paragraph(*rich_texts) -> dict:
    """RichBlockParagraph. Accepts str or rt() dicts."""
    items = [t if isinstance(t, dict) else rt(t) for t in rich_texts]
    return {"paragraph": {"paragraph": items}}


def block_list(items: list, ordered: bool = False) -> dict:
    """
    RichBlockList. Each item can be:
      - str                   → single RichText
      - dict (rt())           → single RichText
      - list of rt()          → multi-span content
      - (content, nested)     → tuple with nested RichBlockList payload
    """
    list_items = []
    for item in items:
        if isinstance(item, tuple):
            content_raw, nested = item
        else:
            content_raw, nested = item, None

        if isinstance(content_raw, str):
            content = [rt(content_raw)]
        elif isinstance(content_raw, dict):
            content = [content_raw]
        else:
            content = content_raw

        entry: dict = {"content": content}
        if nested:
            entry["nested"] = nested
        list_items.append(entry)

    b: dict = {"list": list_items}
    if ordered:
        b["ordered"] = True
    return {"list": b}


def block_table(rows: list[list], header_row: bool = False) -> dict:
    """
    RichBlockTable. rows is a 2-D list of str or rt() dicts.
    If header_row=True the first row cells get header=True.
    """
    cells = []
    for i, row in enumerate(rows):
        row_cells = []
        for cell in row:
            content = [rt(cell) if isinstance(cell, str) else cell]
            entry: dict = {"content": content}
            if header_row and i == 0:
                entry["header"] = True
            row_cells.append(entry)
        cells.append(row_cells)
    return {"table": {"table": cells}}


def block_divider() -> dict:
    return {"divider": {}}


# ── SEND RICH ─────────────────────────────────────────────────────────────────

def send_rich(blocks: list, chat_id: str = None,
              disable_notification: bool = False) -> bool:
    """Send a Bot API 10.1 rich message."""
    _chat_id = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not _chat_id:
        print("  [!] Telegram not configured — skipping send_rich.")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendRichMessage",
            json={
                "chat_id": _chat_id,
                "rich_message": {"blocks": blocks},
                "disable_notification": disable_notification,
            },
            timeout=15,
        )
        if r.status_code != 200:
            print(f"  [!] sendRichMessage {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  [!] sendRichMessage error: {e}")
        return False


def send_rich_voice(ogg_path: str, blocks: list = None,
                    chat_id: str = None) -> bool:
    """
    Send a rich message with an embedded voice note block (Bot API 10.1).
    Voice note is the first block; optional extra blocks follow.
    """
    _chat_id = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not _chat_id:
        print("  [!] Telegram not configured — skipping send_rich_voice.")
        return False

    all_blocks = [{"voice_note": {"voice_note": "attach://arcus_voice"}}]
    if blocks:
        all_blocks += blocks

    try:
        with open(ogg_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendRichMessage",
                data={
                    "chat_id": _chat_id,
                    "rich_message": json.dumps({"blocks": all_blocks}),
                },
                files={"arcus_voice": ("arcus.ogg", f, "audio/ogg")},
                timeout=20,
            )
        if r.status_code != 200:
            print(f"  [!] sendRichMessage(voice) {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  [!] sendRichMessage(voice) error: {e}")
        return False
