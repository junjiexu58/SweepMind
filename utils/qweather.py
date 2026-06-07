import gzip
import json
import re
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from model.factory import chat_model
from utils.config_handler import agent_conf
from utils.logger_handler import logger
from utils.prompt_loader import load_location_extract_prompts

# 和风配置
QW_HOST = (agent_conf.get("qweather_api_host") or "").strip()
QW_API_KEY = (agent_conf.get("qweather_api_key") or "").strip()
QW_JWT_TOKEN = (agent_conf.get("qweather_jwt_token") or "").strip()
QW_TIMEOUT = float(agent_conf.get("qweather_timeout", 5))
QW_LANG = (agent_conf.get("qweather_lang") or "zh").strip()
QW_RANGE = (agent_conf.get("qweather_range") or "cn").strip()


def _normalize_qweather_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if host.startswith("http://") or host.startswith("https://"):
        return host
    return f"https://{host}"


def _extract_json_block(text: str) -> str:
    text = (text or "").strip()

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence_match:
        return fence_match.group(1)

    json_match = re.search(r"\{.*?\}", text, re.S)
    if json_match:
        return json_match.group(0)

    return ""


def qweather_get(path: str, params: dict) -> dict:
    base_url = _normalize_qweather_host(QW_HOST)
    if not base_url:
        raise ValueError("agent.yml中未配置 qweather_api_host")
    if not QW_API_KEY and not QW_JWT_TOKEN:
        raise ValueError("agent.yml中未配置 qweather_api_key 或 qweather_jwt_token")

    query = dict(params or {})
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Mozilla/5.0",
    }

    if QW_JWT_TOKEN:
        headers["Authorization"] = f"Bearer {QW_JWT_TOKEN}"
    else:
        query["key"] = QW_API_KEY

    url = f"{base_url}{path}?{urlencode(query)}"
    req = Request(url, headers=headers, method="GET")

    try:
        with urlopen(req, timeout=QW_TIMEOUT) as resp:
            raw = resp.read()
            content_encoding = (resp.headers.get("Content-Encoding") or "").lower()

            if "gzip" in content_encoding:
                raw = gzip.decompress(raw)
            elif "deflate" in content_encoding:
                raw = zlib.decompress(raw)
            elif raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)

            text = raw.decode("utf-8")
            return json.loads(text)

    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            err_body = ""
        raise RuntimeError(f"和风HTTP错误: {e.code}, body={err_body}") from e

    except URLError as e:
        raise RuntimeError(f"和风网络错误: {e.reason}") from e

    except json.JSONDecodeError as e:
        raise RuntimeError(f"和风返回内容不是合法JSON: {str(e)}") from e

    except Exception as e:
        raise RuntimeError(f"和风请求异常: {str(e)}") from e


def lookup_location_id(city_text: str) -> tuple[str, str]:
    geo = qweather_get(
        "/geo/v2/city/lookup",
        {
            "location": city_text,
            "range": QW_RANGE,
            "lang": QW_LANG,
            "number": 10,
        },
    )

    if geo.get("code") != "200" or not geo.get("location"):
        raise RuntimeError(f"城市搜索失败: {geo.get('code', 'unknown')}")

    first = geo["location"][0]
    resolved_city = first.get("name") or city_text
    location_id = first.get("id")

    if not location_id:
        raise RuntimeError("城市搜索成功但未返回 LocationID")

    return str(resolved_city), str(location_id)


def extract_city_info(user_query: str) -> str:
    prompt = load_location_extract_prompts().format(user_query=user_query).strip()
    try:
        resp = chat_model.invoke(prompt)
        content = getattr(resp, "content", str(resp)).strip()
        m = re.search(r'\{.*\}', content, re.S)
        if not m:
            return ""

        data = json.loads(m.group(0))
        city = (data.get("city") or "").strip()
        return city
    except Exception as e:
        logger.warning(f"[extract_city_info]提取失败 query={user_query} err={e}")
        return ""
