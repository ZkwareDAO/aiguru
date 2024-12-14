def daycount(d,m,y):
    day=0
    if m<=2:
        m-=1
        if m%2==0:
            day=d
        else:
            day=d+(m//2)*(30+31)+31
    elif m<=7:
        m-=1
        if m%2==0:
            if y%4==0:
                day=d+(m//2)*(30+31)-1
            else:
                day=d+(m//2)*(30+31)-2
        elif m%2==1:
            if y%4==0:
                day=d+(m//2)*(30+31)-1+31
            else:
                day=d+(m//2)*(30+31)-2+31
    elif m>7:
        m-=8
        if m%2==0:
            if y%4==0:
                day=d+(m//2)*(30+31)-1+31
            else:
                day=d+(m//2)*(30+31)-2+31
        elif m%2==1:
            if y%4==0:
                day=d+(m//2)*(30+31)-1
            else:
                day=d+(m//2)*(30+31)-2
    print("this is the ",day,"th day of this year")
d=int(input("the day:"))
m=int(input("the month:"))
y=int(input("the year:"))
print(daycount(d,m,y))

