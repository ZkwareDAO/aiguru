import streamlit as st
import pandas as pd

st.title("Hello world")
st.header(":)")
st.subheader("QWERTY")

st.markdown("# QWERTY.WEB")
st.markdown("this is my first web page")
st.caption("??")

code1 = """
def is_leap_year(year):
    if year % 4 != 0:
        return False
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return True
def totaldays(year ,month ,day):
    feb_days = is_leap_year(year) + 28
    list_of_month = [0 ,31 ,feb_days ,31 ,30 ,31 ,30 ,31 ,31 ,30 ,31 ,30 ,31]
    sum = 0
    for i in range(0, month):
        sum += list_of_month[i]
    sum += day
    print(sum)
    return sum
year=int(input("year: "))
month=int(input("month: "))
day=int(input("day: "))
print(totaldays(year,month,day))
"""
st.code(code1, language= "python")
st.divider()

def is_leap_year(year):
    if year % 4 != 0:
        return False
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return True
def totaldays(year ,month ,day):
    feb_days = is_leap_year(year) + 28
    list_of_month = [0 ,31 ,feb_days ,31 ,30 ,31 ,30 ,31 ,31 ,30 ,31 ,30 ,31]
    sum = 0
    for i in range(0, month):
        sum += list_of_month[i]
    sum += day
    print(sum)
    return sum

df = pd.DataFrame({
    "Year": [0,0,0],
    "Month": [0,0,0],
    "Day": [0,0,0],
})
st.dataframe(df)
edited_df = st.data_editor(df)
print(edited_df)
print(df.iloc[0,0])
print(df["Year"].values[0])
for i in range(0,3):
    st.metric(label="The day of year: ", value=totaldays(edited_df["Year"].values[i], edited_df["Month"].values[i], edited_df["Day"].values[i] ))