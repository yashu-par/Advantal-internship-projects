# Payment-Fraud-Detection

INTRODUCTION

1.1 Project Overview

This project implements an automated Payment Fraud Detection System using Machine Learning and data science techniques. The system is designed to analyze online payment transactions and classify them as either legitimate or fraudulent based on transaction patterns and account behavior.
The project combines multiple classification algorithms including Logistic Regression, Random Forest, Neural Network, Support Vector Machine, Decision Tree, and XGBoost to create a complete end-to-end fraud detection pipeline. The system handles the major challenge of highly imbalanced data using SMOTE oversampling and threshold tuning techniques to achieve high precision, recall, and F1 scores across all models.


1.2 Project Objectives

Accurately detect fraudulent payment transactions from a large dataset
Handle the class imbalance problem where fraud cases are only 0.13% of total data
Train and evaluate multiple Machine Learning models for comparison
Improve model performance using feature engineering and threshold tuning
Build a complete pipeline from raw transaction data to final fraud prediction
Compare all models and identify the best performing algorithm

1.3 Technology Stack

Machine Learning Models: Logistic Regression, Random Forest, Neural Network, SVM, Decision Tree, XGBoost
Imbalance Handling: SMOTE (Synthetic Minority Oversampling Technique)
Data Processing: Pandas, NumPy
Visualization: Matplotlib, Seaborn
Programming Language: Python
Development Environment: Jupyter Notebook


DATASET

2.1 Dataset Overview
The dataset consists of over 6.3 million online payment transaction records. Each transaction contains details about the sender, receiver, transaction type, and account balances before and after the transaction. The target variable indicates whether a transaction is fraudulent or legitimate.


2.2 Dataset Composition
Total Records: 63,62,620 transactions
Total Features: 10 columns
Fraud Cases: 8,213 (only 0.13%)
Legitimate Cases: 63,54,407 (99.87%)
Transaction Types: CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER

2.3 Dataset Features
FeatureDescriptionstepTime step of the transactiontypeType of transactionamountAmount of the transactionnameOrigSender account IDoldbalanceOrgSender balance before transactionnewbalanceOrigSender balance after transactionnameDestReceiver account IDoldbalanceDestReceiver balance before transactionnewbalanceDestReceiver balance after transactionisFraudTarget variable (0 = Legit, 1 = Fraud)

2.4 Data Preprocessing
Dropped unnecessary columns: nameOrig, nameDest, isFlaggedFraud
Filtered only CASH_OUT and TRANSFER transactions (fraud only occurs in these types)
Applied Label Encoding on the type column
Applied SMOTE to handle class imbalance on training data only
Applied StandardScaler for Logistic Regression and SVM models


MODELS AND ARCHITECTURE

3.1 Logistic Regression
3.1.1 Model Overview
Logistic Regression is a linear classification algorithm used to predict binary outcomes. It estimates the probability of a transaction being fraudulent based on input features.

3.1.2 Configuration

Solver: SAGA (optimized for large datasets)
Penalty: L1 (feature selection)
Class Weight: Balanced
Max Iterations: 3000
Regularization: C = 0.05

3.1.3 Role in the System
Logistic Regression provides a baseline linear model for fraud detection. It works well after feature scaling and threshold tuning to improve precision and recall.

3.2 Random Forest
3.2.1 Model Overview
Random Forest is an ensemble method that builds multiple decision trees and combines their predictions. It is highly effective for fraud detection due to its ability to handle complex patterns.
3.2.2 Configuration

Number of Estimators: 10
Class Weight: Balanced
Parallel Jobs: -1 (all cores)

3.2.3 Role in the System
Random Forest captures non-linear relationships in transaction data and provides robust fraud classification with high accuracy.

3.3 Neural Network
3.3.1 Model Overview
A Multi-Layer Perceptron (MLP) Neural Network is used to learn complex patterns in transaction data through multiple hidden layers.
3.3.2 Configuration

Hidden Layers: (128, 64, 32)
Max Iterations: 200
Learning Rate: Adaptive
Early Stopping: Enabled

3.3.3 Role in the System
Neural Network learns deep patterns in the data and improves performance through adaptive learning rate and early stopping to prevent overfitting.

3.4 Support Vector Machine (SVM)
3.4.1 Model Overview
LinearSVC is used instead of RBF SVM for large datasets as it provides similar results with significantly faster training time.
3.4.2 Configuration

Model: LinearSVC with CalibratedClassifierCV

Class Weight: Balanced
C Value: 0.1
Cross Validation: 3

3.4.3 Role in the System
SVM finds the optimal decision boundary between fraud and legitimate transactions. CalibratedClassifierCV enables probability output for threshold tuning.

3.5 Decision Tree
3.5.1 Model Overview
Decision Tree is a tree-based algorithm that splits data based on feature conditions to classify transactions as fraud or legitimate.
3.5.2 Configuration

Max Depth: 15
Min Samples Split: 10
Min Samples Leaf: 5
Criterion: Gini
Class Weight: Balanced

3.5.3 Role in the System
Decision Tree provides an interpretable model where fraud detection rules can be visualized and understood clearly.

3.6 XGBoost
3.6.1 Model Overview
XGBoost is a gradient boosting algorithm that builds trees sequentially, with each tree correcting the errors of the previous one. It is one of the most powerful algorithms for structured data.
3.6.2 Configuration

Estimators: 100
Max Depth: 6
Learning Rate: 0.1
Scale Positive Weight: Auto calculated
Tree Method: Histogram (fast training)

3.6.3 Role in the System
XGBoost handles class imbalance through scale_pos_weight and delivers the highest performance among all models in this project.


FEATURE ENGINEERING

5.1 New Features Created
To improve model performance, the following new features were engineered from existing transaction data:
FeatureDescriptionWhy Importantbalance_diff_origSender balance differenceShows how much money left sender accountbalance_diff_destReceiver balance differenceShows how much money entered receiver accounterror_origBalance mismatch of senderHigh mismatch indicates tampered transactionerror_destBalance mismatch of receiverInconsistency signals fraudzero_bal_origAccount completely drainedAccount drain is a strong fraud signaldest_unchangedReceiver balance unchangedMoney sent but not received — suspiciousamount_ratioAmount vs original balanceAmount greater than balance — suspiciouslog_amountLog of transaction amountReduces skewness for better model learningtransfer_and_drainTRANSFER + account drainStrongest fraud signal combinationcashout_and_drainCASH_OUT + account drainSecond strongest fraud signal


IMPLEMENTATION DETAILS

6.1 Project Workflow

Install and import all required libraries
Load the dataset and perform EDA
Preprocess data — drop columns, filter types, encode labels
Engineer new features from existing transaction data
Split data into train and test sets using stratified split
Apply SMOTE on training data only to handle imbalance
Apply StandardScaler for applicable models
Train all 6 Machine Learning models
Apply threshold tuning using Precision-Recall curve
Evaluate each model and compare results
Rank models in ascending order by accuracy

6.2 Key Implementation Decisions
Why filter only CASH_OUT and TRANSFER?
Fraud in this dataset occurs exclusively in CASH_OUT and TRANSFER transactions. Filtering these types removes noise and improves model focus.
Why SMOTE only on training data?
Applying SMOTE on test data would give artificially inflated results. Test data must represent real-world distribution.
Why threshold tuning?
Default threshold of 0.5 gives very low precision on imbalanced data. Optimal threshold from Precision-Recall curve maximizes F1 Score.

RESULTS

7.1 Model Performance
All 6 models were evaluated on Precision, Recall, F1 Score, and Accuracy for the Fraud class. Models were ranked in ascending order of accuracy to identify the best performing algorithm.
7.2 Evaluation Metrics Used
MetricDescriptionAccuracyOverall correct predictionsPrecisionAmong predicted fraud — how many were actually fraudRecallAmong actual fraud — how many were correctly detectedF1 ScoreBalance between Precision and RecallROC-AUCOverall discrimination ability of the model
7.3 Output Format
Each model produces the following output:

Classification report with Precision, Recall, F1 Score
Confusion Matrix showing TP, FP, FN, TN
Threshold vs Precision/Recall/F1 plot
Final metric scores with pass/fail indicator for 80% target


APPLICATIONS AND FUTURE WORK

8.1 Practical Applications

Real-time online banking fraud detection
Credit card transaction monitoring
Mobile payment security systems
E-commerce payment protection
Digital wallet fraud prevention

8.2 Future Enhancements

Deploy model as a REST API for real-time predictions
Add deep learning models like LSTM for sequential transaction analysis
Build a dashboard for fraud monitoring and visualization
Integrate with live payment gateway for real-time detection
Add explainability using SHAP values to explain fraud predictions
Extend to multi-class fraud type classification

8.3 Challenges Addressed

Highly imbalanced dataset (only 0.13% fraud cases)
Low precision due to too many false alarms
Slow training for SVM on large data
Feature engineering for better fraud signals
Selecting optimal decision threshold for each model


CONCLUSION

This project successfully demonstrates a complete Payment Fraud Detection System using six different Machine Learning algorithms. The system handles the major challenge of extreme class imbalance using SMOTE oversampling and threshold tuning techniques.
Feature engineering played a crucial role in improving model performance by creating meaningful fraud signals from raw transaction data. Threshold tuning significantly improved Precision from as low as 0.22 to above 0.80 across models.
The model comparison in ascending order of accuracy clearly identifies the best performing algorithm for deployment in a real-world fraud detection scenario.


Key Achievements

Built and trained 6 different Machine Learning models for fraud detection
Handled extreme class imbalance using SMOTE oversampling technique
Created 10+ new engineered features to improve model performance
Applied threshold tuning to significantly improve Precision and F1 Score
Developed a complete end-to-end pipeline from raw data to final predictions
Compared all models and ranked them by performance


TECHNICAL SPECIFICATIONS

Software Requirements:

Python 3.x,
Pandas,
NumPy,
Scikit-learn,
XGBoost,
Imbalanced-learn,
Matplotlib,
Seaborn,
Jupyter Notebook

Models Used:
ModelTypeLogistic RegressionLinear ClassifierRandom ForestEnsemble MethodNeural NetworkDeep LearningSVM (LinearSVC)Margin ClassifierDecision TreeTree BasedXGBoostGradient Boosting

REFERENCES

Scikit-learn Documentation,
XGBoost Documentation,
Imbalanced-learn (SMOTE) Documentation,
Python Documentation,
Pandas Documentation,
Machine Learning concepts for Fraud Detection
