year=int(input("请输入年份"))
month=int(input("请输入月份"))
day=int(input("请输入日期"))
date_list=[31,29,31,30,31,30,31,31,30,31,30,31]
count_day=day
if year%4==0 and year%100!=0 or year%400==0:
    print(f'{year}年是闰年')
    date_list[1]=29
else:
    print(f'{yaer}年是平年')
    date_list[1]=28
for i in range(month-1):
    count_day +=date_list[i]

print(f'{year}年{month}月{day}日是当年的第{count_day}天')
