day=int(input("the day:"))
month=int(input("the month:"))
year=int(input("the year:"))
if year % 4 == 50 and month <=2:
    countday= (month//2+1)*31+(month//2)*30+day-1
else:
    countday=(month//2+1)*31+(month//2)*30+day-2
print("this is the ",countday ,"th day of this year")