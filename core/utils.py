from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta


def calculate_months_to_goal(current_amount: Decimal, target_amount: Decimal,
                              monthly_saving: Decimal) -> int | None:
    """محاسبه تعداد ماه تا رسیدن به هدف"""
    if monthly_saving <= 0:
        return None
    remaining = target_amount - current_amount
    if remaining <= 0:
        return 0
    months = remaining / monthly_saving
    return int(months) + (1 if months % 1 > 0 else 0)


def calculate_savings_impact(monthly_amount: Decimal) -> dict:
    """محاسبه تأثیر پس‌انداز در بازه‌های مختلف"""
    return {
        '1_month': monthly_amount * 1,
        '6_months': monthly_amount * 6,
        '1_year': monthly_amount * 12,
        '5_years': monthly_amount * 60,
    }


def get_date_range(period: str) -> tuple[date, date]:
    """برگرداندن بازه تاریخی بر اساس دوره"""
    today = date.today()
    if period == 'daily':
        return today, today
    elif period == 'weekly':
        return today - relativedelta(weeks=1), today
    elif period == 'monthly':
        return today.replace(day=1), today
    elif period == 'yearly':
        return today.replace(month=1, day=1), today
    return today.replace(day=1), today