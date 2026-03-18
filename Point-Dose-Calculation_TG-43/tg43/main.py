# from flask import Flask
# from flask import request
# from flask import jsonify
from datetime import datetime
from validation import validation

import pydicom

rtplan_path = r"D:\code\TG43\brachy-hdr-tg43-check\tests\data\rtplan.dcm"
RT_Plan = pydicom.dcmread(rtplan_path)
CalDate = datetime(2021, 4, 22, 5, 22)
RAKR = 52570

# app = Flask('churn')

# @app.route('/predict', methods=['POST'])
# def predict():
#     customer = request.get_json()

#     X = dv.transform([customer])
#     y_pred = model.predict_proba(X)[0,1]
#     churn = y_pred >= 0.5

#     result = {
#         'Question 6 - churn_probability': float(y_pred),
#         'churn': bool(churn)
#     }
#     return jsonify(result)


if __name__ == '__main__':
    # app.run(debug=True, host='0.0.0.0', port=9696)
    print(validation(RAKR, CalDate, RT_Plan))
