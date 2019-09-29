import numpy as np
import requests
import json
import area
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

price_y={}
Dictionary = {}
Data = {}
areaData = area.area_data
url = 'http://data.coa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx?$top=1000&$skip=0&'
condition = '&StartDate=108.06.15&EndDate=108.08.15'
T7 = datetime.timedelta(days = 7)
T1 = datetime.timedelta(days = 1)
startDay = datetime.date(year = 2009, month = 1, day = 1)
today = datetime.date.today()

Partition = {'北':['台北','新北', '基隆', '桃園', '新竹', '新竹', '宜蘭'],
            '中':['苗栗', '台中', '彰化', '南投', '雲林'],
            '南':['嘉義', '台南', '高雄', '屏東', '澎湖'],
            '東':['花蓮', '台東']}

kindList = ['小白菜-土白菜']
# '芒果-愛文','蕹菜-小葉']

#載入資料時，將原始資料整理成price_y(dict)
def loadData(data_json, areaData, Partition, kind):
    global price_y
    for item in data_json:
        kind = item['作物名稱']
        if kind == '休市':
            continue
        for citys in areaData.keys():
            if item['市場名稱'][0:2] == citys[0:2]:
                item['city'] = citys
                success = True
                break
            cityList = areaData[citys]
            success = False
            for city in cityList:
                if item['市場名稱'][0:2] == city[0:2]:
                    item['city'] = citys
                    success = True
                    break
            if success:
                break
        for direc in Partition:
            if citys[0:2] not in Partition[direc]:
                continue
            date = item['交易日期'][0:3]+'-'+ item['交易日期'][4:6]+'-'+ item['交易日期'][7:]
            
            price = item['中價']
            
            if not price_y.__contains__(kind):
                price_y[kind] = {}
            if not price_y[kind].__contains__(direc):
                price_y[kind][direc] = {}
            if not price_y[kind][direc].__contains__(date):
                price_y[kind][direc][date] = []
            price_y[kind][direc][date].append(price)
                
            break

#第一次載入資料
def firstLoadData(url, startDay, kindList):
    for kind in kindList:
        while True:
            StartDate = startDay.strftime("%Y.%m.%d")
            if startDay > today:
                break
            StartDate = str(int(StartDate[0:4])-1911) + StartDate[4:]
            endDay = startDay + T7
            EndDate = endDay.strftime("%Y.%m.%d")
            EndDate = str(int(EndDate[0:4])-1911) + EndDate[4:]
            condition = '&'+ kind + '&StartDate=' + StartDate + '&EndDate=' + EndDate
            
            r = requests.get(url+condition)
            data_json = json.loads(r.text)
            loadData(data_json, areaData, Partition, kind)
            
            startDay = endDay + T1
        last_update = today
        return last_update

#將price_y整理成每個地區當時平均值Dictionary(dict)
def prepData(price_y, Dictionary):
    for kind in price_y.keys():
        item = price_y[kind]
        if not Dictionary.__contains__(kind):
            Dictionary[kind] = {}
            Data[kind] = {}
        for direc in item.keys():
            dateAndPrice = item[direc]
            if not Dictionary[kind].__contains__(direc):
                Dictionary[kind][direc] = {}
                Data[kind][direc] = {}
            for date in dateAndPrice:
                sumPrice = sum(dateAndPrice[date])
                average = sumPrice / len(dateAndPrice[date])
                if not Dictionary[kind][direc].__contains__(date):
                    string = str(int(date[0:3])+1911) + date[3:]
                    dates = pd.datetime.strptime(string, '%Y-%m-%d')
                    Dictionary[kind][direc][dates] = average
                    Data[kind][direc][string] = average
    return Dictionary

# f = open('price_data.txt','w')
# f.write(str(Data)) 



def trainModel(Dictionary, kindList, direction):
    ModelDict = {}
    for kind in kindList:
        for direc in direction:
            y_series = pd.Series(Dictionary[kind][direc])
            y_series.sort_index(ascending=True)
            mod = sm.tsa.statespace.SARIMAX(y_series,
                                            order=(3,0,2),
                                            seasonal_order = (0, 1, 1, 12),
                                            enforce_stationarity=False,
                                            enforce_invertibility=False)

            results = mod.fit()
            if not ModelDict.__contains__(kind):
                ModelDict[kind] = {}
            ModelDict[kind][direc] = results
    return ModelDict


def PredictWeekPrice(kind, direc, ModelDict):
    predict_day = 7
    model = ModelDict[kind][direc]
    forecast_value=model.get_forecast(steps = predict_day).predicted_mean.mean()

    return forecast_value
    # forecast = pd.Series(forecast_value.values, index = date_index[0:50])

def predictPrice(kind, direc, ModelDict, dateString, last_update, price_y):
    predict_day= 7
    model = ModelDict[kind][direc]
    forecast_value = model.get_forecast(steps=predict_day).predicted_mean
    today = datetime.date.today()
    try:
        date = pd.datetime.strptime(dateString, '%Y-%m-%d')
        if(date <= last_update):
            return {'realPrice' : price_y[kind][direc]}
        else:
            delta = date - today
            predict_day = delta.days
            forecast_value = model.get_forecast(steps=predict_day).predicted_mean
            return {'predictPrice' : forecast_value[predict_day - 1]}
    except:
        print('syntax Error')

# f = open('price_data.txt','r')
# string = f.read().replace("'", '"')
# pre_data = json.loads(string)
last_update = firstLoadData(url,startDay,kindList)
ModelDict = trainModel(pre_data,  kindList, Partition.keys())
print(PredictWeekPrice(kindList[0], '北', ModelDict))
