def is_leap_year(year):
    if year % 4 != 0:
        return False
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return True
def totaldays(year ,month ,day):
    feb_days = is_leap_year(year) + 28
    list_of_month = [0 ,31 ,feb_days ,31 ,30 ,31 ,30 ,31 ,31 ,30 ,31 ,30 ,31]
    sum = 0
    for i in range(0, month):
        sum += list_of_month[i]
    sum += day
    print(sum)
    return sum
year=int(input("year: "))
month=int(input("month: "))
day=int(input("day: "))
print(totaldays(year,month,day))