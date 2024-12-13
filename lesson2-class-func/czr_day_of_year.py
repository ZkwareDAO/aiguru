def day_of_year(x,y,z):
    day=0
    if x%4==0 and x%100 != 0:
        max_day=366
        print("这是闰年")
    elif x%400 == 0:
        max_day=366
        print("这是闰年")
    else:
        max_day=365
        print("这不是闰年")
    if y == 1:
        day =0+z
    if y == 2:
        day =31+z
    if max_day==366:
        Basicday = 29+31
    elif max_day == 365:
        Basicday = 28+31
    if y==3:
        day=Basicday+z
    if y ==4 or y==5 or y==6 or y==7:
        if y%2==0:
            day = Basicday +31 +(y-2)/2 *31 +(y-2)/2 *30-30-31+z
        else:
            day = Basicday +(y-1)/2 *31 +(y-1)/2 *30-30-31+z
    if y==8:
        day = Basicday + 31*3+30*2+z
    if y==9 or y==10 or y==11 or y==12:
        if y%2==0:
            day = Basicday +(y/2)*31 +(y/2-1)*30-30-31+z
        else:
            day = Basicday+((y-1)/2-1) *30 +((y-1)/2+1) *31-30-31+z
    print(x, y, z)
    print(day)
    return day
x=int(input("Year: "))
y=int(input("month: "))
z=int(input("day: "))
q=day_of_year(x ,y ,z)
print(q)
