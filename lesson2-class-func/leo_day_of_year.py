days=[0,31,28,31,30,31,30,31,31,30,31,30]
nian=int(input("Year: "))
yue=int(input("month: "))
ri=int(input("day: "))
def runy(y)->bool:
    if y%4!=0:
        return False
    elif y%400==0:
        return True
    elif y%100==0:
        return False
    return True
def cal_days(d,m):
    baisicday=0
    for day in days:
        if  int(days.index(int(day)))<=m:
            baisicday+= int(day) 
    baisicday+=d
    return int(baisicday)
baisicday2=cal_days(ri,yue)
runy2=runy(nian)
if runy2 and yue>2:
    baisicday2+=1
print(baisicday2)






        