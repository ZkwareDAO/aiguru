def is_leap_year(year) -> bool:
    if year % 4 != 0:
        return False
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return True

print(is_leap_year(2104))
def get_day_of_year(year, month, day) -> int:
    big_months = (month-month%2)//2
    if month > 8:
        big_months = big_months+1
    small_months = month - 1 - big_months
    xday = small_months*30+big_months*31+day
    feberuray_days = 28
    if is_leap_year(year):
        feberuray_days = 29
    if month > 2:
        xday = xday - (30-feberuray_days)
    return xday

print(get_day_of_year(2024, 7, 7))