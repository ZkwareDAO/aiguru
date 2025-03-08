def day_of_year(year,month,day):
    total = 0
    if year%4==0 and year%100 != 0:
        max_day=366
        print("这是闰年")
    elif year%400 == 0:
        max_day=366
        print("这是闰年")
    else:
        max_day=365
        print("这不是闰年")
    if month == 1:
        total =0+day
    if month == 2:
        total =31+day
    if max_day==366:
        Basicday = 29+31
    elif max_day == 365:
        Basicday = 28+31
    if month==3:
        total=Basicday+z
    if month == 4 or month == 5 or month == 6 or month ==7:
        if month%2==0:
            total = Basicday +31 + (month-2)/2 *31 + (month-2)/2 *30 -30 - 31 + day
        else:
            total = Basicday + (month-1)/2 *31 + (month-1)/2 *30 - 30- 31 + day
    if month ==8:
        total = Basicday + 31*3 + 30*2 + day
    if month==9 or month==10 or month==11 or month==12:
        if month%2==0:
            total = Basicday +(month/2)*31 +(month/2-1)*30-30-31+day
        else:
            total = Basicday+((month-1)/2-1) *30 +((month-1)/2+1) *31-30-31+day
    print(total)
    return day
x=int(input("Year: "))
y=int(input("month: "))
z=int(input("day: "))
q=day_of_year(x ,y ,z)
print(q)
