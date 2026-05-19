"""
数据采集模块 — 采集早报所需的所有市场数据
"""

import datetime
import json
from dataclasses import dataclass
from typing import Optional

import feedparser
import numpy as np
import pandas as pd
import requests
import yfinance as yf

from config import Config

# ══════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════

@dataclass
class MarketSnapshot:
    """隔夜市场快照"""
    a50_change: Optional[float] = None       # A50期货涨跌幅(%)
    a50_price: Optional[float] = None
    us_change: Optional[float] = None        # 标普500涨跌幅(%)
    nasdaq_change: Optional[float] = None    # 纳斯达克涨跌幅(%)
    cci_change: Optional[float] = None       # 中概股指数涨跌幅(%)
    sh_index: Optional[float] = None         # 上证指数最新值
    
    @property
    def has_data(self) -> bool:
        return any(v is not None for v in [self.a50_change, self.us_change])


@dataclass
class NewsItem:
    title: str
    url: str
    summary: str
    source: str
    published: str
    lang: str = "zh"

    @property
    def is_major(self) -> bool:
        """判断是否可能是重大事件"""
        keywords = ["财报", "加息", "降息", "收购", "制裁", "禁令", "突发",
                    "earnings", "rate", "merger", "sanction", "break", "crash",
                    "Fed", "央行", "白宫", "特朗普", "关税", "tarrif"]
        title_lower = self.title.lower()
        return any(k.lower() in title_lower for k in keywords)


# ══════════════════════════════════════════
# RSS 新闻采集
# ══════════════════════════════════════════

RSS_FEEDS = {
    "华尔街见闻": {"url": "https://wallstreetcn.com/rss", "lang": "zh"},
    "CNBC": {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "lang": "en"},
    "MarketWatch": {"url": "https://feeds.marketwatch.com/marketwatch/topstories", "lang": "en"},
    "Yahoo Finance": {"url": "https://finance.yahoo.com/news/rssindex", "lang": "en"},
}

def fetch_rss() -> list[NewsItem]:
    """抓取所有RSS新闻"""
    items = []
    for name, conf in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(conf["url"])
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                summary = (entry.get("summary") or entry.get("description") or "").strip()
                summary = summary.replace("<p>", "").replace("</p>", "\n").replace("<br>", "\n")
                items.append(NewsItem(
                    title=title, url=entry.get("link", ""),
                    summary=summary[:300], source=name,
                    published=entry.get("published", ""),
                    lang=conf["lang"],
                ))
        except Exception as e:
            print(f"  ⚠️ {name} RSS失败: {e}")
    return items


# ══════════════════════════════════════════
# 隔夜外盘数据
# ══════════════════════════════════════════

US_TICKERS = {
    "标普500": "^GSPC",
    "纳斯达克": "^IXIC",
    "道琼斯": "^DJI",
}

CHINA_ADR_TICKERS = {
    "中概互联ETF": "KWEB",
    "阿里巴巴": "BABA",
    "拼多多": "PDD",
    "百度": "BIDU",
}

def fetch_us_market() -> dict:
    """获取美股指数 + 中概股隔夜数据"""
    result = {}
    try:
        # 美股指数
        for name, ticker in US_TICKERS.items():
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2]
                change_pct = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
                result[name] = {"price": round(latest["Close"], 2), "change_pct": change_pct}

        # 中概股综合信号
        changes = []
        for name, ticker in CHINA_ADR_TICKERS.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
                if len(hist) >= 2:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    cp = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
                    result[name] = {"price": round(latest["Close"], 2), "change_pct": cp}
                    changes.append(cp)
            except:
                pass
        if changes:
            result["中概股综合"] = {"price": None, "change_pct": round(np.mean(changes), 2)}
    except Exception as e:
        print(f"⚠️ 美股数据获取失败: {e}")
    return result


# ══════════════════════════════════════════
# A50 期货数据
# ══════════════════════════════════════════

def fetch_a50_futures() -> Optional[dict]:
    """获取A50/中国大盘股隔夜表现（用FXI作为替代）"""
    # 方案1: FXI (iShares China Large-Cap ETF, 纽交所上市)
    try:
        t = yf.Ticker("FXI")
        hist = t.history(period="5d")
        if len(hist) >= 2:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]
            change_pct = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
            return {"price": round(latest["Close"], 2), "change_pct": change_pct, "source": "FXI"}
    except:
        pass

    # 方案2: ASHR (沪深300 ETF, 纽交所上市)
    try:
        t = yf.Ticker("ASHR")
        hist = t.history(period="5d")
        if len(hist) >= 2:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]
            change_pct = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
            return {"price": round(latest["Close"], 2), "change_pct": change_pct, "source": "ASHR"}
    except:
        pass

    # 方案3: 用已获取的沪深300指数日线数据计算
    try:
        hs300 = yf.Ticker("000300.SS")
        hist = hs300.history(period="5d")
        if len(hist) >= 2:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]
            change_pct = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
            return {"price": round(latest["Close"], 2), "change_pct": change_pct, "source": "CSI300"}
    except:
        pass

    return None


# ══════════════════════════════════════════
# A股实时数据
# ══════════════════════════════════════════

SINA_API = "https://hq.sinajs.cn/list="
A_SHARE_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "沪深300": "sh000300",
}

def fetch_a_share() -> dict:
    """获取A股主要指数"""
    result = {}
    try:
        codes = ",".join(A_SHARE_CODES.values())
        resp = requests.get(SINA_API + codes, headers={
            "User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn",
        }, timeout=10)
        resp.encoding = "gbk"
        for line in resp.text.strip().split("\n"):
            if "=" not in line or "\"" not in line:
                continue
            data_str = line.split("\"")[1]
            fields = data_str.split(",")
            if len(fields) < 4:
                continue
            name = fields[0].strip()
            if not name:
                continue
            code_part = line.split("=")[0].split("_")[-1].strip()
            orig_key = next((k for k, v in A_SHARE_CODES.items() if v == code_part), name)
            try:
                price = float(fields[1])
                change_amt = float(fields[2]) if fields[2] else 0.0
                change_pct = float(fields[3].replace("%", "")) if "%" in fields[3] else 0.0
                if abs(change_pct) > 15:
                    change_pct = 0.0
                    change_amt = 0.0
                result[orig_key] = {"price": price, "change_pct": change_pct, "change": change_amt}
            except (ValueError, IndexError):
                pass
    except Exception as e:
        print(f"⚠️ A股数据获取失败: {e}")
    return result


# ══════════════════════════════════════════
# 资金流向 & 解禁数据 (akshare)
# ══════════════════════════════════════════

def fetch_capital_flows() -> Optional[str]:
    """获取北向资金净流入/流出"""
    try:
        import akshare as ak
        df = ak.stock_hsgt_north_net_flow_in_em(symbol="沪股通")
        if not df.empty:
            latest = df.iloc[-1]
            return f"沪股通: {latest.get('value', 'N/A')}亿"
    except:
        pass
    try:
        import akshare as ak
        df = ak.stock_hsgt_north_flow_em()
        if not df.empty and len(df) >= 2:
            latest = df.iloc[-1]
            return f"北向资金: {latest.get('net_amount', 'N/A')}"
    except:
        pass
    return None


def fetch_unlock_data() -> list[dict]:
    """获取近期限售股解禁列表"""
    items = []
    try:
        import akshare as ak
        df = ak.stock_restricted_release_queue_sina()
        if not df.empty:
            today = datetime.date.today()
            for _, row in df.iterrows():
                try:
                    date_str = str(row.get("date", ""))[:10]
                    if date_str:
                        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                        if abs((d - today).days) <= 3:  # 前后3天
                            items.append({
                                "name": row.get("name", ""),
                                "code": row.get("code", ""),
                                "date": date_str,
                                "ratio": row.get("ratio", ""),
                            })
                except:
                    pass
    except:
        pass
    return items


# ══════════════════════════════════════════
# 历史数据 → 回归模型用
# ══════════════════════════════════════════

def fetch_hist_regression_data(days: int = 100) -> pd.DataFrame:
    """
    获取A50和沪指历史开盘数据，用于回归建模
    返回 DataFrame: columns = [date, a50_change, sh_open_change]
    """
    records = []
    
    # 获取沪指历史日线
    try:
        sh = yf.Ticker("000001.SS")
        sh_hist = sh.history(period=f"{days + 20}d")
    except:
        sh_hist = pd.DataFrame()
    
    # 获取沪深300作为A50代理的历史
    try:
        hs300 = yf.Ticker("000300.SS")
        hs300_hist = hs300.history(period=f"{days + 20}d")
    except:
        hs300_hist = pd.DataFrame()

    if sh_hist.empty or hs300_hist.empty:
        return pd.DataFrame(columns=["date", "a50_change", "sh_open_change"])

    # 计算每日涨跌幅
    sh_daily = sh_hist["Close"].pct_change() * 100
    hs300_daily = hs300_hist["Close"].pct_change() * 100

    # 对齐日期
    combined = pd.DataFrame({
        "sh_close": sh_hist["Close"],
        "sh_change": sh_daily,
        "a50_change": hs300_daily,
    }).dropna()

    combined = combined.tail(days)
    combined.index = combined.index.date
    combined.index.name = "date"
    combined.columns = ["sh_close", "sh_open_change", "a50_change"]

    return combined[["a50_change", "sh_open_change"]].dropna()


# ══════════════════════════════════════════
# 主采集入口
# ══════════════════════════════════════════

def collect_all(cfg: Config) -> dict:
    """采集所有数据，返回结构化数据包"""
    print("=" * 50)
    print("📡 采集隔夜市场数据...")
    print(f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    data = {}

    # 1. 美股 + 中概股
    print("\n🇺🇸 美股市场...")
    data["us_market"] = fetch_us_market()
    print(f"   ✅ {len(data['us_market'])} 项")

    # 2. A50
    print("\n📊 A50期货...")
    data["a50"] = fetch_a50_futures()
    if data["a50"]:
        print(f"   ✅ {data['a50']['change_pct']:+.2f}%")
    else:
        print("   ⚠️ 未获取到")

    # 3. A股
    print("\n🇨🇳 A股指数...")
    data["a_share"] = fetch_a_share()
    print(f"   ✅ {len(data['a_share'])} 个")

    # 4. 资金流向
    print("\n💰 北向资金...")
    data["capital_flow"] = fetch_capital_flows()
    print(f"   {'✅' if data['capital_flow'] else '⚠️'} {data.get('capital_flow', '无数据')}")

    # 5. 解禁数据
    print("\n🔓 限售股解禁...")
    data["unlock"] = fetch_unlock_data()
    print(f"   ✅ {len(data['unlock'])} 条")

    # 6. RSS新闻
    print("\n📰 新闻...")
    news = fetch_rss()
    data["news"] = news
    data["major_news"] = [n for n in news if n.is_major]
    print(f"   ✅ 共{len(news)}条，重大{len(data['major_news'])}条")

    # 7. 回归历史数据
    print("\n📈 回归历史数据...")
    data["regression_data"] = fetch_hist_regression_data(days=100)
    print(f"   ✅ {len(data['regression_data'])} 个交易日")

    print("\n" + "=" * 50)
    print("✅ 数据采集完成")
    print("=" * 50)
    return data
