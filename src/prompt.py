"""
Prompt 系统 — 定义 AI 生成早报的模板和指令
"""

# ═══════════════════════════════════════════════════
# 系统级指令（角色定位 + 核心约束）
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = """你是一位专业的短线交易策略分析师。你的任务是撰写每日「盘前作战地图」早报。

## 你的定位
- 服务于有一定经验的个人投资者
- 提供可执行的量化锚点，而非模糊的市场评论
- 数据驱动，言之有据

## 核心纪律
1. 所有数据必须基于用户提供的原始数据，不得自行编造
2. 情景清单必须包含具体量化条件，禁止模糊表述
3. 每个交易动作必须附带止损/放弃条件
4. 不得推荐具体买卖操作，只提供情景框架
5. 必须标注统计样本量和置信度

## 禁止事项
- 不使用"可能""大概""或许"等模糊词汇
- 不写套话、空话
- 不编造数据
- 不预测无法预测的事件"""


# ═══════════════════════════════════════════════════
# 早报生成指令
# ═══════════════════════════════════════════════════

BRIEF_TEMPLATE = """今天是 {date}，{weekday}。

请根据以下数据，按照要求的格式生成一份完整的「盘前作战地图」。

---
## 📊 数据摘要

### 隔夜外盘
{us_market_summary}

### A50期货
{a50_summary}

### A股盘前
{a_share_summary}

### 资金流向
{capital_flow}

### 限售股解禁
{unlock_summary}

### 开盘锚点模型
{model_summary}

### 今日重大新闻
{news_summary}

---
## 格式要求

请严格按照以下板块输出：

### 一、核心情绪与预期校准

用一个表格展示开盘锚点的多源推导：

| 锚点来源 | 指标状态 | 推导结论 |
|:---|:---|:---|
| A50隔夜联动 | ... | 公式 + R² + 置信区间 |
| 隔夜中概股 | ... | 对科技风格的支撑判断 |
| ... | ... | ... |

**结论**：一句话判断今天开盘情绪。

### 二、今日核心博弈方向

从新闻中选取最重要的1-2个事件做映射分析。

格式参考：
**【事件】** 一句话概述
**【映射锚点】** 传导逻辑说明
**【历史回溯】** N次类似事件的统计表现（N值、中位数、上下四分位）
**【情景清单】** 以表格输出：

| 情景 | 确认条件 | 应对动作 |
|:---|:---|:---|
| 强势 | 条件A + 条件B | 买入/观望/放弃 |
| 常态 | 条件 | 动作 |
| 不及预期 | 条件 | 动作 |

### 三、风险与避坑清单

- **具体风险1**（个股/板块 + 原因）
- **具体风险2**（个股/板块 + 原因）
- 解禁个股提醒（如有）

### 四、重点关注

| 时间 | 事件 | 影响评级 |
|:---|:---|:---:|
| 日期 | 事件 | ⭐⭐⭐ |

### 五、📖 指标说明

- **R²**：模型解释了多少实际走势（越接近1越准）
- **β**：A50每涨1%，沪指开盘平均跟涨多少%
- **N**：统计样本量（N≥30参考价值较高，N<30仅供观察）
- **置信区间**：真实值有95%概率落在此范围内

---
⚠️ 本早报所有推演均基于历史统计与公开信息，无法预测突发事件。所有情景概率仅为辅助决策，不构成确定性投资建议。请严格遵循自身交易纪律。"""


def build_prompt(data: dict) -> str:
    """根据采集的数据构建完整的 Prompt"""

    # 外盘
    us_lines = []
    for name, d in data.get("us_market", {}).items():
        cp = d.get("change_pct")
        if cp is not None:
            arrow = "📈" if cp >= 0 else "📉"
            price_str = f" {d['price']}" if d.get("price") else ""
            us_lines.append(f"{arrow} {name}{price_str}: {cp:+.2f}%")
    us_market_summary = "\n".join(us_lines) if us_lines else "暂无数据"

    # A50
    a50 = data.get("a50")
    if a50 and a50.get("change_pct") is not None:
        a50_summary = f"A50期货: {a50.get('price', 'N/A')}  ({a50['change_pct']:+.2f}%)"
    else:
        a50_summary = "A50期货: 暂无数据"

    # A股
    a_share_summary = "\n".join(
        f"{n}: {d['price']} ({d['change_pct']:+.2f}%)"
        for n, d in data.get("a_share", {}).items()
    ) if data.get("a_share") else "暂无数据"

    # 资金
    capital_flow = data.get("capital_flow", "暂无数据")

    # 解禁
    unlock = data.get("unlock", [])
    if unlock:
        unlock_summary = "\n".join(
            f"- {u['name']}({u['code']}) {u['date']} 解禁{u['ratio']}"
            for u in unlock[:5]
        )
    else:
        unlock_summary = "暂无近期限售股解禁"

    # 模型
    model = data.get("anchor_model")
    model_summary = model.summary() if model else "暂无历史数据"

    # 新闻
    news_list = data.get("major_news", data.get("news", []))[:8]
    if news_list:
        news_summary = "\n".join(
            f"- [{n.source}] {n.title}" for n in news_list
        )
    else:
        news_summary = "暂无重大新闻"

    # 日期
    now = data.get("now")
    if now:
        date = now.strftime("%Y-%m-%d")
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekdays[now.weekday()]
    else:
        date = ""
        weekday = ""

    return BRIEF_TEMPLATE.format(
        date=date,
        weekday=weekday,
        us_market_summary=us_market_summary,
        a50_summary=a50_summary,
        a_share_summary=a_share_summary,
        capital_flow=capital_flow,
        unlock_summary=unlock_summary,
        model_summary=model_summary,
        news_summary=news_summary,
    )
