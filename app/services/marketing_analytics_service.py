"""Mock marketing performance data shared by the dashboard and agent tools."""

from copy import deepcopy


MOCK_MARKETING_ANALYTICS = {
    "period": "2026-10",
    "summary": {
        "impressions": 128400,
        "engagements": 18460,
        "clicks": 6240,
        "conversions": 518,
        "engagementRate": 14.38,
        "clickThroughRate": 4.86,
        "conversionRate": 8.30,
    },
    "trend": [
        {"date": "10/01", "impressions": 12800, "engagements": 1730, "conversions": 42},
        {"date": "10/05", "impressions": 16400, "engagements": 2480, "conversions": 61},
        {"date": "10/09", "impressions": 18100, "engagements": 2760, "conversions": 82},
        {"date": "10/13", "impressions": 15300, "engagements": 2190, "conversions": 70},
        {"date": "10/17", "impressions": 22500, "engagements": 3490, "conversions": 104},
        {"date": "10/21", "impressions": 19400, "engagements": 2740, "conversions": 78},
        {"date": "10/25", "impressions": 24400, "engagements": 3510, "conversions": 81},
        {"date": "10/29", "impressions": 19500, "engagements": 1560, "conversions": 0},
    ],
    "platforms": [
        {"platform": "小红书", "impressions": 48200, "engagements": 8910, "clicks": 2430, "conversions": 238, "engagementRate": 18.49, "conversionRate": 9.79},
        {"platform": "微信公众号", "impressions": 35700, "engagements": 4210, "clicks": 2120, "conversions": 177, "engagementRate": 11.79, "conversionRate": 8.35},
        {"platform": "抖音", "impressions": 44500, "engagements": 5340, "clicks": 1690, "conversions": 103, "engagementRate": 12.00, "conversionRate": 6.09},
    ],
    "topContent": [
        {"title": "每天 10 分钟，建立更稳定的护肤习惯", "platform": "小红书", "impressions": 18600, "engagements": 3920, "conversions": 112},
        {"title": "换季护肤常见误区：先看懂成分表", "platform": "微信公众号", "impressions": 14200, "engagements": 1830, "conversions": 86},
        {"title": "三步完成晚间清洁", "platform": "抖音", "impressions": 16800, "engagements": 2190, "conversions": 49},
    ],
}


def get_mock_marketing_analytics() -> dict:
    return deepcopy(MOCK_MARKETING_ANALYTICS)
