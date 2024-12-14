months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
def isrun(year):
    if (year % 400 == 0 and year % 100 == 0):
        return 1
    else:
        if (year % 4 == 0 and year % 100 != 0):
            return 1
        else:
            return 0
def cal(day, month):
    total = 0
    for i in range(0, month-1):
        total += months[i]
    total += day
    print("这是这一年的第",total,"天")
def inpt():
    judge = 0
    while (judge == 0):
        months[1] = 29
        day = int(input("日:"))
        month = int(input("月:"))
        year = int(input("年:"))
        run = isrun(year)
        if (run != 1):
            months[1] = 28
        if (month > 12 or month < 1):
            print("该日期不存在")
        else: 
            if (months[month-1] < day or day < 1):
                print("该日期不存在")
            else:
                judge = 1
    cal(day, month)
inpt()