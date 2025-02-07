# Importing essential libraries and modules

from flask import Flask, render_template, request, Markup
import numpy as np
import pandas as pd
from utils.fertilizer import fertilizer_dic
import requests
import config
import pickle
import io

crop_recommendation_model_path = 'Models/rfmodel.pickle'
crop_recommendation_model = pickle.load(open(crop_recommendation_model_path, 'rb'))

data_1 = pd.read_csv("Data/datafile (1).csv")
data_2 = pd.read_csv("Data/datafile (2).csv")
data_3 = pd.read_csv("Data/datafile (3).csv")
data_ = pd.read_csv("Data/datafile.csv")
produce = pd.read_csv("Data/produce.csv")

def weather_fetch(city_name):
    api_key = config.weather_api_key
    base_url = "http://api.openweathermap.org/data/2.5/weather?"

    complete_url = base_url + "appid=" + api_key + "&q=" + city_name
    response = requests.get(complete_url)
    x = response.json()

    if x["cod"] != "404":
        y = x["main"]

        temperature = round((y["temp"] - 273.15), 2)
        humidity = y["humidity"]
        return temperature, humidity
    else:
        return None

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random as rnd

def get_recomm_npk(c_val):
  df=pd.read_csv("Data/crop_recommendation.csv")

  def combine_features(row):
      return str(row['N'])+" "+str(row['P'])+" "+str(row['K'])

  df["combined_features"] = df.apply(combine_features,axis=1)

  cv = CountVectorizer()
  cosim = cosine_similarity(cv.fit_transform(df["combined_features"]))

  def get_lfi(index):
      try: return df[df.index == index]["label"].values[0] 
      except: ''
  def get_inpk(npk):
      npk = list(map(int,npk.split(" ")))
      return [df.index[df.N == npk[0]][0]]+[df.index[df.P == npk[1]][0]]+[df.index[df.K == npk[2]][0]]

  # c_val= input() #crop name input rice etc
  choice_npk=list(zip(df[df.label==c_val]["N"],df[df.label==c_val]["P"],df[df.label==c_val]["K"]))

  try:    npki = get_inpk(input()) #n value p value k value in string format eg '90 30 50'
  except: npki = get_inpk(" ".join(map(str,rnd.choice(choice_npk))))

  try:
    sort_n = sorted(list(enumerate(cosim[npki[0]])),key=lambda x:x[1],reverse=True)[1:][:5]
    sort_p = sorted(list(enumerate(cosim[npki[1]])),key=lambda x:x[1],reverse=True)[1:][:5]
    sort_k = sorted(list(enumerate(cosim[npki[2]])),key=lambda x:x[1],reverse=True)[1:][:5]
  except:
    npki=get_inpk(" ".join(map(str,choice_npk[0])))
    sort_n = sorted(list(enumerate(cosim[npki[0]])),key=lambda x:x[1],reverse=True)[1:][:5]
    sort_p = sorted(list(enumerate(cosim[npki[1]])),key=lambda x:x[1],reverse=True)[1:][:5]
    sort_k = sorted(list(enumerate(cosim[npki[2]])),key=lambda x:x[1],reverse=True)[1:][:5]

  recom_n=" ".join(set(filter(lambda x: x is not None,map(lambda x: get_lfi(x[0]),sort_n))))
  recom_p=" ".join(set(filter(lambda x: x is not None,map(lambda x: get_lfi(x[0]),sort_p))))
  recom_k=" ".join(set(filter(lambda x: x is not None,map(lambda x: get_lfi(x[0]),sort_k))))

  
  return [recom_n, recom_p, recom_k]    
    

app = Flask(__name__)


@ app.route('/')
def home():
    title = 'MyPlant - Home'
    return render_template('index.html', title=title)


@ app.route('/crop-recommend')
def crop_recommend():
    title = 'MyPlant - Crop Recommendation'
    return render_template('crop.html', title=title)

@ app.route('/fertilizer')
def fertilizer_recommendation():
    title = 'MyPlant - Fertilizer Suggestion'

    return render_template('fertilizer.html', title=title)


@ app.route('/crop-predict', methods=['POST'])
def crop_prediction():
    title = 'MyPlant - Crop Recommendation'

    if request.method == 'POST':
        N = int(request.form['nitrogen'])
        P = int(request.form['phosphorous'])
        K = int(request.form['pottasium'])
        ph = float(request.form['ph'])
        rainfall = float(request.form['rainfall'])

        # state = request.form.get("stt")
        city = request.form.get("city")

        if weather_fetch(city) != None:
            temperature, humidity = weather_fetch(city)
            data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
            my_prediction = crop_recommendation_model.predict(data)
            final_prediction = my_prediction[0]

            return render_template('crop-result.html', prediction=final_prediction, title=title)

        else:

            return render_template('try_again.html', title=title)

@ app.route('/crop-calc', methods=['POST', 'GET'])
def crop_calc():
    title = 'MyPlant - Crop Calc'

    if request.method == 'POST':
        crop= request.form['crop']
        states = list(data_1[data_1["Crop"] == crop]["State"])
        culti_cost = list(data_1[data_1["Crop"] == crop]["Cost of Cultivation (`/Hectare) C2"])
        yield_quintal = list(data_1[data_1["Crop"] == crop]["Yield (Quintal/ Hectare) "])
        mapped = zip(states, culti_cost, yield_quintal)
        return render_template('crop-calc-result.html', data=mapped, title=title)
    if request.method == 'GET':
        return render_template('crop-calc.html', title=title)
    
@ app.route('/fertilizer-predict', methods=['POST'])
def fert_recommend():
    title = 'MyPlant - Fertilizer Suggestion'

    crop_name = str(request.form['cropname'])
    N = int(request.form['nitrogen'])
    P = int(request.form['phosphorous'])
    K = int(request.form['pottasium'])
    recomm_npk = get_recomm_npk(crop_name)
    # ph = float(request.form['ph'])

    df = pd.read_csv('Data/fertilizer.csv')

    nr = df[df['Crop'] == crop_name]['N'].iloc[0]
    pr = df[df['Crop'] == crop_name]['P'].iloc[0]
    kr = df[df['Crop'] == crop_name]['K'].iloc[0]

    n = nr - N
    p = pr - P
    k = kr - K
    temp = {abs(n): "N", abs(p): "P", abs(k): "K"}
    max_value = temp[max(temp.keys())]
    if max_value == "N":
        if n < 0:
            key = 'NHigh'
        else:
            key = "Nlow"
    elif max_value == "P":
        if p < 0:
            key = 'PHigh'
        else:
            key = "Plow"
    else:
        if k < 0:
            key = 'KHigh'
        else:
            key = "Klow"

    response = Markup(str(fertilizer_dic[key]))

    return render_template('fertilizer-result.html', recommendation=response, title=title, recomm_npk=recomm_npk)


if __name__ == '__main__':
    app.run(debug=True)
