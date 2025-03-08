jyearinput=int(input("年份："))
monthinput=int(input("月份："))
dayinput=int(input("日："))
extra=int(0)
if monthinput>2 and ((yearinput%4==0 and yearinput%100!=0) or yearinput%400==0):
    extra=extra+1
def dayofyear (month,day,change):
    for i in range(int(month-1)):
        if i==1:
            change=change-2
        elif i==0 or i==2 or i==4 or i==6 or i==7 or i==9 or i==11:
            change=change+1
    print(30*(month-1)+day+change)
dayofyear(monthinput,dayinput,extra)

