#include <bits/stdc++.h>
using namespace std;
int sum;
int month[15]={0,31,28,31,30,31,30,31,31,30,31,30,31};//存储月份到month数组中
int main(){
	int y,m,d;//y年份，m月份，d天数
	cin>>y>>m>>d;
	if(y%4==0&&(y%100>0||y%400==0)){
		month[2]+=1;
	}
	for(int i=1;i<m;i++){
		sum+=month[i];//加入1到m-1月的天数
	}
	if(d>=month[m]){//判断天数是否溢出，如果溢出（如1月输入300天）则直接加上该月天数（加31）
		sum+=month[m];//直接将天数加到sum中
	}else{
		sum+=d;//未溢出，直接加d
	}	
	cout<<sum;
	return 0;
}
/*
思路：
1.输入年月日，先是判断年份是否是闰年，如果是闰年则将2月份设置为29天
2.将1月到m-1月的天数直接加到sum变量内
3.判断d是否移除，然后将直接将d加到变量中
*/