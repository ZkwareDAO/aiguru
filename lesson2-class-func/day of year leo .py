def daycount(d,m,y):
    day=0
    if m<=2:
        m1=m-1
        if m1%2==0:
            day=d
        else:
            day=d+(m1//2)*(30+31)+31
    elif m<=7:
        m1=m-1
        if m1%2==0:
            if y%4==0 and y%100!=0:
                day=d+(m1//2)*(30+31)-1
                print("run")
            elif y%400==0:
                day=d+(m1//2)*(30+31)-1
                print("run")
            else:
                day=d+(m1//2)*(30+31)-2
                print("burun")
        elif m1%2==1:
            if y%4==0 and y%100!=0:
                day=d+(m1//2)*(30+31)-1+31
                print("run")
            elif y%400==0:
                day=d+(m1//2)*(30+31)-1+31
                print("run")
            else:
                day=d+(m1//2)*(30+31)-2+31
                print("burun")
        print("上半年不加天")
    elif m>7:
        m1=m-8
        print("下半年减月",m1)
        if m1%2==0:
            if y%4==0 and y%100!=0:
                day=d+(m1//2)*(30+31)-1
                print("run")
            elif y%400==0:
                day=d+(m1//2)*(30+31)-1
                print("run")
            else:
                day=d+(m1//2)*(30+31)-2
                print("burun")
        elif m1%2==1:
            if y%4==0 and y%100!=0:
                day=d+(m1//2)*(30+31)-1+31
                print("run")
            elif y%400==0:
                day=d+(m1//2)*(30+31)-1+31
                print("run")
            else:
                day=d+(m1//2)*(30+31)-2+31
                print("burun")
        day+=214
        print("下半年")
    print("this is the ",day,"th day of this year")
d=int(input("the day:"))
m=int(input("the month:"))
y=int(input("the year:"))
print(daycount(d,m,y))

