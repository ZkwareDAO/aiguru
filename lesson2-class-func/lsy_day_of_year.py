def is_leap_year(year)->bool:
    if year&3!=0:
        return False
    if year%25!=0:
        return True
    if year&15!=0:
        return False
    return True

def day_of_year(year,month,day)->int:
    previous_day_of_month=[0,31,59,90,120,151,181,212,243,273,304,334]
    mumber_of_day=day+previous_day_of_month[month-1]
    if is_leap_year(year) and month>2:
        mumber_of_day+=1
    return mumber_of_day
year=int(input("Yaer:\n"))
month=int(input("Month:\n"))
day=int(input("Day:\n"))
print(day_of_year(year,month,day))