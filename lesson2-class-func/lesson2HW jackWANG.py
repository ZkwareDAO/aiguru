yearinput=int(input("年份："))
monthinput=int(input("月份："))
dayinput=int(input("日："))
def dayofyear (numofyear,month,day):
    for i in range(month):
        if i==1 or i==3 or i==5 or i==7 or i==8 or i==10 or i==12:
            day+=day
        elif i==2:
            day=day-2
    print(int(bool(numofyear%4==0))+30*month+day)

dayofyear(yearinput,monthinput,dayinput)