# Market Rent Management System — Streamlit + MongoDB Deploy Guide

## Step 1: MongoDB Atlas free database banayen
1. https://www.mongodb.com/cloud/atlas/register pe jayen, free sign up karain
2. "Create a free cluster" (M0 Free tier) select karain, koi bhi region choose kar lein
3. "Database Access" mein ek user banayen (username/password yaad rakhein)
4. "Network Access" mein "Allow access from anywhere" (0.0.0.0/0) add karain
5. Cluster ban jane ke baad "Connect" > "Drivers" pe click karain, connection string copy karain — kuch is tarhan dikhega:
   `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
6. Us string mein `<password>` ki jagah apna asal password likh dein

## Step 2: GitHub pe code upload karain
1. GitHub pe naya repository banayen (public ya private, dono chalega)
2. `app.py` aur `requirements.txt` dono files upload kar dein

## Step 3: Streamlit Community Cloud pe deploy karain
1. https://share.streamlit.io pe jayen, GitHub se sign in karain
2. "New app" > apni repository select karain > main file `app.py` choose karain
3. Deploy karne se pehle "Advanced settings" > "Secrets" mein ye likhein:
   ```
   mongo_uri = "yahan apni MongoDB connection string paste karain"
   ```
4. "Deploy" par click karain — 2-3 minute mein live link mil jayega
   (jaisay: `yourapp.streamlit.app`)

## Zaroori baatain
- Connection string kisi ke sath share na karain, sirf Streamlit ke "Secrets" mein dalain
- Default login password `admin123` hai — deploy hone ke baad Admin panel se turant tabdeel kar lein
- Data ab MongoDB mein save hoga — app restart ho, ya kahin se bhi khulay, data hamesha wahin milega
