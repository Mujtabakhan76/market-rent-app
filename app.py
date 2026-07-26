"""
مارکیٹ کرایہ مینجمنٹ سسٹم — Streamlit + MongoDB Atlas
اردو مارکیٹ رینٹ مینجمنٹ سسٹم — ڈیٹا مستقل طور پر MongoDB میں محفوظ ہوتا ہے۔
"""

import streamlit as st
import requests
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go

MONTHS_UR = ["جنوری","فروری","مارچ","اپریل","مئی","جون","جولائی","اگست","ستمبر","اکتوبر","نومبر","دسمبر"]

# ============================== Database ==============================
@st.cache_resource
def get_db():
    uri = st.secrets["mongo_uri"]
    client = MongoClient(uri)
    d = client["market_rent_db"]
    # Indexes speed up lookups — safe to call every time (no-op if already present)
    d["payments"].create_index([("shop_id", 1), ("month", 1), ("year", 1)], unique=True)
    d["shops"].create_index("status")
    return d

db = get_db()
shops_col = db["shops"]
payments_col = db["payments"]
settings_col = db["settings"]

def get_settings():
    s = settings_col.find_one({"_id": "config"})
    if not s:
        s = {"_id": "config", "collector_name": "مولانا عدنان صاحب", "admin_password": "admin123", "sms_enabled": True}
        settings_col.insert_one(s)
    return s

def update_settings(**kwargs):
    settings_col.update_one({"_id": "config"}, {"$set": kwargs}, upsert=True)

def seed_demo_if_empty():
    if shops_col.count_documents({}) == 0:
        demo = [
            {"number":"1","name":"الکریم جنرل اسٹور","tenant_name":"محمد اسلم","mobile":"03001234567","cnic":"","monthly_rent":15000,"status":"rented"},
            {"number":"2","name":"فیصل کلاتھ ہاؤس","tenant_name":"فیصل رشید","mobile":"03011234567","cnic":"","monthly_rent":22000,"status":"rented"},
            {"number":"3","name":"—","tenant_name":"—","mobile":"","cnic":"","monthly_rent":0,"status":"empty"},
        ]
        shops_col.insert_many(demo)

# ============================== Page Setup ==============================
st.set_page_config(page_title="مارکیٹ کرایہ مینجمنٹ سسٹم", page_icon="🏪", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@600;700&family=Noto+Naskh+Arabic:wght@400;600;700&display=swap');

/* Base font, applied narrowly so Streamlit's own layout scaffolding (flex
   containers, columns, sidebar drawer) is NOT force-flipped to RTL — that
   was causing overlapping headings and a stray vertical divider line. */
body, .stMarkdown, .stText, p, span, li {
  font-family: 'Noto Naskh Arabic', sans-serif;
}

/* Right-align actual text content without reversing Streamlit's internal
   flex/column layout (which needs to stay LTR to render correctly). */
.main .block-container { direction: rtl; }
.main .block-container div[data-testid="stHorizontalBlock"] { direction: ltr; }
.main .block-container div[data-testid="stHorizontalBlock"] > div { direction: rtl; }

h1, h2, h3 {
  font-family: 'Noto Nastaliq Urdu', serif !important;
  direction: rtl;
  text-align: right;
  line-height: 2.1 !important;
  padding-top: 8px;
  padding-bottom: 8px;
  margin: 0 0 6px 0 !important;
}
@media (max-width: 640px) {
  h1 { font-size: 26px !important; }
  h2 { font-size: 20px !important; }
  h3 { font-size: 17px !important; }
}

.stButton>button { border-radius: 10px; font-weight:600; }

div[data-testid="stMetric"] {
  background: linear-gradient(135deg, #eef9f3, #e7f1fb); border:1px solid #d8ece0;
  border-radius:16px; padding:14px 16px; direction: rtl; text-align: right;
}
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { text-align: right; width:100%; }

.badge-paid{background:#e6f6ec;color:#2f8a60;padding:4px 12px;border-radius:20px;font-weight:600;font-size:13px;}
.badge-due{background:#fdecea;color:#c0392b;padding:4px 12px;border-radius:20px;font-weight:600;font-size:13px;}
.badge-empty{background:#eee;color:#777;padding:4px 12px;border-radius:20px;font-weight:600;font-size:13px;}

/* Sidebar: keep its own drawer/animation mechanics in LTR (so it slides in
   correctly on mobile) but right-align the Urdu text inside it. */
section[data-testid="stSidebar"] { background:#ffffff; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p {
  direction: rtl; text-align: right;
}
</style>
""", unsafe_allow_html=True)

seed_demo_if_empty()
settings = get_settings()

# ============================== Login ==============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🏪 مارکیٹ کرایہ مینجمنٹ سسٹم</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#666;'>ایڈمن رسائی کے لیے پاس ورڈ درج کریں</p>", unsafe_allow_html=True)
        pw = st.text_input("پاس ورڈ", type="password")
        if st.button("داخل ہوں 🔐", use_container_width=True):
            if pw == settings["admin_password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("غلط پاس ورڈ، دوبارہ کوشش کریں۔")
        st.caption("ڈیفالٹ پاس ورڈ: admin123")
    st.stop()

# ============================== Helpers ==============================
def all_shops():
    return list(shops_col.find({}))

def get_payment(shop_id, month, year):
    return payments_col.find_one({"shop_id": shop_id, "month": month, "year": year})

def ensure_payment(shop, month, year):
    p = get_payment(shop["_id"], month, year)
    if not p:
        p = {"shop_id": shop["_id"], "month": month, "year": year,
             "total_rent": shop["monthly_rent"], "paid_amount": 0, "payment_date": None, "method": "نقد"}
        res = payments_col.insert_one(p)
        p["_id"] = res.inserted_id
    return p

# ============================== Bulk Data Loading (fast) ==============================
@st.cache_data(ttl=20)
def load_all_shops():
    return list(shops_col.find({}))

@st.cache_data(ttl=20)
def load_all_payments():
    return list(payments_col.find({}))

def invalidate_cache():
    load_all_shops.clear()
    load_all_payments.clear()

def build_payment_index(payments):
    idx = {}
    for p in payments:
        idx[(p["shop_id"], p["month"], p["year"])] = p
    return idx

def month_summary_fast(month, year, shops, pay_idx):
    total, collected = 0, 0
    for s in shops:
        if s["status"] != "rented":
            continue
        p = pay_idx.get((s["_id"], month, year))
        total += p["total_rent"] if p else s["monthly_rent"]
        collected += p["paid_amount"] if p else 0
    return total, collected, max(total - collected, 0)

def year_summary_fast(year, shops, pay_idx):
    total, collected = 0, 0
    for m in range(1, 13):
        t, c, _ = month_summary_fast(m, year, shops, pay_idx)
        total += t; collected += c
    return total, collected, max(total - collected, 0)

def fmt(n):
    return f"{int(n):,}"

def send_whatsapp(mobile, message):
    """Ultramsg API ke zariye asal WhatsApp message bhejta hai.
    Streamlit Secrets mein 'ultramsg_instance_id' aur 'ultramsg_token' na hon to
    khamoshi se skip kar deta hai (koi error nahi dikhata)."""
    if "ultramsg_instance_id" not in st.secrets or "ultramsg_token" not in st.secrets:
        return False, "ultramsg_secrets_missing"
    if not mobile:
        return False, "no_mobile_number"
    # Pakistani number ko international format mein badalna (03XXXXXXXXX -> 923XXXXXXXXX)
    clean = mobile.strip().replace(" ", "").replace("-", "")
    if clean.startswith("0"):
        clean = "92" + clean[1:]
    elif clean.startswith("+92"):
        clean = clean[1:]
    elif clean.startswith("92"):
        pass
    instance_id = st.secrets["ultramsg_instance_id"]
    token = st.secrets["ultramsg_token"]
    url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    try:
        resp = requests.post(url, data={"token": token, "to": clean, "body": message}, timeout=10)
        if resp.status_code == 200:
            return True, "sent"
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)

# ============================== Sidebar ==============================
with st.sidebar:
    st.markdown("### 🏪 مارکیٹ کرایہ مینجمنٹ")
    st.info(f"👳 کرایہ وصول کرنے والا:\n**{settings['collector_name']}**")
    page = st.radio("مینیو", [
        "🏠 ڈیش بورڈ", "🏬 دکانیں", "💰 کرایہ وصولی", "📒 دکان دار کھاتہ",
        "📊 رپورٹس", "🔍 سرچ", "⚙️ ایڈمن"
    ], label_visibility="collapsed")
    st.divider()
    if st.button("لاگ آؤٹ ⏻", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

today = date.today()
all_shops_data = load_all_shops()
all_payments_data = load_all_payments()
pay_idx = build_payment_index(all_payments_data)

# ============================== Dashboard ==============================
if page.endswith("ڈیش بورڈ"):
    st.title("🏠 ڈیش بورڈ")
    shops = all_shops_data
    total_shops = len(shops)
    rented = len([s for s in shops if s["status"] == "rented"])
    empty = total_shops - rented
    mt, mc, md = month_summary_fast(today.month, today.year, shops, pay_idx)
    yt, yc, yd = year_summary_fast(today.year, shops, pay_idx)

    c1, c2, c3 = st.columns(3)
    c1.metric("کل دکانیں", total_shops)
    c2.metric("کرایہ پر دی گئی دکانیں", rented)
    c3.metric("خالی دکانیں", empty)
    c1.metric("اس ماہ کا کل کرایہ", f"Rs {fmt(mt)}")
    c2.metric("اس ماہ وصول شدہ", f"Rs {fmt(mc)}")
    c3.metric("اس ماہ بقایا", f"Rs {fmt(md)}")
    c1.metric("اس سال کا کل کرایہ", f"Rs {fmt(yt)}")
    c2.metric("اس سال وصول شدہ", f"Rs {fmt(yc)}")
    c3.metric("اس سال بقایا", f"Rs {fmt(yd)}")

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        st.subheader("📈 ماہانہ آمدنی (پچھلے 12 مہینے)")
        labels, vals = [], []
        y, m = today.year, today.month
        for i in range(11, -1, -1):
            mm = m - i
            yy = y
            while mm <= 0:
                mm += 12; yy -= 1
            _, c, _ = month_summary_fast(mm, yy, shops, pay_idx)
            labels.append(MONTHS_UR[mm-1]); vals.append(c)
        fig = go.Figure(go.Bar(x=labels, y=vals, marker_color="#3fa373"))
        fig.update_layout(height=320, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        st.subheader("💠 وصول شدہ بمقابلہ بقایا (اس ماہ)")
        fig2 = go.Figure(go.Pie(labels=["وصول شدہ","بقایا"], values=[mc, md], hole=0.55,
                                 marker_colors=["#3fa373","#c0392b"]))
        fig2.update_layout(height=320, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

    colC, colD = st.columns(2)
    with colC:
        st.subheader("📊 سالانہ آمدنی")
        yl, yvals = [], []
        for yy in range(today.year-4, today.year+1):
            _, c, _ = year_summary_fast(yy, shops, pay_idx)
            yl.append(str(yy)); yvals.append(c)
        fig3 = go.Figure(go.Bar(x=yl, y=yvals, marker_color="#2f6fb0"))
        fig3.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)
    with colD:
        st.subheader("🏬 کرایہ پر بمقابلہ خالی")
        fig4 = go.Figure(go.Pie(labels=["کرایہ پر","خالی"], values=[rented, empty], hole=0.55,
                                 marker_colors=["#2f6fb0","#aaa"]))
        fig4.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

# ============================== Shops ==============================
elif page.endswith("دکانیں"):
    st.title("🏬 دکانیں")
    with st.expander("➕ نئی دکان شامل کریں"):
        c1, c2 = st.columns(2)
        number = c1.text_input("دکان نمبر *")
        name = c2.text_input("دکان کا نام")
        tenant = c1.text_input("دکان دار کا نام *")
        mobile = c2.text_input("موبائل نمبر *")
        cnic = c1.text_input("شناختی کارڈ نمبر (اختیاری)")
        rent = c2.number_input("ماہانہ کرایہ *", min_value=0, step=500)
        status = st.selectbox("دکان کی حالت", ["rented", "empty"], format_func=lambda x: "کرایہ پر" if x=="rented" else "خالی")
        if st.button("محفوظ کریں", key="add_shop"):
            if number and tenant and mobile and rent > 0:
                shops_col.insert_one({"number":number,"name":name or "—","tenant_name":tenant,"mobile":mobile,"cnic":cnic,"monthly_rent":rent,"status":status})
                invalidate_cache()
                st.success(f"دکان نمبر {number} شامل کر دی گئی۔")
                st.rerun()
            else:
                st.error("براہ کرم لازمی خانے (*) پُر کریں۔")

    st.divider()
    q = st.text_input("🔎 تلاش کریں (دکان نمبر / نام / موبائل)")
    shops = all_shops_data
    if q:
        shops = [s for s in shops if q.lower() in s["number"].lower() or q.lower() in s["tenant_name"].lower() or q in s.get("mobile","")]

    for s in shops:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2,2,1,1])
            c1.markdown(f"**دکان # {s['number']} — {s['name']}**")
            c1.caption(f"👤 {s['tenant_name']} · 📱 {s.get('mobile','—')}")
            c2.markdown(f"**Rs {fmt(s['monthly_rent'])}** / ماہانہ")
            badge = "کرایہ پر" if s["status"]=="rented" else "خالی"
            c2.markdown(f"<span class='{'badge-paid' if s['status']=='rented' else 'badge-empty'}'>{badge}</span>", unsafe_allow_html=True)
            if c3.button("✏️ ترمیم", key=f"edit_{s['_id']}"):
                st.session_state[f"editing_{s['_id']}"] = True
            if c4.button("🗑️ حذف", key=f"del_{s['_id']}"):
                shops_col.delete_one({"_id": s["_id"]})
                payments_col.delete_many({"shop_id": s["_id"]})
                invalidate_cache()
                st.rerun()
            if st.session_state.get(f"editing_{s['_id']}"):
                with st.form(f"form_{s['_id']}"):
                    nn = st.text_input("دکان کا نام", value=s["name"])
                    nt = st.text_input("دکان دار کا نام", value=s["tenant_name"])
                    nm = st.text_input("موبائل نمبر", value=s.get("mobile",""))
                    nr = st.number_input("ماہانہ کرایہ", value=s["monthly_rent"], min_value=0, step=500)
                    ns = st.selectbox("حالت", ["rented","empty"], index=0 if s["status"]=="rented" else 1, format_func=lambda x:"کرایہ پر" if x=="rented" else "خالی")
                    if st.form_submit_button("اپڈیٹ کریں"):
                        shops_col.update_one({"_id": s["_id"]}, {"$set": {"name":nn,"tenant_name":nt,"mobile":nm,"monthly_rent":nr,"status":ns}})
                        invalidate_cache()
                        st.session_state[f"editing_{s['_id']}"] = False
                        st.rerun()

# ============================== Rent Collection ==============================
elif page.endswith("کرایہ وصولی"):
    st.title("💰 کرایہ وصولی")
    c1, c2 = st.columns(2)
    month = c1.selectbox("مہینہ", list(range(1,13)), index=today.month-1, format_func=lambda m: MONTHS_UR[m-1])
    year = c2.selectbox("سال", list(range(today.year-3, today.year+2)), index=3)

    rows = []
    for s in all_shops_data:
        if s["status"] != "rented":
            continue
        p = pay_idx.get((s["_id"], month, year))
        if not p:
            p = ensure_payment(s, month, year)
        due = max(p["total_rent"] - p["paid_amount"], 0)
        rows.append({"شاپ":s, "پیمنٹ":p, "بقایا":due})

    if not rows:
        st.info("کوئی کرایہ دار دکان موجود نہیں۔")
    for r in rows:
        s, p, due = r["شاپ"], r["پیمنٹ"], r["بقایا"]
        with st.container(border=True):
            c1,c2,c3,c4,c5 = st.columns([1.3,1.3,1.3,1.3,1.3])
            c1.markdown(f"**دکان # {s['number']}**\n\n{s['tenant_name']}")
            c2.markdown(f"کل کرایہ\n\n**Rs {fmt(p['total_rent'])}**")
            c3.markdown(f"وصول شدہ\n\n**Rs {fmt(p['paid_amount'])}**")
            c4.markdown(f"بقایا\n\n**Rs {fmt(due)}**")
            status_html = "<span class='badge-paid'>✔ ادا شدہ</span>" if due<=0 else "<span class='badge-due'>بقایا</span>"
            c5.markdown(status_html, unsafe_allow_html=True)
            with st.expander("💰 وصول کریں"):
                amt = st.number_input("وصول شدہ رقم", min_value=0, value=int(p["paid_amount"]), step=500, key=f"amt_{p['_id']}")
                mth = st.selectbox("ادائیگی کا طریقہ", ["نقد","بینک","ایزی پیسہ","جاز کیش"], key=f"mth_{p['_id']}")
                pdate = st.date_input("تاریخ", value=today, key=f"date_{p['_id']}")
                if st.button("محفوظ کریں ✅", key=f"save_{p['_id']}"):
                    payments_col.update_one({"_id": p["_id"]}, {"$set": {
                        "paid_amount": amt, "method": mth, "payment_date": str(pdate)
                    }})
                    invalidate_cache()
                    new_due = max(p["total_rent"] - amt, 0)
                    msg = f"السلام علیکم\nآپ نے اس ماہ {fmt(amt)} روپے جمع کروا دیے ہیں۔\nبقایا رقم: {fmt(new_due)} روپے\nشکریہ\nمارکیٹ انتظامیہ\n{settings['collector_name']}"
                    if settings.get("sms_enabled", True):
                        ok, info = send_whatsapp(s.get("mobile",""), msg)
                        if ok:
                            st.toast(f"✅ WhatsApp پیغام بھیج دیا گیا — {s.get('mobile','—')}")
                        elif info == "ultramsg_secrets_missing":
                            st.info("ℹ️ WhatsApp API ابھی کنیکٹ نہیں ہوئی — Admin کو Secrets میں Ultramsg تفصیلات شامل کرنی ہوں گی۔")
                            st.code(msg, language=None)
                        else:
                            st.warning(f"⚠️ WhatsApp پیغام نہیں جا سکا ({info})۔")
                            st.code(msg, language=None)
                    st.success("ادائیگی محفوظ کر لی گئی۔")
                    st.rerun()

# ============================== Ledger ==============================
elif page.endswith("دکان دار کھاتہ"):
    st.title("📒 دکان دار کھاتہ")
    shops = all_shops_data
    names = {f"دکان #{s['number']} — {s['tenant_name']}": s for s in shops}
    if names:
        pick = st.selectbox("دکان دار منتخب کریں", list(names.keys()))
        s = names[pick]
        history = sorted([p for p in all_payments_data if p["shop_id"] == s["_id"]], key=lambda p:(p["year"], p["month"]), reverse=True)
        total_rent = sum(p["total_rent"] for p in history)
        total_paid = sum(p["paid_amount"] for p in history)
        total_due = max(total_rent - total_paid, 0)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("ماہانہ کرایہ", f"Rs {fmt(s['monthly_rent'])}")
        c2.metric("کل بننے والا کرایہ", f"Rs {fmt(total_rent)}")
        c3.metric("کل وصول شدہ", f"Rs {fmt(total_paid)}")
        c4.metric("کل بقایا", f"Rs {fmt(total_due)}")

        if history:
            df = pd.DataFrame([{
                "مہینہ": f"{MONTHS_UR[p['month']-1]} {p['year']}",
                "کل کرایہ": p["total_rent"], "وصول شدہ": p["paid_amount"],
                "بقایا": max(p["total_rent"]-p["paid_amount"],0),
                "تاریخ": p.get("payment_date") or "—", "طریقہ": p["method"]
            } for p in history])
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ کھاتہ CSV ڈاؤن لوڈ کریں", csv, f"ledger_{s['number']}.csv", "text/csv")
        else:
            st.info("ابھی تک کوئی ادائیگی درج نہیں ہوئی۔")
    else:
        st.info("کوئی دکان موجود نہیں۔")

# ============================== Reports ==============================
elif page.endswith("رپورٹس"):
    st.title("📊 رپورٹس")
    filt = st.radio("فلٹر", ["اس مہینے","اس سال"], horizontal=True)
    if filt == "اس مہینے":
        t, c, d = month_summary_fast(today.month, today.year, all_shops_data, pay_idx)
    else:
        t, c, d = year_summary_fast(today.year, all_shops_data, pay_idx)
    c1,c2,c3 = st.columns(3)
    c1.metric("کل بننے والا کرایہ", f"Rs {fmt(t)}")
    c2.metric("کل وصول شدہ", f"Rs {fmt(c)}")
    c3.metric("کل بقایا", f"Rs {fmt(d)}")

    st.divider()
    colL, colR = st.columns(2)
    defaulters, paid_up = [], []
    for s in all_shops_data:
        if s["status"] != "rented":
            continue
        p = pay_idx.get((s["_id"], today.month, today.year))
        total = p["total_rent"] if p else s["monthly_rent"]
        paid = p["paid_amount"] if p else 0
        due = max(total - paid, 0)
        if due > 0:
            defaulters.append({"دکان":s["number"], "نام":s["tenant_name"], "موبائل":s.get("mobile","—"), "بقایا": fmt(due)})
        elif p:
            paid_up.append({"دکان":s["number"], "نام":s["tenant_name"], "موبائل":s.get("mobile","—"), "وصول شدہ": fmt(paid)})
    with colL:
        st.subheader("🔴 کرایہ نہ دینے والے")
        st.dataframe(pd.DataFrame(defaulters) if defaulters else pd.DataFrame([{"پیغام":"کوئی بقایا دار نہیں 🎉"}]), use_container_width=True, hide_index=True)
    with colR:
        st.subheader("🟢 مکمل ادائیگی کرنے والے")
        st.dataframe(pd.DataFrame(paid_up) if paid_up else pd.DataFrame([{"پیغام":"ابھی تک کوئی نہیں"}]), use_container_width=True, hide_index=True)

# ============================== Search ==============================
elif page.endswith("سرچ"):
    st.title("🔍 سرچ")
    q = st.text_input("دکان نمبر، دکان دار کا نام یا موبائل نمبر لکھیں")
    if q:
        results = [s for s in all_shops_data if q.lower() in s["number"].lower() or q.lower() in s["tenant_name"].lower() or q in s.get("mobile","")]
        if results:
            for s in results:
                with st.container(border=True):
                    st.markdown(f"**دکان # {s['number']} — {s['tenant_name']}**")
                    st.caption(f"📱 {s.get('mobile','—')} · Rs {fmt(s['monthly_rent'])}")
        else:
            st.warning("کوئی نتیجہ نہیں ملا۔")

# ============================== Admin ==============================
elif page.endswith("ایڈمن"):
    st.title("⚙️ ایڈمن پینل")

    st.subheader("👤 کرایہ وصول کرنے والا")
    new_name = st.text_input("نام", value=settings["collector_name"])
    if st.button("نام محفوظ کریں"):
        update_settings(collector_name=new_name)
        st.success("محفوظ ہو گیا۔")
        st.rerun()

    st.divider()
    st.subheader("🔐 پاس ورڈ تبدیل کریں")
    old_p = st.text_input("موجودہ پاس ورڈ", type="password")
    new_p = st.text_input("نیا پاس ورڈ", type="password")
    if st.button("پاس ورڈ اپڈیٹ کریں"):
        if old_p != settings["admin_password"]:
            st.error("موجودہ پاس ورڈ غلط ہے۔")
        elif len(new_p) < 4:
            st.error("نیا پاس ورڈ کم از کم 4 حروف کا ہو۔")
        else:
            update_settings(admin_password=new_p)
            st.success("پاس ورڈ تبدیل ہو گیا۔")

    st.divider()
    st.subheader("📡 WhatsApp سیٹنگ")
    sms_on = st.toggle("خودکار WhatsApp پیغام بھیجیں", value=settings.get("sms_enabled", True))
    st.caption("پیغام بھیجنے کے لیے Ultramsg WhatsApp API کنیکٹ ہونی ضروری ہے (Streamlit Secrets میں ultramsg_instance_id اور ultramsg_token شامل کریں)۔")
    if sms_on != settings.get("sms_enabled", True):
        update_settings(sms_enabled=sms_on)
        st.rerun()

    st.divider()
    st.subheader("💾 ڈیٹا ایکسپورٹ")
    all_data = {
        "shops": [{k:str(v) for k,v in s.items()} for s in all_shops()],
        "payments": [{k:str(v) for k,v in p.items()} for p in payments_col.find({})]
    }
    import json
    st.download_button("⬇️ مکمل بیک اپ (JSON) ڈاؤن لوڈ کریں", json.dumps(all_data, ensure_ascii=False, indent=2).encode("utf-8"), "backup.json", "application/json")
